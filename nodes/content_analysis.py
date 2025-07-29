#!/usr/bin/env python3
"""
Content Analysis Node: Extracts concepts, entities, and semantic meaning from processed captures
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from collections import Counter
import os

from pocketflow import Node as BaseNode
from .llm_client import get_llm_client


class ContentAnalysisNode(BaseNode):
    """
    Node 2: Content Analysis & Concept Extraction
    
    Purpose: Extract key concepts, entities, topics, and semantic meaning from captures
    
    Input: shared_state['raw_captures'] from Capture Ingestion node. 
    Process: LLM analysis + entity extraction + topic classification + concept hierarchy
    Output: shared_state['extracted_concepts'] and shared_state['content_analysis']
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.llm_client = None
        self.use_llm = False
        self._initialize_llm()
    

    def _initialize_llm(self):
        """Initialize LLM client (tries multiple providers)"""
        try:
            preferred_provider = os.getenv('LLM_PROVIDER')  # 'anthropic', etc.
            
            self.llm_client = get_llm_client(preferred_provider)
            self.provider_name = self.llm_client.get_provider_name()
            
            self.logger.info(f"LLM client initialized with provider: {self.provider_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize any LLM provider: {str(e)}")
            self.logger.error("Please configure at least one of:")
            self.logger.error("- ANTHROPIC_API_KEY for Anthropic Claude")
            raise RuntimeError(f"No LLM providers available: {str(e)}")

    
    def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare for content analysis by validating inputs and LLM availability.
        """
        self.logger.info("Starting Content Analysis prep phase")

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
        
        valid_captures = []
        for i, capture in enumerate(raw_captures):
            if isinstance(capture, dict) and 'content' in capture and capture['content'].strip():
                valid_captures.append(capture)
            else:
                self.logger.warning(f"Skipping invalid capture {i}: missing or empty content")
        
        analysis_config = {
            'total_captures': len(raw_captures),
            'valid_captures': len(valid_captures),
            'combined_content_length': sum(len(c['content']) for c in valid_captures),
            'llm_provider': self.provider_name,
            'model_recommendations': self.llm_client.get_model_recommendations()
        }
        
        self.logger.info(f"Content analysis prep complete: {len(valid_captures)} valid captures using {self.provider_name}")
        return {
            'captures_to_analyze': valid_captures,
            'analysis_config': analysis_config
        }

    
    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution: Analyze captures using LLM for learning concept extraction.
        """
        self.logger.info("Starting LLM-powered content analysis")

        captures = prep_result.get('captures_to_analyze', [])
        config = prep_result.get('analysis_config', {})

        if 'error' in prep_result:
            return {'error': prep_result['error'], 'extracted_concepts': {}, 'content_analysis': {}}
        
        if not captures:
            return {'extracted_concepts': {}, 'content_analysis': {}}

        try:
            # Analyze each capture individually
            individual_analyses = []
            for i, capture in enumerate(captures):
                self.logger.debug(f"Analyzing capture {i+1}/{len(captures)}")
                analysis = self._analyze_single_capture(capture, i)
                individual_analyses.append(analysis)
            
            # cross-capture synthesis
            synthesis_result = self._synthesize_across_captures(individual_analyses, captures)
    
            combined_result = self._combine_analysis_results(individual_analyses, synthesis_result, config)
            
            self.logger.info(f"LLM analysis complete: extracted {len(combined_result.get('extracted_concepts', {}).get('learning_concepts', []))} learning concepts")
            return combined_result
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {str(e)}")
            return {
                'error': f"LLM analysis failed: {str(e)}",
                'extracted_concepts': {},
                'content_analysis': {'method': 'failed', 'error': str(e)}
            }


    def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """
        Post-processing: Store analysis results in shared_state for the next node.
        """
        self.logger.info("Starting Content Analysis post-execution phase")

        shared_state['extracted_concepts'] = exec_result.get('extracted_concepts', {})
        shared_state['content_analysis'] = exec_result.get('content_analysis', {})

        concepts = exec_result.get('extracted_concepts', {})
        processing_summary = {
            'learning_concepts_extracted': len(concepts.get('learning_concepts', [])),
            'entities_found': len(concepts.get('entities', {})),
            'topics_identified': len(concepts.get('topics', [])),
            'analysis_method': 'llm_powered',
            'overall_complexity': concepts.get('complexity_assessment', {}).get('overall_level', 'unknown'),
            'learning_objectives_count': len(concepts.get('learning_objectives', [])),
            'knowledge_domains_count': len(concepts.get('knowledge_domains', []))
        }

        shared_state['pipeline_metadata']['content_analysis_summary'] = processing_summary
        shared_state['pipeline_metadata']['content_analysis_end'] = datetime.now(timezone.utc).isoformat()
        
        self.logger.info("Content analysis results stored in shared_state")
        return "default"

    
    def _analyze_single_capture(self, capture: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Analyze a single capture for learning concepts using LLM."""
        
        content = capture['content']
        url = capture.get('url', 'Unknown URL')
        selected_text = capture.get('metadata', {}).get('selected_text', '')
        
        # focused prompt for single capture analysis
        prompt = f"""Analyze this learning content and extract key learning information:

        URL: {url}
        Selected Text: "{selected_text}"
        Full Content: {content[:1500]}...

        Extract and return JSON with:
        1. "learning_concepts": Core concepts being taught/learned (array of strings)
        2. "key_terms": Important terminology and definitions (object: term -> definition)
        3. "entities": People, companies, technologies, tools mentioned (object: name -> type)
        4. "methodologies": Approaches, frameworks, processes described (array)
        5. "skills": Specific skills or competencies involved (array)
        6. "complexity": learning complexity (beginner/intermediate/advanced/expert)
        7. "prerequisites": What knowledge is assumed/required (array)
        8. "learning_type": type of learning content (tutorial, explanation, documentation, example, theory, practical)
        9. "actionable_items": Concrete things a learner could do/try (array)
        10. "main_topic": The primary subject area being learned

        Focus on educational/learning value. Return only valid JSON."""

        try:
            # Use provider-agnostic client
            messages = [
                {"role": "system", "content": "You are an expert at analyzing educational content and extracting learning concepts. Always return valid JSON focused on learning value."},
                {"role": "user", "content": prompt}
            ]
            
            # Set provider-specific defaults
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.2,
                max_tokens=800
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            result = json.loads(response_text)
            result['capture_index'] = index
            result['capture_id'] = capture.get('id', f'capture_{index}')
            return result
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze capture {index}: {str(e)}")
            return {
                'capture_index': index,
                'capture_id': capture.get('id', f'capture_{index}'),
                'error': str(e),
                'learning_concepts': [],
                'key_terms': {},
                'entities': {},
                'main_topic': 'unknown'
            }


    def _synthesize_across_captures(self, individual_analyses: List[Dict[str, Any]], captures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize learning insights across all captures using LLM."""
        
        # Prepare summary of individual analyses
        analysis_summary = []
        for i, analysis in enumerate(individual_analyses):
            summary = {
                'capture': i + 1,
                'main_topic': analysis.get('main_topic', 'unknown'),
                'learning_concepts': analysis.get('learning_concepts', [])[:3],  # Top 3
                'complexity': analysis.get('complexity', 'unknown'),
                'learning_type': analysis.get('learning_type', 'unknown')
            }
            analysis_summary.append(summary)
        
        # Create synthesis prompt
        prompt = f"""Analyze this learning session where a user captured {len(captures)} pieces of content:

        Individual Content Analysis:
        {json.dumps(analysis_summary, indent=2)}

        Synthesize across all captures and return JSON with:
        1. "session_learning_theme": Overall theme/topic of this learning session
        2. "knowledge_progression": How concepts build on each other (array of steps)
        3. "learning_path": Suggested order for learning these concepts (array)
        4. "knowledge_gaps": Important related concepts not covered (array)
        5. "session_complexity": Overall session difficulty (beginner/intermediate/advanced/expert)
        6. "learning_goals": What the user is trying to achieve (inferred goals)
        7. "next_steps": Recommended follow-up learning (array)
        8. "concept_connections": How the main concepts relate (object describing relationships)
        9. "practical_applications": Real-world uses for this knowledge (array)
        10. "mastery_indicators": How to know if concepts are understood (array)

        Focus on the learning journey and knowledge building. Return only valid JSON."""

        try:
            messages = [
                {"role": "system", "content": "You are an expert learning analyst who understands how knowledge builds across multiple learning resources."},
                {"role": "user", "content": prompt}
            ]
            
            # Set provider-specific defaults
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.3,
                max_tokens=1000
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            return json.loads(response_text)
            
        except Exception as e:
            self.logger.warning(f"Failed to synthesize across captures: {str(e)}")
            return {
                'session_learning_theme': 'mixed_topics',
                'session_complexity': 'intermediate',
                'learning_goals': ['general_learning'],
                'error': str(e)
            }


    def _combine_analysis_results(self, individual_analyses: List[Dict[str, Any]], synthesis: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Combine individual and synthesis results into final structure."""
        
        all_learning_concepts = []
        all_key_terms = {}
        all_entities = {}
        all_methodologies = []
        all_skills = []
        all_actionable_items = []
        
        for analysis in individual_analyses:
            all_learning_concepts.extend(analysis.get('learning_concepts', []))
            all_key_terms.update(analysis.get('key_terms', {}))
            all_entities.update(analysis.get('entities', {}))
            all_methodologies.extend(analysis.get('methodologies', []))
            all_skills.extend(analysis.get('skills', []))
            all_actionable_items.extend(analysis.get('actionable_items', []))
        
        # remove duplicates while preserving order
        unique_concepts = list(dict.fromkeys(all_learning_concepts))
        unique_methodologies = list(dict.fromkeys(all_methodologies))
        unique_skills = list(dict.fromkeys(all_skills))
        unique_actionable = list(dict.fromkeys(all_actionable_items))
        
        # Build final extracted_concepts structure
        extracted_concepts = {
            'learning_concepts': unique_concepts,
            'key_terms': all_key_terms,
            'entities': all_entities,
            'methodologies': unique_methodologies,
            'skills': unique_skills,
            'actionable_items': unique_actionable,
            
            'session_theme': synthesis.get('session_learning_theme', 'mixed_topics'),
            'knowledge_progression': synthesis.get('knowledge_progression', []),
            'learning_path': synthesis.get('learning_path', []),
            'knowledge_gaps': synthesis.get('knowledge_gaps', []),
            'learning_goals': synthesis.get('learning_goals', []),
            'next_steps': synthesis.get('next_steps', []),
            'concept_connections': synthesis.get('concept_connections', {}),
            'practical_applications': synthesis.get('practical_applications', []),
            'mastery_indicators': synthesis.get('mastery_indicators', []),
            
            # Complexity assessment
            'complexity_assessment': {
                'overall_level': synthesis.get('session_complexity', 'intermediate'),
                'per_capture_levels': [a.get('complexity', 'intermediate') for a in individual_analyses]
            },
            
            'topics': [synthesis.get('session_learning_theme', 'general')],
            'key_concepts': unique_concepts[:10],  # Top 10 for compatibility
            
            'capture_analyses': individual_analyses
        }
        
        content_analysis = {
            'method': 'llm_powered',
            'model_used': config.get('llm_model', 'gpt-3.5-turbo'),
            'confidence': 'high',
            'captures_analyzed': len(individual_analyses),
            'synthesis_performed': True,
            'processing_time': datetime.now(timezone.utc).isoformat(),
            'provider': config.get('llm_provider', 'unknown')
        }
        
        return {
            'extracted_concepts': extracted_concepts,
            'content_analysis': content_analysis
        }
