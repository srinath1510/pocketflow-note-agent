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
    
    Converts API note format → PocketFlow format → Execute pipeline → Return results
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            self.pipeline = NoteGenerationPipeline()
            self.logger.info("Pipeline orchestrator initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline: {str(e)}")
            raise


    def run_pipeline(self, bake_data: Dict[str, Any], session_notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute the complete pipeline on session notes.
        
        Args:
            bake_data: Bake request metadata from API
            session_notes: List of notes from the current session
            
        Returns:
            Complete pipeline results
        """
        bake_id = bake_data.get('bake_id', 'unknown')
        self.logger.info(f"Starting pipeline execution for bake {bake_id} with {len(session_notes)} notes")
        
        try:
            pipeline_input = self._convert_notes_to_pipeline_format(session_notes, bake_data)
            
            shared_state = self.pipeline.run(pipeline_input)
            
            pipeline_results = self._format_pipeline_results(shared_state, bake_data)
            
            self.logger.info(f"Pipeline execution completed successfully for bake {bake_id}")
            return pipeline_results
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed for bake {bake_id}: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            return {
                'bake_id': bake_id,
                'status': 'failed',
                'error': str(e),
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'input_notes_count': len(session_notes),
                'pipeline_results': None,
                'shared_state': None
            }


    def _convert_notes_to_pipeline_format(self, session_notes: List[Dict[str, Any]], bake_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert API note format to the format expected by the 1st node CaptureIngestionNode.
        
        Args:
            session_notes: Notes from API
            bake_data: Bake request metadata
            
        Returns:
            Notes in pipeline format
        """
        self.logger.info(f"Converting {len(session_notes)} notes to pipeline format")
        
        pipeline_captures = []
        
        for i, note in enumerate(session_notes):
            try:
                raw_note = note.get('raw_note', {})
                
                pipeline_capture = {
                    # Required fields for CaptureIngestionNode
                    'url': note.get('url') or raw_note.get('source', {}).get('url', ''),
                    'content': note.get('content_full') or raw_note.get('content', ''),
                    'timestamp': note.get('captured_at') or raw_note.get('metadata', {}).get('captured_at', datetime.now(timezone.utc).isoformat()),
                    
                    'selected_text': raw_note.get('metadata', {}).get('selected_text', ''),
                    'highlights': raw_note.get('highlights', []),
                    'context_before': raw_note.get('metadata', {}).get('context_before', ''),
                    'context_after': raw_note.get('metadata', {}).get('context_after', ''),
                    'dwell_time': raw_note.get('metadata', {}).get('time_on_page', 0),
                    'scroll_depth': raw_note.get('metadata', {}).get('scroll_depth_at_selection', 0),
                    'viewport_size': raw_note.get('metadata', {}).get('viewport_size', 'unknown'),
                    'user_agent': raw_note.get('metadata', {}).get('browser', 'Unknown'),
                    'trigger': raw_note.get('metadata', {}).get('capture_trigger', 'extension'),
                    'intent': raw_note.get('metadata', {}).get('intent', 'general'),
                    
                    'selection_start_offset': raw_note.get('metadata', {}).get('selection_start_offset', 0),
                    'selection_end_offset': raw_note.get('metadata', {}).get('selection_end_offset', 0),
                    'relative_position': raw_note.get('metadata', {}).get('relative_position', 0.0),
                    
                    # Additional metadata for pipeline
                    'api_note_id': note.get('id'),
                    'api_stored_at': note.get('stored_at'),
                    'bake_id': bake_data.get('bake_id')
                }
                
                pipeline_captures.append(pipeline_capture)
                
            except Exception as e:
                self.logger.warning(f"Error converting note {i}: {str(e)}. Skipping note.")
                continue
        
        self.logger.info(f"Successfully converted {len(pipeline_captures)} notes to pipeline format")
        return pipeline_captures
        

    def _format_pipeline_results(self, shared_state: Dict[str, Any], bake_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format pipeline results into a structure suitable for API storage.
        
        Args:
            shared_state: Complete shared_state from pipeline execution
            bake_data: Original bake request metadata
            
        Returns:
            Formatted results for API storage
        """
        bake_id = bake_data.get('bake_id', 'unknown')
        
        raw_captures = shared_state.get('raw_captures', [])
        extracted_concepts = shared_state.get('extracted_concepts', {})
        content_analysis = shared_state.get('content_analysis', {})
        pipeline_metadata = shared_state.get('pipeline_metadata', {})
        
        processing_stats = self._calculate_processing_stats(shared_state, raw_captures, extracted_concepts)
        
        insights = self._generate_processing_insights(raw_captures, extracted_concepts, shared_state)
        
        formatted_results = {
            'bake_id': bake_id,
            'status': pipeline_metadata.get('status', 'completed'),
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'input_notes_count': bake_data.get('total_notes', 0),
            
            'pipeline_metadata': {
                'session_id': shared_state.get('session_id'),
                'pipeline_stage': shared_state.get('pipeline_stage'),
                'execution_time': self._calculate_execution_time(pipeline_metadata),
                'pipeline_version': pipeline_metadata.get('pipeline_version'),
                'nodes_executed': ['capture_ingestion'],
                **pipeline_metadata
            },
            
            'processing_summary': processing_stats,
            'insights': insights,
            'processed_captures': raw_captures,
            'shared_state': shared_state,
            
            'results': {
                'summary': f"Successfully processed {len(raw_captures)} captures through capture ingestion",
                'captures_processed': len(raw_captures),
                'concepts_extracted': len(extracted_concepts.get('key_concepts', [])),
                'session_theme': extracted_concepts.get('session_theme', 'mixed_topics'),
                'topics_identified': extracted_concepts.get('topics', []),
                'content_types_detected': processing_stats.get('content_types_detected', {}),
                'domains_processed': processing_stats.get('domains_processed', []),
                'complexity_level': extracted_concepts.get('complexity_assessment', {}).get('overall_level', 'unknown'),
                'next_steps': 'Ready for historical knowledge retrieval and concept extraction'
            }
        }

        self.logger.info(f"Formatted pipeline results for bake {bake_id}")
        return formatted_results


    def _calculate_processing_stats(self, shared_state: Dict[str, Any], raw_captures: List[Dict[str, Any]], extracted_concepts: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate processing statistics from pipeline results."""
        pipeline_metadata = shared_state.get('pipeline_metadata', {})
        capture_summary = pipeline_metadata.get('capture_ingestion_summary', {})
        content_summary = pipeline_metadata.get('content_analysis_summary', {})
        
        stats = {
            'total_input_captures': capture_summary.get('total_input_captures', 0),
            'successfully_processed': len(raw_captures),
            'processing_success_rate': capture_summary.get('processing_success_rate', 0),
            'content_types_detected': capture_summary.get('content_types_detected', {}),
            'domains_processed': capture_summary.get('domains_processed', []),
            'average_content_length': capture_summary.get('average_content_length', 0),
            'captures_processed': pipeline_metadata.get('captures_processed', 0),

            # Content analysis stats
            'concepts_extracted': content_summary.get('concepts_extracted', 0),
            'entities_found': content_summary.get('entities_found', 0),
            'topics_identified': content_summary.get('topics_identified', 0),
            'analysis_method': content_summary.get('analysis_method', 'unknown'),
            'overall_complexity': content_summary.get('overall_complexity', 'unknown'),
            'session_theme': content_summary.get('session_theme', 'unknown'),
            'llm_provider': content_summary.get('llm_provider', 'unknown')
        }
        
        # Add additional statistics from processed captures
        if raw_captures:
            knowledge_levels = {}
            categories = {}
            
            for capture in raw_captures:
                metadata = capture.get('metadata', {})
                
                # Count knowledge levels
                level = metadata.get('knowledge_level', 'unknown')
                knowledge_levels[level] = knowledge_levels.get(level, 0) + 1
                
                # Count categories
                category = metadata.get('content_category', 'unknown')
                categories[category] = categories.get(category, 0) + 1
            
            stats['knowledge_level_distribution'] = knowledge_levels
            stats['category_distribution'] = categories
            stats['has_code_samples'] = sum(1 for c in raw_captures if c.get('metadata', {}).get('has_code', False))
            stats['has_math_content'] = sum(1 for c in raw_captures if c.get('metadata', {}).get('has_math', False))
            stats['has_data_tables'] = sum(1 for c in raw_captures if c.get('metadata', {}).get('has_data_tables', False))
        
        if extracted_concepts:
            stats['learning_concepts'] = extracted_concepts.get('learning_concepts', [])
            stats['key_terms'] = extracted_concepts.get('key_terms', {})
            stats['methodologies'] = extracted_concepts.get('methodologies', [])
            stats['skills'] = extracted_concepts.get('skills', [])
            stats['session_theme'] = extracted_concepts.get('session_theme', 'mixed_topics')
            stats['learning_goals'] = extracted_concepts.get('learning_goals', [])

        return stats


    def _generate_processing_insights(self, raw_captures: List[Dict[str, Any]], extracted_concepts: Dict[str, Any], shared_state: Dict[str, Any]) -> List[str]:
        """Generate insights about the processed data."""
        insights = []
        
        if not raw_captures:
            insights.append("No captures were successfully processed")
            return insights
        
        if extracted_concepts:
            learning_concepts = extracted_concepts.get('learning_concepts', [])
            session_theme = extracted_concepts.get('session_theme', '')
            learning_goals = extracted_concepts.get('learning_goals', [])
            entities = extracted_concepts.get('entities', {})
            complexity = extracted_concepts.get('complexity_assessment', {}).get('overall_level', 'basic')
            
            # Learning concepts insights
            if learning_concepts:
                insights.append(f"Identified {len(learning_concepts)} learning concepts: {', '.join(learning_concepts[:3])}")
            
            # Session theme insights
            if session_theme and session_theme != 'mixed_topics':
                insights.append(f"Learning session focused on: {session_theme.replace('_', ' ')}")
            
            # Learning goals insights
            if learning_goals and len(learning_goals) > 0:
                primary_goal = learning_goals[0] if learning_goals[0] != 'general_learning' else None
                if primary_goal:
                    insights.append(f"Primary learning objective: {primary_goal.replace('_', ' ')}")
            
            # Entity insights
            if entities:
                entity_types = list(set(entities.values()))
                insights.append(f"Found entities across {len(entity_types)} categories: {', '.join(entity_types[:3])}")
            
            # Complexity insights
            insights.append(f"Content complexity assessed as: {complexity}")
            
            # Learning pattern insights from semantic analysis
            semantic = extracted_concepts.get('semantic_analysis', {})
            if semantic:
                intent = semantic.get('primary_intent', '')
                if intent:
                    insights.append(f"Detected learning focus: {intent.replace('_', ' ')}")
        
        domains = set()
        knowledge_levels = {}
        
        for capture in raw_captures:
            metadata = capture.get('metadata', {})
            domain = metadata.get('domain', 'unknown')
            domains.add(domain)
            
            level = metadata.get('knowledge_level', 'basic')
            knowledge_levels[level] = knowledge_levels.get(level, 0) + 1
        
        insights.append(f"Captured content from {len(domains)} different sources")

        # Generate insights based on patterns
        total_captures = len(raw_captures)

        # Knowledge level insights
        if knowledge_levels:
            if knowledge_levels.get('advanced', 0) > total_captures * 0.3:
                insights.append("High proportion of advanced-level content detected")
            elif knowledge_levels.get('basic', 0) > total_captures * 0.7:
                insights.append("Mostly basic-level content captured")
            else:
                insights.append("Balanced mix of knowledge levels detected")
        
        # Technical content insights
        code_captures = sum(1 for c in raw_captures if c.get('metadata', {}).get('has_code', False))
        if code_captures > 0:
            insights.append(f"Found {code_captures} captures with code samples")
        
        math_captures = sum(1 for c in raw_captures if c.get('metadata', {}).get('has_math', False))
        if math_captures > 0:
            insights.append(f"Found {math_captures} captures with mathematical content")
        
        return insights
        

    def _calculate_execution_time(self, pipeline_metadata: Dict[str, Any]) -> Optional[float]:
        """Calculate pipeline execution time in seconds."""
        try:
            start_time = pipeline_metadata.get('start_time')
            end_time = pipeline_metadata.get('end_time')
            
            if start_time and end_time:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                return (end_dt - start_dt).total_seconds()
        except Exception:
            pass
        
        return None