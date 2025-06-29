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
        

    def _format_pipeline_results(self, shared_state: Dict[str, Any], bake_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format pipeline results into a structure suitable for API storage.
        
        Args:
            shared_state: Complete shared_state from pipeline execution
            bake_data: Original bake request metadata
            
        Returns:
            Formatted results for API storage
        """