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


    def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """
        Post-processing: Store analysis results in shared_state for Node 3.
        """