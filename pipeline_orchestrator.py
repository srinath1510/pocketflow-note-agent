#!/usr/bin/env python3
"""
Pipeline Orchestrator: Connects the Flask API to the PocketFlow pipeline
Handles data format conversion and pipeline execution coordination
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
import traceback

from main import NoteGenerationPipeline
from nodes.capture_ingestion import CaptureIngestionNode


class PipelineOrchestrator:
    """
    Orchestrates the execution of the note processing pipeline.
        
    Responsibilities:
    1. Accept minimal standardized input
    2. Execute the complete pipeline 
    3. Return structured results
    
    Does NOT handle:
    - Input format conversion (handled by adapters - coming soon)
    - Browser-specific logic (removed completely)
    - Request parsing (handled by transport layer)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            self.pipeline = NoteGenerationPipeline()
            self.logger.info("Pipeline orchestrator initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline: {str(e)}")
            raise
    
    def _create_error_response(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create consistent error responses with helpful information
        """
        return {
            'status': 'failed',
            'error': {
                'type': type(error).__name__,
                'message': str(error),
                'timestamp': datetime.now(timezone.utc).isoformat()
        },
        'context': {
            'user_id': context.get('user_id', 'unknown'),
            'session_id': context.get('session_id', 'unknown'),
            'input_captures_count': context.get('input_count', 0),
            'pipeline_stage': context.get('stage', 'unknown')
        },
        'pipeline_results': None,
        'suggestions': self._get_error_suggestions(error)
    }

    def _get_error_suggestions(self, error: Exception) -> List[str]:
        """
        Provide helpful suggestions based on error type
        """
        error_type = type(error).__name__
    
        if error_type == 'ValueError':
            return [
                "Check input format matches minimal capture schema",
                "Ensure required fields 'content' and 'user_id' are present",
                "Verify content length is at least 10 characters"
            ]
        elif error_type == 'KeyError':
            return [
                "Missing required field in input data",
                "Check that all captures have 'content' and 'user_id' fields"
            ]
        elif 'LLM' in str(error) or 'API' in str(error):
            return [
                "Check LLM provider API keys are configured",
                "Verify network connectivity",
                "Try again in a few moments"
            ]
        elif 'Neo4j' in str(error):
            return [
                "Check Neo4j database is running",
                "Verify database connection settings",
                "Ensure Neo4j credentials are correct"
            ]
        else:
            return [
                "Check system logs for more details",
                "Verify all required services are running",
                "Contact support if issue persists"
            ]


    def run_pipeline(self, captures: List[Dict[str, Any]], execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the complete pipeline on session notes.
        
        Args:
            captures: List of captures in minimal format:
                {
                    "content": "string",  # Required
                    "user_id": "string",  # Required  
                    "source_url": "string",  # Optional
                    "title": "string",  # Optional
                    "timestamp": "ISO string",  # Optional
                    "intent": "learn|research|reference|archive",  # Optional
                    "user_note": "string"  # Optional
                }
            execution_context: Optional execution metadata
            
        Returns:
            Complete pipeline results
        """
        execution_context = execution_context or {}

        error_context = {
            'input_count': len(captures),
            'stage': 'initialization'
        }
        try:
        # Safety check for batch size
            MAX_CAPTURES_PER_BATCH = 100
            if len(captures) > MAX_CAPTURES_PER_BATCH:
                raise ValueError(f"Too many captures. Maximum {MAX_CAPTURES_PER_BATCH} per batch, got {len(captures)}")
            
            error_context['stage'] = 'validation'
            validated_captures = self._validate_and_normalize_captures(captures)
            
            if not validated_captures:
                raise ValueError("No valid captures provided")
            
            user_id = validated_captures[0].get('user_id', 'unknown')
            session_id = execution_context.get('session_id') or self._generate_session_id(user_id)
            
            # Update error context
            error_context.update({
                'user_id': user_id,
                'session_id': session_id,
                'stage': 'pipeline_execution'
            })

            self.logger.info(f"Starting pipeline execution for user {user_id}")
            self.logger.info(f"Processing {len(validated_captures)} captures")

            pipeline_input = self._convert_to_pipeline_format(validated_captures, session_id)
            
            error_context['stage'] = 'pipeline_processing'
            shared_state = self.pipeline.run(pipeline_input)
            
            error_context['stage'] = 'result_formatting'
            pipeline_results = self._format_pipeline_results(shared_state, execution_context)
            
            self.logger.info(f"Pipeline execution completed successfully")
            return pipeline_results
        
        except ValueError as e:
            # Handle validation errors specifically
            self.logger.error(f"Validation error: {str(e)}")
            return self._create_error_response(e, error_context)
            
        except Exception as e:
            # Handle all other errors
            self.logger.error(f"Pipeline execution failed at stage: {error_context.get('stage', 'unknown')}")
            self.logger.error(f"Error: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            return self._create_error_response(e, error_context)

    
    def _validate_capture_format(self, capture: Dict[str, Any], index: int) -> List[str]:
        """
        More comprehensive validation with specific error messages
        """
        issues = []
    
        # Required field validation
        if not capture.get('content'):
            issues.append(f"Capture {index}: Missing 'content' field")
        elif not isinstance(capture['content'], str):
            issues.append(f"Capture {index}: 'content' must be a string")
        elif len(capture['content'].strip()) < 10:
            issues.append(f"Capture {index}: Content too short (minimum 10 characters)")
    
        if not capture.get('user_id'):
            issues.append(f"Capture {index}: Missing 'user_id' field")
        elif not isinstance(capture['user_id'], str):
            issues.append(f"Capture {index}: 'user_id' must be a string")
        elif len(capture['user_id'].strip()) < 2:
            issues.append(f"Capture {index}: 'user_id' too short (minimum 2 characters)")
    
        # Optional field validation
        if 'intent' in capture:
            valid_intents = ['learn', 'research', 'reference', 'archive']
            if capture['intent'] not in valid_intents:
                issues.append(f"Capture {index}: Invalid intent '{capture['intent']}'. Valid options: {valid_intents}")
    
        if 'source_url' in capture and capture['source_url']:
            if not isinstance(capture['source_url'], str):
                issues.append(f"Capture {index}: 'source_url' must be a string")
        elif capture['source_url'] != 'unknown' and not self._is_valid_url(capture['source_url']):
            issues.append(f"Capture {index}: Invalid URL format")
    
        return issues


    def _is_valid_url(self, url: str) -> bool:
        """Simple URL validation"""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


    def _validate_and_normalize_captures(self, captures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and normalize captures in minimal format
        
        Required fields: content, user_id
        Optional fields: source_url, title, timestamp, intent, user_note
        """
        if not isinstance(captures, list):
            raise ValueError("Captures must be a list")
        
        if not captures:
            raise ValueError("No captures provided")
        
        validated_captures = []
        all_issues = []

        for i, capture in enumerate(captures):
            if not isinstance(capture, dict):
                all_issues.append(f"Capture {i}: Must be a dictionary, got {type(capture).__name__}")
                continue

            if not capture.get('content') or not capture.get('content').strip():
                all_issues.append(f"Capture {i}: Missing or empty 'content' field")
                continue
            
            if not capture.get('user_id') or not capture.get('user_id').strip():
                all_issues.append(f"Capture {i}: Missing or empty 'user_id' field")
                continue
            
            content = capture['content'].strip()
            if len(content) < 10:
                all_issues.append(f"Capture {i}: Content too short (minimum 10 characters, got {len(content)})")
                continue
            
            normalized_capture = {
                'content': capture['content'].strip(),
                'user_id': capture['user_id'].strip(),
                'source_url': capture.get('source_url', 'unknown'),
                'title': capture.get('title', 'Untitled'),
                'timestamp': capture.get('timestamp') or datetime.now(timezone.utc).isoformat(),
                'intent': capture.get('intent', 'learn'),
                'user_note': capture.get('user_note', '')
            }

            # Validate intent
            valid_intents = ['learn', 'research', 'reference', 'archive']
            if normalized_capture['intent'] not in valid_intents:
                normalized_capture['intent'] = 'learn'
        
            validated_captures.append(normalized_capture)

        if all_issues:
            for issue in all_issues:
                self.logger.warning(issue)
            
        if not validated_captures:
            error_message = f"No valid captures found. Issues:\n" + "\n".join(all_issues)
            raise ValueError(error_message)
        
        self.logger.info(f"✅ Validated {len(validated_captures)}/{len(captures)} captures")
        return validated_captures
        

    def _convert_to_pipeline_format(self, minimal_captures: List[Dict[str, Any]], session_id: str) -> List[Dict[str, Any]]:
        """
        Convert minimal capture format to internal pipeline format
        
        This bridges the gap between the clean minimal input and what the existing
        pipeline nodes expect, while removing all the browser extension bloat
        """
        pipeline_captures = []
        
        for capture in minimal_captures:
            domain = self._extract_domain(capture.get('source_url', ''))
            
            content_category = self._map_intent_to_category(capture.get('intent', 'learn'))
            
            knowledge_level = self._estimate_knowledge_level(capture['content'])
            
            pipeline_capture = {
                # Core fields
                'url': capture.get('source_url', 'unknown'),
                'content': capture['content'],
                'timestamp': capture['timestamp'],
                
                # User context
                'user_id': capture['user_id'],
                'session_id': session_id,
                
                # Minimal metadata
                'title': capture.get('title', 'Untitled'),
                'domain': domain,
                'intent': capture.get('intent', 'learn'),
                'user_note': capture.get('user_note', ''),
                
                # Classification (derived from content)
                'content_category': content_category,
                'knowledge_level': knowledge_level,
                
                # Technical metadata (minimal set)
                'word_count': len(capture['content'].split()),
                'content_type': 'text/html',  # Default assumption
                'language': 'en',  # Default assumption
                
                'selected_text': '',  
                'highlights': [],
                'context_before': '',
                'context_after': '',
                'dwell_time': 0, 
                'scroll_depth': 0, 
                'viewport_size': 'unknown', 
                'user_agent': 'minimal_api',
                'trigger': 'api',
                'selection_start_offset': 0,
                'selection_end_offset': 0,
                'relative_position': 0.0,
                
                # Source tracking
                'input_type': 'minimal_capture',
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            pipeline_captures.append(pipeline_capture)
        
        return pipeline_captures

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url or url == 'unknown':
            return 'unknown'
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return 'unknown'

    def _map_intent_to_category(self, intent: str) -> str:
        """Map user intent to content category"""
        intent_mapping = {
            'learn': 'educational',
            'research': 'research_material',
            'reference': 'documentation',
            'archive': 'general'
        }
        return intent_mapping.get(intent, 'general')

    def _estimate_knowledge_level(self, content: str) -> str:
        """Simple heuristic to estimate knowledge level"""
        word_count = len(content.split())
        
        # Count technical indicators
        technical_terms = len([word for word in content.split() if len(word) > 10])
        technical_ratio = technical_terms / max(word_count, 1)
        
        if word_count > 1000 and technical_ratio > 0.05:
            return 'advanced'
        elif word_count > 300 and technical_ratio > 0.02:
            return 'intermediate'
        else:
            return 'basic'

    def _generate_session_id(self, user_id: str) -> str:
        """Generate session ID"""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        return f"{user_id}_session_{timestamp}"

    def _format_pipeline_results(self, shared_state: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format pipeline results for API consumption
        
        Simplified format focused on actual value, not internal complexity
        """
        # Extract key results
        raw_captures = shared_state.get('raw_captures', [])
        extracted_concepts = shared_state.get('extracted_concepts', {})
        knowledge_graph = shared_state.get('knowledge_graph', {})
        historical_connections = shared_state.get('historical_connections', {})
        knowledge_gaps = shared_state.get('knowledge_gaps', [])
        learning_recommendations = shared_state.get('learning_recommendations', [])
        notion_generation = shared_state.get('notion_generation', {})
        pipeline_metadata = shared_state.get('pipeline_metadata', {})

        batch_metrics = None

        if 'batch_metrics' in shared_state:
            batch_metrics = shared_state['batch_metrics']
            print(f"✅ Found batch_metrics in shared_state root: {batch_metrics}")
    
        # Check pipeline_metadata
        elif 'batch_optimization_metrics' in pipeline_metadata:
            batch_metrics = pipeline_metadata['batch_optimization_metrics']
            print(f"✅ Found batch_metrics in pipeline_metadata: {batch_metrics}")
        
        # Check if it's embedded in content_analysis
        elif 'content_analysis' in shared_state and 'optimization_metrics' in shared_state['content_analysis']:
            batch_metrics = shared_state['content_analysis']['optimization_metrics']
            print(f"✅ Found batch_metrics in content_analysis: {batch_metrics}")
        
        else:
            print(f"❌ No batch_metrics found anywhere!")
            print(f"   Available shared_state keys: {list(shared_state.keys())}")
            print(f"   Pipeline metadata keys: {list(pipeline_metadata.keys())}")
            
            # Create default metrics for response
            batch_metrics = {
                'api_calls_made': 0,
                'api_calls_saved': 0,
                'api_calls_reduction_percent': 0,
                'cache_hit_rate': 0,
                'method_breakdown': {},
                'total_captures_processed': len(raw_captures),
                'error': 'batch_metrics_not_found_in_shared_state'
            }

        formatted_results = {
            # Execution metadata
            'status': 'completed',
            'session_id': shared_state.get('session_id'),
            'user_id': shared_state.get('user_id'),
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'processing_time': self._calculate_execution_time(pipeline_metadata),

            'batch_optimization': batch_metrics,
            
            # High-level summary
            'summary': {
                'captures_processed': len(raw_captures),
                'concepts_extracted': len(extracted_concepts.get('learning_concepts', [])),
                'session_theme': extracted_concepts.get('session_theme', 'mixed_topics'),
                'knowledge_connections_found': historical_connections.get('total_connections_found', 0),
                'knowledge_gaps_identified': len(knowledge_gaps),
                'recommendations_generated': len(learning_recommendations),
                'api_calls_saved': batch_metrics.get('api_calls_saved', 0) if batch_metrics else 0
            },
            
            # Core learning results
            'learning_analysis': {
                'key_concepts': extracted_concepts.get('learning_concepts', []),
                'session_theme': extracted_concepts.get('session_theme', 'general'),
                'complexity_level': extracted_concepts.get('complexity_assessment', {}).get('overall_level', 'intermediate'),
                'knowledge_progression': extracted_concepts.get('knowledge_progression', []),
                'learning_goals': extracted_concepts.get('learning_goals', [])
            },
            
            # Knowledge connections
            'knowledge_insights': {
                'historical_connections': historical_connections.get('total_connections_found', 0),
                'knowledge_gaps': knowledge_gaps,
                'learning_recommendations': learning_recommendations,
                'next_steps': self._extract_next_steps(learning_recommendations)
            },
            
            # Generated outputs
            'outputs': {
                'notion_page_created': notion_generation.get('session_page_url') is not None,
                'notion_page_url': notion_generation.get('session_page_url'),
                'knowledge_graph_updated': bool(knowledge_graph),
                'export_available': True
            },
            
            # Pipeline metadata
            'metadata': {
                'pipeline_version': pipeline_metadata.get('pipeline_version', '1.1.0'),
                'nodes_executed': self._count_executed_nodes(shared_state),
                'input_format': 'minimal_capture',
                'batch_metrics': batch_metrics
            }
        }
        
        return formatted_results

    def _calculate_execution_time(self, pipeline_metadata: Dict[str, Any]) -> float:
        """Calculate pipeline execution time"""
        try:
            start_time = pipeline_metadata.get('start_time')
            end_time = pipeline_metadata.get('end_time')
            
            if start_time and end_time:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                return (end_dt - start_dt).total_seconds()
        except Exception:
            pass
        
        return 0.0

    def _extract_next_steps(self, recommendations: List[Dict[str, Any]]) -> List[str]:
        """Extract actionable next steps"""
        next_steps = []
        
        # Extract high-priority recommendations
        high_priority = [rec for rec in recommendations if rec.get('priority') == 'high']
        for rec in high_priority[:3]:  # Top 3
            action = rec.get('action', rec.get('recommended_action', ''))
            if action:
                next_steps.append(action)
        
        # Add medium priority if we don't have enough
        if len(next_steps) < 3:
            medium_priority = [rec for rec in recommendations if rec.get('priority') == 'medium']
            for rec in medium_priority[:3-len(next_steps)]:
                action = rec.get('action', rec.get('recommended_action', ''))
                if action:
                    next_steps.append(action)
        
        # Default next step
        if not next_steps:
            next_steps.append("Continue learning and capturing content")
        
        return next_steps

    def _count_executed_nodes(self, shared_state: Dict[str, Any]) -> int:
        """Count how many pipeline nodes were executed"""
        executed_nodes = 0
        
        if shared_state.get('raw_captures'):
            executed_nodes += 1  # Capture ingestion
        if shared_state.get('extracted_concepts'):
            executed_nodes += 1  # Content analysis
        if shared_state.get('knowledge_graph'):
            executed_nodes += 1  # Knowledge graph
        if shared_state.get('historical_connections'):
            executed_nodes += 1  # Historical analysis
        if shared_state.get('notion_generation'):
            executed_nodes += 1  # Notion generation
        
        return executed_nodes

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get pipeline status"""
        return {
            'status': 'operational',
            'version': '1.1.0-decoupled',
            'input_format': 'minimal_capture',
            'required_fields': ['content', 'user_id'],
            'optional_fields': ['source_url', 'title', 'timestamp', 'intent', 'user_note'],
            'supported_intents': ['learn', 'research', 'reference', 'archive'],
            'max_captures_per_session': 100,
            'estimated_processing_time': '30-60 seconds'
        }


if __name__ == "__main__":
    # Example of minimal input format
    minimal_captures = [
        {
            "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data without being explicitly programmed.",
            "user_id": "researcher_123",
            "source_url": "https://example.com/ml-intro",
            "title": "Introduction to Machine Learning",
            "intent": "learn"
        },
        {
            "content": "Deep learning uses neural networks with multiple layers to model and understand complex patterns in data.",
            "user_id": "researcher_123", 
            "source_url": "https://example.com/deep-learning",
            "title": "Deep Learning Basics",
            "intent": "research",
            "user_note": "Important for my AI project"
        }
    ]
    
    orchestrator = PipelineOrchestrator()
    
    try:
        results = orchestrator.run_pipeline(minimal_captures)
        
        print("✅ Pipeline execution completed!")
        print(f"   Status: {results['status']}")
        print(f"   Captures processed: {results['summary']['captures_processed']}")
        print(f"   Concepts extracted: {results['summary']['concepts_extracted']}")
        print(f"   Session theme: {results['learning_analysis']['session_theme']}")
        print(f"   Processing time: {results['processing_time']:.2f} seconds")
        
        if results['outputs']['notion_page_created']:
            print(f"   Notion page: {results['outputs']['notion_page_url']}")
        
        print(f"\n🎯 Next steps:")
        for step in results['knowledge_insights']['next_steps']:
            print(f"   - {step}")
            
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")