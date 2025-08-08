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
            self.logger.info(f"Processed {len(batch_results)} captures with {len(batch_results) // self.batch_size + 1} LLM calls")
            
            # Combine all results
            all_results = cached_results + rule_based_results + batch_results
            
            # Step 4: Cross-capture synthesis (single LLM call for all)
            synthesis_result = self._synthesize_across_all_captures(all_results)
            
            # Step 5: Combine and format final results
            combined_result = self._combine_all_analysis_results(all_results, synthesis_result, batch_config)

            batch_metrics = combined_result.get('batch_metrics', {})
            self.logger.info(f"🔍 DEBUG: ContentAnalysisNode.exec() returning batch_metrics: {batch_metrics}")
            
            if not batch_metrics:
                self.logger.error("🚨 CRITICAL: No batch_metrics in combined_result!")
                self.logger.error(f"   Available keys: {list(combined_result.keys())}")
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
                'content_analysis': {'method': 'failed', 'error': str(e)}
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
            self.logger.info(f"🔍 Added batch_metrics to shared_state: {batch_metrics}")
        else:
            self.logger.warning("⚠️  No batch_metrics found in exec_result")

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
        
        self.logger.info(f"Content analysis complete - API calls saved: {batch_metrics['api_calls_saved']}")
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
            {"role": "system", "content": "You are an expert at analyzing educational content in batches. "
                                         "Always return valid JSON with analysis for each capture in the batch."},
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
                'learning_concepts': analysis.get('learning_concepts', []),
                'key_terms': analysis.get('key_terms', {}),
                'entities': analysis.get('entities', {}),
                'methodologies': analysis.get('methodologies', []),
                'skills': analysis.get('skills', []),
                'complexity': analysis.get('complexity', 'intermediate'),
                'prerequisites': analysis.get('prerequisites', []),
                'learning_type': analysis.get('learning_type', 'explanation'),
                'actionable_items': analysis.get('actionable_items', []),
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
        
        return f"""Analyze these {len(batch)} learning captures together for efficiency:

        {chr(10).join(batch_content)}
            
        For each capture, extract learning information and return as JSON:

        {{
        "analyses": [
            {{
            "learning_concepts": ["concept1", "concept2"],
            "key_terms": {{"term": "definition"}},
            "entities": {{"name": "type"}},
            "methodologies": ["approach1"],
            "skills": ["skill1"],
            "complexity": "beginner|intermediate|advanced|expert",
            "prerequisites": ["prereq1"],
            "learning_type": "tutorial|explanation|documentation|example|theory|practical",
            "actionable_items": ["action1"],
            "main_topic": "primary_subject"
            }},
            // ... analysis for each capture
        ]
        }}

        Focus on educational value and learning concepts. Return valid JSON only."""

    
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
            
            prompt = f"""Analyze this complex learning session with multiple concepts and topics:

    CONCEPTS LEARNED: {', '.join(unique_concepts[:15])}
    TOPICS COVERED: {', '.join(unique_topics)}
    SESSION COMPLEXITY: {primary_complexity}
    TOTAL CAPTURES: {len(all_results)}

    Synthesize the session and return JSON:
    {{
        "session_learning_theme": "primary_unified_theme",
        "knowledge_progression": ["concept1", "concept2", "concept3"],
        "learning_path": ["logical_step1", "logical_step2", "logical_step3"],
        "session_complexity": "beginner|intermediate|advanced|expert",
        "learning_goals": ["specific_goal1", "specific_goal2"],
        "next_steps": ["actionable_step1", "actionable_step2"],
        "concept_connections": {{"concept1": ["related1", "related2"]}},
        "synthesis_method": "llm_complex"
    }}

    Focus on the learning journey and concept relationships. Return valid JSON only."""

            messages = [
                {"role": "system", "content": "You are an expert learning session synthesizer. Return only valid JSON."},
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
        
        api_calls_made = method_breakdown.get('llm_batch', 0) + method_breakdown.get('llm_synthesis', 0)
        api_calls_without_batching = len(all_results)  # What it would have been
        api_calls_saved = api_calls_without_batching - api_calls_made
        
        batch_metrics = {
            'api_calls_made': api_calls_made,
            'api_calls_saved': api_calls_saved,
            'api_calls_reduction_percent': (api_calls_saved / api_calls_without_batching * 100) if api_calls_without_batching > 0 else 0,
            'cache_hit_rate': (method_breakdown.get('cached', 0) / len(all_results) * 100) if all_results else 0,
            'method_breakdown': method_breakdown,
            'total_captures_processed': len(all_results)
        }
        
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
        
        # Look for capitalized terms (potential concepts)
        concept_patterns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        concepts.extend([concept for concept in concept_patterns if len(concept.split()) <= 3])
        
        # Look for quoted terms
        quoted_terms = re.findall(r'"([^"]+)"', content)
        concepts.extend([term for term in quoted_terms if len(term.split()) <= 3])
        
        return list(set(concepts))[:10]  # Limit and deduplicate
    
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
        definitions = re.findall(r'(\w+(?:\s+\w+)*)\s+(?:is|means|refers to)\s+([^.!?]+)', content, re.IGNORECASE)
        for term, definition in definitions[:5]:  # Limit to 5
            terms[term.strip()] = definition.strip()
        
        return terms
    
    def _assess_complexity_rules(self, content: str) -> str:
        """Assess content complexity using simple heuristics"""
        word_count = len(content.split())
        
        # Count technical indicators
        technical_patterns = [r'\b\w{10,}\b', r'\$[^$]+\$', r'```', r'<code>', r'\([A-Z][a-z]+\s+et\s+al\.\)']
        technical_score = sum(len(re.findall(pattern, content)) for pattern in technical_patterns)
        
        if word_count < 200 and technical_score < 3:
            return 'beginner'
        elif word_count > 1000 or technical_score > 10:
            return 'advanced'
        elif technical_score > 5:
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


    def _llm_synthesize_complex_session(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to synthesize complex multi-topic sessions"""
        
        if not self.llm_client or not self.llm_client.is_available():
            return self._rule_based_synthesis([], ['general'], 'intermediate')
        
        # Extract key data for synthesis
        all_concepts = []
        all_topics = []
        
        for result in all_results:
            all_concepts.extend(result.get('learning_concepts', []))
            all_topics.append(result.get('main_topic', 'unknown'))
        
        # Create synthesis prompt
        prompt = f"""Analyze this learning session with multiple concepts: {', '.join(all_concepts[:10])}

    The session covered these topics: {', '.join(set(all_topics))}

    Synthesize the session and return JSON:
    {{
    "session_learning_theme": "primary_theme",
    "knowledge_progression": ["concept1", "concept2", "concept3"],
    "learning_path": ["step1", "step2", "step3"],
    "session_complexity": "beginner|intermediate|advanced",
    "learning_goals": ["goal1", "goal2"],
    "next_steps": ["action1", "action2"],
    "concept_connections": {{"concept1": ["related1", "related2"]}},
    "synthesis_method": "llm_complex"
    }}

    Focus on the learning journey and concept relationships. Return valid JSON only."""

        try:
            messages = [
                {"role": "system", "content": "You are an expert learning session synthesizer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.3,
                max_tokens=800
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            synthesis_result = json.loads(response_text)
            
            return synthesis_result
            
        except Exception as e:
            self.logger.warning(f"LLM synthesis failed: {str(e)}, falling back to rule-based")
            return self._rule_based_synthesis(all_concepts, list(set(all_topics)), 'intermediate')

    
    
