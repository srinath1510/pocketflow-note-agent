#!/usr/bin/env python3
"""
Enhanced Content Analysis Node with Batch LLM Processing
Reduces API calls by up to 80% while maintaining analysis quality
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from collections import Counter
import os
import hashlib

from pocketflow import Node as BaseNode
from .llm_client import get_llm_client


class ContentAnalysisNode(BaseNode):
    """
    Node 2: Enhanced Content Analysis Node with Batch Processing
    
    Purpose: Extract key concepts, entities, topics, and semantic meaning from captures
    
    Input: shared_state['raw_captures'] from Capture Ingestion node. 
    Process: LLM analysis + entity extraction + topic classification + concept hierarchy
    Output: shared_state['extracted_concepts'] and shared_state['content_analysis']

    Key Optimizations:
    1. Batch multiple captures in single LLM call (5x reduction)
    2. Smart caching for similar content (20x speedup for duplicates)
    3. Rule-based pre-filtering (avoid LLM for simple content)
    4. Hierarchical analysis (quick first pass, detailed second pass)
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.llm_client = None
        self._initialize_llm()

        # Batch processing configuration
        self.batch_size = 5  # Process 5 captures per LLM call
        self.min_content_length = 100  # Skip LLM for very short content
        self.cache_enabled = True

        # Content analysis cache
        self.content_cache = {}
        self.domain_patterns = {}

        self.content_patterns = {
            'code_tutorial': [r'```', r'<code>', r'def ', r'function ', r'import ', r'#include'],
            'research_paper': [r'abstract', r'doi:', r'arxiv', r'references', r'\[\d+\]'],
            'documentation': [r'api reference', r'getting started', r'installation', r'usage'],
            'blog_post': [r'posted on', r'by .+ on', r'comments', r'share this'],
            'news_article': [r'published \d+ hours ago', r'breaking news', r'updated:']
        }
    

    def _initialize_llm(self):
        """Initialize LLM client (tries multiple providers)"""
        try:
            preferred_provider = os.getenv('LLM_PROVIDER')  # 'anthropic', etc.
            
            self.llm_client = get_llm_client(preferred_provider)
            self.provider_name = self.llm_client.get_provider_name()
            self.logger.info(f"LLM client initialized for batch processing: {self.provider_name}")

        except Exception as e:
            self.logger.error(f"Failed to initialize any LLM provider: {str(e)}")
            raise RuntimeError(f"No LLM providers available: {str(e)}")

    
    def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare for content analysis by validating inputs and LLM availability.
        """
        self.logger.info("Starting Enhanced Content Analysis prep phase")

        shared_state.setdefault('pipeline_metadata', {})
        shared_state['pipeline_metadata']['content_analysis_start'] = datetime.now(timezone.utc).isoformat()

        if not self.llm_client or not self.llm_client.is_available():
            error_msg = f"LLM provider ({self.provider_name}) not available"
            self.logger.error(error_msg)
            return {'error': error_msg, 'captures_to_analyze': []}
        
        # output of Capture Ingestion node
        raw_captures = shared_state.get('raw_captures', [])

        if not raw_captures:
            self.logger.error("No raw captures found in shared state")
            return {'captures_to_analyze': [], 'error': 'No captures to analyze'}
        
        # Pre-process and categorize captures for batch optimization
        capture_categories = self._categorize_captures_for_processing(raw_captures)
        
        prep_data = {
            'capture_categories': capture_categories,
            'batch_config': {
                'total_captures': len(raw_captures),
                'llm_required': len(capture_categories['llm_required']),
                'rule_based': len(capture_categories['rule_based']),
                'cached': len(capture_categories['cached']),
                'batch_size': self.batch_size,
                'estimated_api_calls': self._estimate_api_calls(capture_categories)
            },
            'llm_provider': self.provider_name
        }
        
        self.logger.info(f"Batch processing setup: {prep_data['batch_config']['estimated_api_calls']} API calls estimated "
                        f"(vs {len(raw_captures)} individual calls)")

        return prep_data

    
    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution: Analyze captures using LLM for learning concept extraction.
        """
        self.logger.info("Starting batch content analysis execution")

        if 'error' in prep_result:
            return {'error': prep_result['error'], 'extracted_concepts': {}, 'content_analysis': {}}

        capture_categories = prep_result['capture_categories']
        batch_config = prep_result['batch_config']

        try:
            # Step 1: Process cached content (instant)
            cached_results = self._process_cached_captures(capture_categories['cached'])
            self.logger.info(f"Retrieved {len(cached_results)} results from cache")
            
            # Step 2: Process rule-based content (no LLM needed)
            rule_based_results = self._process_rule_based_captures(capture_categories['rule_based'])
            self.logger.info(f"Processed {len(rule_based_results)} captures with rule-based analysis")
            
            # Step 3: Batch process complex content requiring LLM
            batch_results = self._process_captures_in_batches(capture_categories['llm_required'])
            self.logger.info(f"Processed {len(batch_results)} captures with {(len(batch_results) // self.batch_size) + 1 if batch_results else 0} LLM calls")
            
            # Combine all results
            all_results = cached_results + rule_based_results + batch_results
            
            # Step 4: Cross-capture synthesis (single LLM call for all)
            synthesis_result = self._synthesize_across_all_captures(all_results)
            
            # Step 5: Combine and format final results
            combined_result = self._combine_all_analysis_results(all_results, synthesis_result, batch_config)

            batch_metrics = combined_result.get('batch_metrics', {})
            
            if not batch_metrics:
                self.logger.error("🚨 CRITICAL: No batch_metrics in combined_result!")
                self.logger.error(f"   Available keys: {list(combined_result.keys())}")
                
                # default batch_metrics to prevent crash
                default_batch_metrics = {
                    'api_calls_made': 0,
                    'api_calls_saved': 0,
                    'api_calls_reduction_percent': 0,
                    'cache_hit_rate': 0,
                    'method_breakdown': {},
                    'total_captures_processed': len(all_results)
                }
                combined_result['batch_metrics'] = default_batch_metrics
                self.logger.warning(f"🔧 CREATED DEFAULT batch_metrics: {default_batch_metrics}")
            else:
                api_calls_made = batch_metrics.get('api_calls_made', 0)
                api_calls_saved = batch_metrics.get('api_calls_saved', 0)
                self.logger.info(f"✅ BATCH METRICS FOUND: {api_calls_made} made, {api_calls_saved} saved")
            
            self.logger.info(f"Batch analysis complete: {len(all_results)} captures processed with "
                        f"{batch_config['estimated_api_calls']} API calls")
            
            return combined_result

        except Exception as e:
            self.logger.error(f"Batch analysis failed: {str(e)}")
            return {
                'error': f"Batch analysis failed: {str(e)}",
                'extracted_concepts': {},
                'content_analysis': {'method': 'failed', 'error': str(e)},
                'batch_metrics': {  # Add default metrics even on error
                    'api_calls_made': 0,
                    'api_calls_saved': 0,
                    'api_calls_reduction_percent': 0,
                    'cache_hit_rate': 0,
                    'method_breakdown': {},
                    'total_captures_processed': 0
            }
        }


    def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """
        Enhanced post-processing with batch metrics
        """
        self.logger.info("Starting Enhanced Content Analysis post-execution phase")

        shared_state['extracted_concepts'] = exec_result.get('extracted_concepts', {})
        shared_state['content_analysis'] = exec_result.get('content_analysis', {})

        batch_metrics = exec_result.get('batch_metrics', {})
        

        if batch_metrics:
            shared_state['batch_metrics'] = batch_metrics
            shared_state.setdefault('pipeline_metadata', {})
            shared_state['pipeline_metadata']['batch_optimization_metrics'] = batch_metrics

            api_calls_saved = batch_metrics.get('api_calls_saved', 0)
            cache_hit_rate = batch_metrics.get('cache_hit_rate', 0)
            total_processed = batch_metrics.get('total_captures_processed', 0)

            self.logger.info(f"🔍 ✅ BATCH METRICS SUCCESSFULLY ADDED:")
            self.logger.info(f"   → API calls saved: {api_calls_saved}")
            self.logger.info(f"   → Cache hit rate: {cache_hit_rate:.1f}%")
            self.logger.info(f"   → Total captures processed: {total_processed}")
            self.logger.info(f"   → Stored in shared_state['batch_metrics']")
            self.logger.info(f"   → Stored in shared_state['pipeline_metadata']['batch_optimization_metrics']")

            print(f"🎉 BATCH OPTIMIZATION SUCCESS IN CONTENT ANALYSIS:")
            print(f"   API Calls Saved: {api_calls_saved}")
            print(f"   Cache Hit Rate: {cache_hit_rate:.1f}%")
            print(f"   Method Breakdown: {batch_metrics.get('method_breakdown', {})}")
 
        else:
            self.logger.warning("⚠️  No batch_metrics found in exec_result")
            self.logger.error(f"   Available exec_result keys: {list(exec_result.keys())}")

            default_batch_metrics = {
                'api_calls_made': 0,
                'api_calls_saved': 0,
                'api_calls_reduction_percent': 0,
                'cache_hit_rate': 0,
                'method_breakdown': {},
                'total_captures_processed': 0,
                'error': 'batch_metrics_missing_from_exec_result'
            }
            shared_state['batch_metrics'] = default_batch_metrics
            shared_state['pipeline_metadata']['batch_optimization_metrics'] = default_batch_metrics

            self.logger.warning(f"🔧 CREATED DEFAULT batch_metrics to prevent failures")


        concepts = exec_result.get('extracted_concepts', {})
        processing_summary = {
            'learning_concepts_extracted': len(concepts.get('learning_concepts', [])),
            'entities_found': len(concepts.get('entities', {})),
            'topics_identified': len(concepts.get('topics', [])),
            'analysis_method': 'batch_optimized_llm',
            'overall_complexity': concepts.get('complexity_assessment', {}).get('overall_level', 'unknown'),
            'batch_optimization_metrics': batch_metrics,
            'llm_provider': prep_result.get('llm_provider', 'unknown')
        }

        shared_state['pipeline_metadata']['content_analysis_summary'] = processing_summary
        shared_state['pipeline_metadata']['content_analysis_end'] = datetime.now(timezone.utc).isoformat()
        
        final_batch_metrics = shared_state.get('batch_metrics', {})
        api_calls_saved = final_batch_metrics.get('api_calls_saved', 0)
    
        if api_calls_saved > 0:
            self.logger.info(f"✅ Content analysis complete - API calls saved: {api_calls_saved}")
            print(f"✅ CONTENT ANALYSIS POST COMPLETE - {api_calls_saved} API calls saved!")
        else:
            self.logger.warning(f"⚠️  Content analysis complete but no API call savings detected")
            print(f"⚠️  CONTENT ANALYSIS POST COMPLETE - No API call savings detected")
    
        return "default"

    
    def _categorize_captures_for_processing(self, raw_captures: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize captures by processing method to optimize batch processing"""
        
        categories = {
            'cached': [],        # Already analyzed similar content
            'rule_based': [],    # Can be analyzed without LLM
            'llm_required': []   # Needs LLM analysis
        }
        
        for capture in raw_captures:
            content = capture.get('content', '')
            
            # Check cache first
            content_hash = self._get_content_hash(content)
            if self.cache_enabled and content_hash in self.content_cache:
                categories['cached'].append({**capture, 'content_hash': content_hash})
                continue
            
            # Check if rule-based analysis is sufficient
            if self._can_use_rule_based_analysis(capture):
                categories['rule_based'].append({**capture, 'content_hash': content_hash})
                continue
            
            # Requires LLM analysis
            categories['llm_required'].append({**capture, 'content_hash': content_hash})
        
        return categories
    

    def _can_use_rule_based_analysis(self, capture: Dict[str, Any]) -> bool:
        """Determine if capture can be analyzed without LLM"""
        
        content = capture.get('content', '')
        metadata = capture.get('metadata', {})
        
        # Skip LLM for very short content
        if len(content.split()) < 3:
            return True
        
        # Skip LLM for simple reference pages
        if metadata.get('content_category') in ['simple_reference', 'basic_documentation']:
            return True
        
        # Skip LLM if domain has established patterns
        domain = metadata.get('domain', '')
        if domain in self.domain_patterns and self.domain_patterns[domain]['confidence'] > 0.8:
            return True
        
        # Skip LLM for clearly identified content types
        content_type = self._classify_content_type_rules(content)
        if content_type and content_type != 'unknown':
            return True
        
        return False
    

    def _process_cached_captures(self, cached_captures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process captures using cached analysis results"""
        
        results = []
        for capture in cached_captures:
            content_hash = capture['content_hash']
            cached_analysis = self.content_cache[content_hash].copy()
            
            # Update metadata for this specific capture
            cached_analysis.update({
                'capture_id': capture.get('id', f'capture_{len(results)}'),
                'processing_method': 'cached',
                'url': capture.get('url', ''),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            results.append(cached_analysis)
        
        return results
    

    def _process_rule_based_captures(self, rule_based_captures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process captures using rule-based analysis (no LLM)"""
        
        results = []
        for i, capture in enumerate(rule_based_captures):
            content = capture.get('content', '')
            
            # Rule-based concept extraction
            concepts = self._extract_concepts_rules(content)
            entities = self._extract_entities_rules(content)
            content_type = self._classify_content_type_rules(content)
            
            analysis = {
                'capture_id': capture.get('id', f'rule_based_{i}'),
                'learning_concepts': concepts,
                'key_terms': self._extract_key_terms_rules(content),
                'entities': entities,
                'main_topic': content_type or 'general',
                'complexity': self._assess_complexity_rules(content),
                'learning_type': self._classify_learning_type_rules(content),
                'processing_method': 'rule_based',
                'url': capture.get('url', ''),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Cache the result for future use
            if self.cache_enabled:
                self.content_cache[capture['content_hash']] = analysis.copy()
            
            results.append(analysis)
        
        return results

    
    def _process_captures_in_batches(self, llm_captures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process captures in batches using LLM"""
        
        results = []
        total_batches = (len(llm_captures) + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(0, len(llm_captures), self.batch_size):
            batch = llm_captures[batch_idx:batch_idx + self.batch_size]
            
            self.logger.info(f"Processing batch {batch_idx // self.batch_size + 1}/{total_batches} "
                           f"with {len(batch)} captures")
            
            try:
                batch_results = self._analyze_batch_with_llm(batch)
                results.extend(batch_results)
                
                # Cache successful results
                if self.cache_enabled:
                    for capture, result in zip(batch, batch_results):
                        self.content_cache[capture['content_hash']] = result.copy()
                
            except Exception as e:
                self.logger.warning(f"Batch {batch_idx // self.batch_size + 1} failed: {str(e)}")
                # Fallback to rule-based analysis for failed batch
                fallback_results = self._process_rule_based_captures(batch)
                results.extend(fallback_results)
        
        return results

    
    def _analyze_batch_with_llm(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze a batch of captures with a single LLM call"""
        
        # Create batch prompt
        batch_prompt = self._create_batch_prompt(batch)
        
        messages = [
            {"role": "system", "content": self._get_analysis_system_message('batch_analysis')},
            {"role": "user", "content": batch_prompt}
        ]
        
        # Set provider-specific defaults
        request_params = self.llm_client.set_provider_specific_defaults(
            temperature=0.2,
            max_tokens=2000  # Increased for batch processing
        )
        
        response_text = self.llm_client.chat_completion(messages, **request_params)
        batch_analysis = json.loads(response_text)
        
        # Process and validate batch results
        processed_results = []
        for i, (capture, analysis) in enumerate(zip(batch, batch_analysis.get('analyses', []))):
            processed_analysis = {
                'capture_id': capture.get('id', f'batch_capture_{i}'),
                'learning_concepts': analysis.get('core_concepts', []),
                'key_terms': analysis.get('key_terms', {}),
                'entities': analysis.get('entities', {}),
                'methodologies': analysis.get('methodologies', []),
                'skills': analysis.get('learning_objectives', []),
                'complexity': analysis.get('complexity_level', 'intermediate'),
                'prerequisites': analysis.get('prerequisite_knowledge', []),
                'learning_type': analysis.get('content_type', 'explanation'),
                'actionable_items': analysis.get('practical_applications', []), 
                'main_topic': analysis.get('main_topic', 'unknown'),
                'processing_method': 'llm_batch',
                'url': capture.get('url', ''),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            processed_results.append(processed_analysis)
        
        return processed_results
    

    def _create_batch_prompt(self, batch: List[Dict[str, Any]]) -> str:
        """Create optimized prompt for batch processing"""
        
        batch_content = []
        for i, capture in enumerate(batch):
            content_preview = capture.get('content', '')[:800]  # Limit content length
            url = capture.get('url', 'Unknown URL')
            
            batch_content.append(f"""
            CAPTURE {i+1}:
            URL: {url}
            CONTENT: {content_preview}
            ---""")
        
        return f"""You are analyzing {len(batch)} learning materials to extract educational insights that help someone build knowledge and skills.

    {chr(10).join(batch_content)}

    For each capture, focus on what someone could LEARN and APPLY. Extract:

    {{
        "analyses": [
            {{
            "core_concepts": ["fundamental concept 1", "key concept 2", "important principle 3"],
            "key_terms": {{"technical_term": "clear, learner-friendly definition"}},
            "learning_objectives": ["specific skill you can develop", "knowledge you can gain"],
            "complexity_level": "beginner|intermediate|advanced|expert",
            "content_type": "tutorial|explanation|documentation|example|theory|practical",
            "practical_applications": ["how to use this knowledge", "where to apply these skills"],
            "prerequisite_knowledge": ["what to learn first", "foundational concepts needed"],
            "key_insights": ["main takeaway", "important understanding"],
            "main_topic": "primary subject area",
            "entities": {{"name": "type"}},
            "methodologies": ["approach", "technique", "method"]
            }},
            // ... repeat for each capture
        ]
    }}

    FOCUS ON:
    - Concepts that build understanding and capability
    - Knowledge that transfers to real applications  
    - Skills someone can develop and practice
    - Clear definitions that aid comprehension

    Return only valid JSON. Be specific and actionable."""

    
    def _synthesize_across_all_captures(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize insights across all processed captures"""
        
        if not all_results:
            return {'session_learning_theme': 'no_content', 'error': 'No results to synthesize'}
        
        # Extract key data for synthesis
        all_concepts = []
        all_topics = []
        all_complexity_levels = []
        
        for result in all_results:
            all_concepts.extend(result.get('learning_concepts', []))
            all_topics.append(result.get('main_topic', 'unknown'))
            all_complexity_levels.append(result.get('complexity', 'intermediate'))
        
        # Rule-based synthesis for efficiency (instead of always using LLM)
        primary_topics = [topic for topic, count in Counter(all_topics).most_common(3)]
        primary_complexity = Counter(all_complexity_levels).most_common(1)[0][0]
        
        # Use LLM synthesis only for complex multi-topic sessions
        if len(set(primary_topics)) > 2 and len(all_results) > 3:
            return self._llm_synthesize_complex_session(all_results)
        else:
            return self._rule_based_synthesis(all_concepts, primary_topics, primary_complexity)
    

    def _rule_based_synthesis(self, concepts: List[str], topics: List[str], complexity: str) -> Dict[str, Any]:
        """Fast rule-based synthesis for simple sessions"""
        
        unique_concepts = list(dict.fromkeys(concepts))  # Preserve order, remove duplicates
        primary_topic = topics[0] if topics else 'general'
        
        return {
            'session_learning_theme': primary_topic.replace('_', ' ').title(),
            'knowledge_progression': unique_concepts[:5],  # First 5 as progression
            'learning_path': unique_concepts,
            'knowledge_gaps': [],  # Will be filled by historical analysis
            'session_complexity': complexity,
            'learning_goals': [f"understand_{primary_topic}"],
            'next_steps': [f"practice_{concept.lower().replace(' ', '_')}" for concept in unique_concepts[:3]],
            'concept_connections': {},  # Will be built by knowledge graph
            'synthesis_method': 'rule_based'
        }

    
    def _llm_synthesize_complex_session(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to synthesize complex multi-topic sessions"""
    
        if not self.llm_client or not self.llm_client.is_available():
            self.logger.warning("LLM not available for complex synthesis, falling back to rule-based")
            # Extract concepts for fallback
            all_concepts = []
            all_topics = []
            for result in all_results:
                all_concepts.extend(result.get('learning_concepts', []))
                all_topics.append(result.get('main_topic', 'unknown'))
            return self._rule_based_synthesis(all_concepts, list(set(all_topics)), 'intermediate')
        
        try:
            # Extract key data for synthesis
            all_concepts = []
            all_topics = []
            all_complexity_levels = []
            
            for result in all_results:
                all_concepts.extend(result.get('learning_concepts', []))
                all_topics.append(result.get('main_topic', 'unknown'))
                all_complexity_levels.append(result.get('complexity', 'intermediate'))
            
            # Create synthesis prompt
            unique_concepts = list(dict.fromkeys(all_concepts))  # Remove duplicates, preserve order
            unique_topics = list(set(all_topics))
            primary_complexity = max(set(all_complexity_levels), key=all_complexity_levels.count)
            
            prompt = f"""You are analyzing a comprehensive learning session to identify the knowledge journey and skill development path.

SESSION DATA:
- Key concepts mastered: {', '.join(unique_concepts[:12])}
- Subject areas covered: {', '.join(unique_topics)}
- Learning complexity: {primary_complexity}
- Total materials: {len(all_results)}

Create a learning synthesis that shows HOW these concepts build knowledge:

{{
    "session_learning_theme": "descriptive theme that captures the learning journey",
    "knowledge_progression": ["foundational concept", "building concept", "advanced concept"],
    "learning_path": ["logical step 1", "logical step 2", "logical step 3"],
    "session_complexity": "beginner|intermediate|advanced|expert",
    "learning_goals": ["specific capability 1", "specific capability 2"],
    "next_steps": ["concrete action 1", "concrete action 2", "concrete action 3"],
    "concept_connections": {{"concept1": ["directly_related1", "builds_to2"]}},
    "synthesis_method": "llm_complex"
}}

REQUIREMENTS:
- Learning goals should be specific capabilities, not vague statements
- Next steps must be concrete actions someone can take
- Concept connections should show how ideas build on each other
- Focus on the intellectual journey and skill development

Return valid JSON only."""

            messages = [
                {"role": "system", "content": self._get_analysis_system_message('session_synthesis')},
                {"role": "user", "content": prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.3,
                max_tokens=800
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            synthesis_result = json.loads(response_text)
            
            self.logger.info(f"LLM synthesis completed for complex session with {len(all_results)} captures")
            return synthesis_result
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"LLM synthesis JSON parsing failed: {str(e)}, falling back to rule-based")
            return self._rule_based_synthesis(all_concepts, unique_topics, primary_complexity)
        except Exception as e:
            self.logger.warning(f"LLM synthesis failed: {str(e)}, falling back to rule-based")
            return self._rule_based_synthesis(all_concepts, unique_topics, primary_complexity)
        

    def _combine_all_analysis_results(self, all_results: List[Dict[str, Any]], synthesis: Dict[str, Any], batch_config: Dict[str, Any]) -> Dict[str, Any]:
        """Combine all analysis results into final structure"""
        
        # Aggregate all concepts and entities
        all_learning_concepts = []
        all_key_terms = {}
        all_entities = {}
        all_methodologies = []
        all_skills = []
        
        for result in all_results:
            all_learning_concepts.extend(result.get('learning_concepts', []))
            all_key_terms.update(result.get('key_terms', {}))
            all_entities.update(result.get('entities', {}))
            all_methodologies.extend(result.get('methodologies', []))
            all_skills.extend(result.get('skills', []))
        
        # Remove duplicates while preserving order
        unique_concepts = list(dict.fromkeys(all_learning_concepts))
        unique_methodologies = list(dict.fromkeys(all_methodologies))
        unique_skills = list(dict.fromkeys(all_skills))
        
        # Calculate batch processing metrics
        processing_methods = [r.get('processing_method', 'unknown') for r in all_results]
        method_breakdown = dict(Counter(processing_methods))

        llm_batch_captures = method_breakdown.get('llm_batch', 0)
        cached_captures = method_breakdown.get('cached', 0)
        rule_based_captures = method_breakdown.get('rule_based', 0)
        
         # Calculate actual API calls
        if llm_batch_captures > 0:
            api_calls_made = (llm_batch_captures + self.batch_size - 1) // self.batch_size
            api_calls_made += 1  # Add synthesis call
            self.logger.info(f"   API calls made: {api_calls_made} (including synthesis)")
        else:
            api_calls_made = 0
            self.logger.info(f"   API calls made: 0 (no LLM processing needed)")
        
        # Add synthesis call if we processed any captures with LLM
        if llm_batch_captures > 0:
            api_calls_made += 1  # For synthesis call
        
        # Calculate what it would have been without batching
        api_calls_without_batching = llm_batch_captures  # Each capture would need its own call
        if llm_batch_captures > 0:
            api_calls_without_batching += 1  # Plus synthesis call
        
        # Calculate savings
        api_calls_saved = max(0, api_calls_without_batching - api_calls_made)
        
        # Calculate reduction percentage
        reduction_percent = 0.0
        if api_calls_without_batching > 0:
            reduction_percent = (api_calls_saved / api_calls_without_batching) * 100
        
        # Calculate cache hit rate
        cache_hit_rate = 0.0
        if len(all_results) > 0:
            cache_hit_rate = (cached_captures / len(all_results)) * 100
        
        batch_metrics = {
            'api_calls_made': api_calls_made,
            'api_calls_saved': api_calls_saved,
            'api_calls_reduction_percent': reduction_percent,
            'cache_hit_rate': cache_hit_rate,
            'method_breakdown': method_breakdown,
            'total_captures_processed': len(all_results),
            'batch_size_used': self.batch_size,
            'llm_captures_batched': llm_batch_captures,
            'batches_created': (llm_batch_captures + self.batch_size - 1) // self.batch_size if llm_batch_captures > 0 else 0,
            'processing_breakdown': {
                'llm_batched': llm_batch_captures,
                'cached': cached_captures,
                'rule_based': rule_based_captures
            }
        }

        self.logger.info(f"🔍 FINAL BATCH METRICS CREATED:")
        self.logger.info(f"   API calls saved: {api_calls_saved}")
        self.logger.info(f"   Reduction: {reduction_percent:.1f}%")
        self.logger.info(f"   Cache hit rate: {cache_hit_rate:.1f}%")
    
        print(f"📊 BATCH METRICS FINAL CALCULATION:")
        print(f"   API Calls Made: {api_calls_made}")
        print(f"   API Calls Saved: {api_calls_saved}")
        print(f"   Reduction: {reduction_percent:.1f}%")
        print(f"   Cache Hit Rate: {cache_hit_rate:.1f}%")
        
        # Build final extracted_concepts structure
        extracted_concepts = {
            'learning_concepts': unique_concepts,
            'key_terms': all_key_terms,
            'entities': all_entities,
            'methodologies': unique_methodologies,
            'skills': unique_skills,
            
            'session_theme': synthesis.get('session_learning_theme', 'mixed_topics'),
            'knowledge_progression': synthesis.get('knowledge_progression', []),
            'learning_path': synthesis.get('learning_path', []),
            'knowledge_gaps': synthesis.get('knowledge_gaps', []),
            'learning_goals': synthesis.get('learning_goals', []),
            'next_steps': synthesis.get('next_steps', []),
            'concept_connections': synthesis.get('concept_connections', {}),
            
            'complexity_assessment': {
                'overall_level': synthesis.get('session_complexity', 'intermediate'),
                'per_capture_levels': [r.get('complexity', 'intermediate') for r in all_results]
            },
            
            'topics': [synthesis.get('session_learning_theme', 'general')],
            'key_concepts': unique_concepts[:10],
            
            'capture_analyses': all_results
        }
        
        content_analysis = {
            'method': 'batch_optimized_llm_plus_rules',
            'batch_size': batch_config.get('batch_size', self.batch_size),
            'optimization_metrics': batch_metrics,
            'synthesis_method': synthesis.get('synthesis_method', 'unknown'),
            'confidence': 'high',
            'captures_analyzed': len(all_results),
            'processing_time': datetime.now(timezone.utc).isoformat(),
            'provider': batch_config.get('llm_provider', 'unknown')
        }
        
        return {
            'extracted_concepts': extracted_concepts,
            'content_analysis': content_analysis,
            'batch_metrics': batch_metrics
        }

    
    # Utility methods for rule-based analysis
    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content caching"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _classify_content_type_rules(self, content: str) -> Optional[str]:
        """Classify content type using pattern matching"""
        content_lower = content.lower()
        
        for content_type, patterns in self.content_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, content_lower))
            if matches >= 2:  # Require multiple pattern matches
                return content_type
        return None
    
    def _extract_concepts_rules(self, content: str) -> List[str]:
        """Extract concepts using rule-based patterns"""
        # Simple concept extraction - can be enhanced
        concepts = []
        
        content_lower = content.lower()
    
        # Learning-specific concept patterns
        learning_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s+(?:is|are|means|refers to)',  # Definitions
            r'(?:concept of|principle of|theory of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})',  # Named concepts
            r'(?:understanding|learning|mastering)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})',  # Learning targets
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s+(?:algorithm|method|technique|approach)',  # Technical concepts
            r'(?:key|important|fundamental|core)\s+([a-z]+(?:\s+[a-z]+){0,2})',  # Emphasized concepts
        ]
        
        for pattern in learning_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            concepts.extend([match.strip() for match in matches if len(match.split()) <= 3])
        
        # Look for quoted important terms
        quoted_terms = re.findall(r'"([^"]+)"', content)
        concepts.extend([term for term in quoted_terms if len(term.split()) <= 3])
        
        # Look for capitalized technical terms
        tech_terms = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', content)
        concepts.extend([term for term in tech_terms if len(term) > 3 and len(term) < 20])
        
        # Clean and deduplicate
        cleaned_concepts = []
        for concept in concepts:
            clean = concept.strip().title()
            if clean and len(clean) > 2 and clean not in cleaned_concepts:
                cleaned_concepts.append(clean)
        
        return cleaned_concepts[:12]  # Return top 12 concepts
        

    def _extract_entities_rules(self, content: str) -> Dict[str, str]:
        """Extract entities using simple patterns"""
        entities = {}
        
        # Simple company/product detection
        companies = re.findall(r'\b(?:Google|Microsoft|Apple|Amazon|Facebook|Tesla|Netflix)\b', content)
        for company in companies:
            entities[company] = 'company'
        
        # Programming languages
        languages = re.findall(r'\b(?:Python|JavaScript|Java|React|Vue|Angular|Django)\b', content)
        for lang in languages:
            entities[lang] = 'technology'
        
        return entities
    
    def _extract_key_terms_rules(self, content: str) -> Dict[str, str]:
        """Extract key terms with simple definitions"""
        terms = {}
        
        # Look for definition patterns: "X is/means/refers to Y"
        definition_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+([^.!?]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+means\s+([^.!?]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+refers to\s+([^.!?]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:\s*([^.!?]+)',  # Colon definitions
            r'The term\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([^.!?]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+can be defined as\s+([^.!?]+)',
        ]
        
        for pattern in definition_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for term, definition in matches:
                if len(term.split()) <= 3 and len(definition) > 10:  # Quality filter
                    clean_term = term.strip().title()
                    clean_def = definition.strip().capitalize()
                    if clean_term and clean_def:
                        terms[clean_term] = clean_def
                    
                    if len(terms) >= 8:  # Limit to most important terms
                        break
        
        return terms
    
    def _assess_complexity_rules(self, content: str) -> str:
        """Assess content complexity using simple heuristics"""
        word_count = len(content.split())
        
        # Learning complexity indicators
        beginner_indicators = ['introduction', 'basics', 'getting started', 'overview', 'simple']
        intermediate_indicators = ['implementation', 'practical', 'application', 'building']
        advanced_indicators = ['optimization', 'architecture', 'advanced', 'performance', 'scaling']
        expert_indicators = ['research', 'theoretical', 'novel', 'cutting-edge', 'paradigm']
    
        content_lower = content.lower()
    
        # Count complexity indicators
        beginner_score = sum(1 for term in beginner_indicators if term in content_lower)
        intermediate_score = sum(1 for term in intermediate_indicators if term in content_lower)
        advanced_score = sum(1 for term in advanced_indicators if term in content_lower)
        expert_score = sum(1 for term in expert_indicators if term in content_lower)
    
        # Technical depth indicators
        technical_patterns = [r'\b\w{12,}\b', r'[A-Z]{3,}', r'[\w\-]+\(\)', r'[a-z]+\.[a-z]+']
        technical_score = sum(len(re.findall(pattern, content)) for pattern in technical_patterns)
    
        # Math/formula indicators
        math_score = len(re.findall(r'[\+\-\*/=<>∑∏∫∆]|\b(?:equation|formula|algorithm)\b', content))
    
        # Combine indicators
        if expert_score > 0 or (advanced_score > 2 and technical_score > 20):
            return 'expert'
        elif advanced_score > 0 or (intermediate_score > 2 and technical_score > 10):
            return 'advanced'
        elif intermediate_score > 0 or (word_count > 500 and technical_score > 5):
            return 'intermediate'
        else:
            return 'beginner'
    
    def _classify_learning_type_rules(self, content: str) -> str:
        """Classify learning type using patterns"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['tutorial', 'step by step', 'how to']):
            return 'tutorial'
        elif any(word in content_lower for word in ['example', 'demo', 'sample']):
            return 'example'
        elif any(word in content_lower for word in ['api', 'reference', 'documentation']):
            return 'documentation'
        elif any(word in content_lower for word in ['theory', 'concept', 'principle']):
            return 'theory'
        else:
            return 'explanation'
    
    def _estimate_api_calls(self, capture_categories: Dict[str, List]) -> int:
        """Estimate number of API calls needed"""
        llm_required = len(capture_categories['llm_required'])
        batch_calls = (llm_required + self.batch_size - 1) // self.batch_size if llm_required > 0 else 0
        synthesis_calls = 1 if llm_required > 0 else 0
        return batch_calls + synthesis_calls


    def _get_analysis_system_message(self, analysis_type: str) -> str:
        """Get specific system message for different analysis types"""
    
        system_messages = {
            'batch_analysis': """You are an expert educational content analyzer specializing in extracting learning insights from diverse materials.

Your expertise:
- Identifying core concepts that build foundational understanding
- Recognizing learning objectives and skill development opportunities  
- Assessing complexity levels for different learner backgrounds
- Extracting practical applications and real-world connections
- Creating clear, learner-friendly definitions of technical terms

Always focus on what someone can learn, understand, and apply. Prioritize educational value over surface-level content analysis.""",

        'session_synthesis': """You are an expert learning session synthesizer who creates coherent knowledge journeys from educational content.

Your expertise:
- Identifying how concepts build upon each other in logical progression
- Creating meaningful learning pathways that connect disparate topics
- Recognizing knowledge gaps and prerequisite relationships
- Designing actionable next steps that advance learning goals
- Synthesizing multi-topic sessions into unified learning themes

Focus on the learner's intellectual journey: how concepts connect, what capabilities they're building, and how to continue learning effectively."""
    }
    
        return system_messages.get(analysis_type, system_messages['batch_analysis'])
        
        
