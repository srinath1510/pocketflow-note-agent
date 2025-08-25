#!/usr/bin/env python3
"""
Capture Ingestion Node: This node handles the initial processing and validation of raw browsing data
from Chrome extension captures, preparing them for downstream analysis.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs
import re

from bs4 import BeautifulSoup
import html2text
from dateutil import parser as date_parser
import validators

from pocketflow import Node as BaseNode

class CaptureIngestionNode(BaseNode):
    """
    Capture Ingestion Node
    
    Purpose: Process minimal capture input and prepare for AI analysis
    
    Input: Minimal capture format from shared_state['raw_input']:
        [
            {
                "content": "string",  # Required: The actual content
                "user_id": "string",  # Required: User identifier
                "source_url": "string",  # Optional: Source URL
                "title": "string",  # Optional: Content title
                "timestamp": "ISO string",  # Optional: When captured
                "intent": "learn|research|reference|archive",  # Optional: User intent
                "user_note": "string"  # Optional: User's personal note
            }
        ]
    
    Process: Clean, normalize, and enrich with AI-ready metadata
    Output: Structured captures in shared_state['raw_captures']
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # HTML to text converter for content cleaning
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0

        # Simple content classification patterns
        self.content_patterns = {
            'research_paper': [
                r'abstract\s*:?\s*\n',
                r'references\s*:?\s*\n', 
                r'doi\s*:?\s*10\.',
                r'arxiv\.org',
                r'pubmed\.ncbi\.nlm\.nih\.gov'
            ],
            'documentation': [
                r'api\s+reference',
                r'getting\s+started',
                r'installation\s+guide',
                r'docs?\.',
                r'github\.io'
            ],
            'tutorial': [
                r'step\s+\d+',
                r'tutorial',
                r'how\s+to',
                r'beginner.s+guide'
            ],
            'educational': [
                r'learn\s+about',
                r'introduction\s+to',
                r'basics?\s+of',
                r'fundamentals?'
            ]
        }

    def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare for capture ingestion by validating minimal input format
        """
        self.logger.info("📥 Preparing Capture Ingestion (Minimal Format)")
        
        shared_state.setdefault('pipeline_metadata', {})
        shared_state['pipeline_metadata']['capture_ingestion_start'] = datetime.now(timezone.utc).isoformat()

        raw_input = shared_state.get('raw_input', [])
        
        if not raw_input:
            self.logger.error("No raw input data found in shared state")
            return {'error': 'No raw input data', 'captures_to_process': []}
        
        if not isinstance(raw_input, list):
            raw_input = [raw_input]
        
        valid_captures = []
        validation_issues = []
        
        for i, capture in enumerate(raw_input):
            issues = self._validate_minimal_capture(capture, i)
            if issues:
                validation_issues.extend(issues)
            else:
                valid_captures.append(capture)
        
        if validation_issues:
            for issue in validation_issues:
                self.logger.warning(issue)
        
        validation_summary = {
            'total_input': len(raw_input),
            'valid_captures': len(valid_captures),
            'validation_issues': len(validation_issues),
            'success_rate': len(valid_captures) / len(raw_input) if raw_input else 0
        }
        
        self.logger.info(f"✅ Validation complete: {len(valid_captures)}/{len(raw_input)} captures valid")
        
        return {
            'captures_to_process': valid_captures,
            'validation_summary': validation_summary,
            'validation_issues': validation_issues
        }

    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution: Process minimal captures into AI-ready format
        """
        if 'error' in prep_result:
            return prep_result
            
        self.logger.info("🔄 Processing minimal captures")
        
        captures_to_process = prep_result.get('captures_to_process', [])
        processed_captures = []
        processing_errors = []
        
        for i, minimal_capture in enumerate(captures_to_process):
            try:
                self.logger.debug(f"Processing capture {i+1}/{len(captures_to_process)}")
                processed_capture = self._process_minimal_capture(minimal_capture, i)
                processed_captures.append(processed_capture)
                
            except Exception as e:
                error_msg = f"Error processing capture {i}: {str(e)}"
                self.logger.error(error_msg)
                processing_errors.append(error_msg)
                continue
        
        processing_summary = {
            'input_captures': len(captures_to_process),
            'successfully_processed': len(processed_captures),
            'processing_errors': len(processing_errors),
            'success_rate': len(processed_captures) / len(captures_to_process) if captures_to_process else 0
        }
        
        self.logger.info(f"✅ Processing complete: {len(processed_captures)} captures ready for analysis")
        
        return {
            'processed_captures': processed_captures,
            'processing_summary': processing_summary,
            'processing_errors': processing_errors,
            'validation_summary': prep_result['validation_summary']
        }

    def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """
        Post-processing: Store processed captures and metadata
        """
        self.logger.info("📋 Finalizing Capture Ingestion")
        
        if 'error' in exec_result:
            shared_state['capture_ingestion_error'] = exec_result['error']
            return "error"
        
        processed_captures = exec_result.get('processed_captures', [])
        
        # Store processed captures for downstream nodes
        shared_state['raw_captures'] = processed_captures
        
        # Create comprehensive summary
        processing_summary = exec_result.get('processing_summary', {})
        validation_summary = exec_result.get('validation_summary', {})
        
        combined_summary = {
            # Input statistics
            'total_input_captures': validation_summary.get('total_input', 0),
            'valid_input_captures': validation_summary.get('valid_captures', 0),
            'successfully_processed': processing_summary.get('successfully_processed', 0),
            'processing_success_rate': processing_summary.get('success_rate', 0),
            
            # Content analysis
            'content_types_detected': self._analyze_content_types(processed_captures),
            'domains_processed': self._extract_domains(processed_captures),
            'user_intents': self._analyze_user_intents(processed_captures),
            'average_content_length': self._calculate_average_content_length(processed_captures),
            
            # Metadata
            'input_format': 'minimal_capture',
            'bloat_removed': [
                'browser_fingerprinting', 'viewport_tracking', 'scroll_depth_monitoring',
                'dwell_time_tracking', 'selection_precision', 'meaningless_metadata'
            ]
        }
        
        # Store in pipeline metadata
        shared_state['pipeline_metadata']['capture_ingestion_summary'] = combined_summary
        shared_state['pipeline_metadata']['capture_ingestion_end'] = datetime.now(timezone.utc).isoformat()
        shared_state['pipeline_metadata']['captures_processed'] = len(processed_captures)
        
        self.logger.info("✅ Capture Ingestion complete - ready for Content Analysis")
        return "default"

    def _validate_minimal_capture(self, capture: Dict[str, Any], index: int) -> List[str]:
        """
        Validate a single minimal capture
        
        Returns list of validation issues (empty if valid)
        """
        issues = []
        
        # Check required fields
        if not capture.get('content'):
            issues.append(f"Capture {index}: Missing or empty 'content' field")
        elif len(capture['content'].strip()) < 10:
            issues.append(f"Capture {index}: Content too short (minimum 10 characters)")
        
        if not capture.get('user_id'):
            issues.append(f"Capture {index}: Missing or empty 'user_id' field")
        elif len(capture['user_id'].strip()) < 2:
            issues.append(f"Capture {index}: user_id too short")
        
        # Validate optional fields if present
        if 'intent' in capture:
            valid_intents = ['learn', 'research', 'reference', 'archive']
            if capture['intent'] not in valid_intents:
                issues.append(f"Capture {index}: Invalid intent '{capture['intent']}'. Must be one of: {valid_intents}")
        
        if 'source_url' in capture and capture['source_url']:
            if not self._is_valid_url(capture['source_url']):
                issues.append(f"Capture {index}: Invalid source_url format")
        
        return issues

    def _process_minimal_capture(self, minimal_capture: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Process a single minimal capture into AI-ready format
        
        Takes minimal input and enriches it with metadata needed for AI analysis
        """
        # Extract core data
        content = minimal_capture['content'].strip()
        user_id = minimal_capture['user_id'].strip()
        source_url = minimal_capture.get('source_url', 'unknown')
        title = minimal_capture.get('title', 'Untitled')
        timestamp = minimal_capture.get('timestamp')
        intent = minimal_capture.get('intent', 'learn')
        user_note = minimal_capture.get('user_note', '')
        
        # Parse and normalize timestamp
        normalized_timestamp = self._parse_timestamp(timestamp)
        
        # Generate capture ID
        capture_id = self._generate_capture_id(user_id, normalized_timestamp, index)
        
        # Clean and process content
        cleaned_content = self._clean_content(content)
        
        # Extract metadata from content and context
        content_metadata = self._extract_content_metadata(cleaned_content, title, source_url)
        
        # Classify content based on patterns and intent
        content_category = self._classify_content(cleaned_content, title, source_url, intent)
        
        # Estimate knowledge level
        knowledge_level = self._estimate_knowledge_level(cleaned_content, content_metadata)
        
        # Create processed capture
        processed_capture = {
            # Core identification
            'id': capture_id,
            'user_id': user_id,
            'session_id': minimal_capture.get('session_id'),  # Added by orchestrator
            
            # Content data
            'content': cleaned_content,
            'title': title,
            'url': source_url,
            
            # User context
            'intent': intent,
            'user_note': user_note,
            
            # Metadata for AI analysis
            'metadata': {
                # Core metadata
                'capture_id': capture_id,
                'timestamp': normalized_timestamp.isoformat(),
                'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                
                # Content classification
                'content_category': content_category,
                'knowledge_level': knowledge_level,
                'estimated_reading_time': content_metadata['estimated_reading_time'],
                
                # Source information
                'page_title': title,
                'domain': content_metadata['domain'],
                'source_type': self._classify_source_type(source_url),
                
                # Content structure
                'word_count': content_metadata['word_count'],
                'paragraph_count': content_metadata['paragraph_count'],
                'has_structured_content': content_metadata['has_structured_content'],
                
                # Technical content indicators (AI can detect these)
                'likely_has_code': content_metadata['likely_has_code'],
                'likely_has_math': content_metadata['likely_has_math'],
                'likely_technical': content_metadata['likely_technical'],
                
                # Processing metadata
                'input_format': 'minimal_capture',
                'content_cleaned': True,
                'ready_for_ai_analysis': True
            }
        }
        
        return processed_capture

    def _parse_timestamp(self, timestamp_input: Optional[str]) -> datetime:
        """Parse timestamp from various formats"""
        if not timestamp_input:
            return datetime.now(timezone.utc)
        
        try:
            # Try ISO format first
            if isinstance(timestamp_input, str):
                return date_parser.parse(timestamp_input)
            elif isinstance(timestamp_input, (int, float)):
                # Handle Unix timestamp (seconds or milliseconds)
                if timestamp_input > 1e12:  # Milliseconds
                    timestamp_input = timestamp_input / 1000
                return datetime.fromtimestamp(timestamp_input, tz=timezone.utc)
            else:
                return datetime.now(timezone.utc)
        except Exception:
            self.logger.warning(f"Could not parse timestamp: {timestamp_input}")
            return datetime.now(timezone.utc)

    def _generate_capture_id(self, user_id: str, timestamp: datetime, index: int) -> str:
        """Generate unique capture ID"""
        timestamp_ms = int(timestamp.timestamp() * 1000)
        return f"{user_id}_{timestamp_ms}_{index:03d}"

    def _clean_content(self, content: str) -> str:
        """Clean content for AI analysis"""
        try:
            # Check if content contains HTML
            if '<' in content and '>' in content:
                # Use BeautifulSoup to clean HTML
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()
                
                # Convert to clean text
                cleaned = self.html_converter.handle(str(soup))
            else:
                # Plain text content
                cleaned = content
            
            # Clean up whitespace and formatting
            cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)  # Multiple newlines to double
            cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Multiple spaces to single
            cleaned = cleaned.strip()
            
            return cleaned
            
        except Exception as e:
            self.logger.warning(f"Content cleaning failed: {e}")
            return content.strip()

    def _extract_content_metadata(self, content: str, title: str, source_url: str) -> Dict[str, Any]:
        """Extract metadata from content for AI analysis"""
        
        words = content.split()
        word_count = len(words)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Estimate reading time (average 200 words per minute)
        reading_time_minutes = max(1, word_count / 200)
        
        # Extract domain
        domain = self._extract_domain(source_url)
        
        # Analyze content structure
        has_structured_content = self._has_structured_content(content)
        
        # Simple technical content detection
        likely_has_code = self._likely_contains_code(content)
        likely_has_math = self._likely_contains_math(content)
        likely_technical = self._likely_technical_content(content, domain)
        
        return {
            'word_count': word_count,
            'paragraph_count': len(paragraphs),
            'estimated_reading_time': reading_time_minutes,
            'domain': domain,
            'has_structured_content': has_structured_content,
            'likely_has_code': likely_has_code,
            'likely_has_math': likely_has_math,
            'likely_technical': likely_technical
        }

    def _classify_content(self, content: str, title: str, source_url: str, intent: str) -> str:
        """Classify content based on patterns and context"""
        
        # Use intent as primary signal
        if intent in ['research', 'reference']:
            # Check for research patterns
            if self._matches_patterns(content + ' ' + title, self.content_patterns['research_paper']):
                return 'research_paper'
            elif self._matches_patterns(content + ' ' + title, self.content_patterns['documentation']):
                return 'documentation'
            else:
                return 'reference_material'
        
        elif intent == 'learn':
            # Educational content
            if self._matches_patterns(content + ' ' + title, self.content_patterns['tutorial']):
                return 'tutorial'
            elif self._matches_patterns(content + ' ' + title, self.content_patterns['educational']):
                return 'educational'
            else:
                return 'learning_material'
        
        else:
            # Default classification based on content patterns
            for category, patterns in self.content_patterns.items():
                if self._matches_patterns(content + ' ' + title, patterns):
                    return category
            
            return 'general'

    def _estimate_knowledge_level(self, content: str, metadata: Dict[str, Any]) -> str:
        """Estimate required knowledge level"""
        
        word_count = metadata['word_count']
        likely_technical = metadata['likely_technical']
        
        # Simple heuristics
        if likely_technical and word_count > 1000:
            return 'advanced'
        elif likely_technical or word_count > 500:
            return 'intermediate'
        else:
            return 'basic'

    # Helper methods
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            return validators.url(url) or url in ['unknown', '']
        except Exception:
            return False

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url or url == 'unknown':
            return 'unknown'
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return 'unknown'

    def _classify_source_type(self, url: str) -> str:
        """Classify source type based on URL"""
        if not url or url == 'unknown':
            return 'unknown'
        
        domain = self._extract_domain(url).lower()
        
        # Academic sources
        if domain.endswith('.edu') or 'arxiv' in domain or 'pubmed' in domain:
            return 'academic'
        
        # Documentation sites
        if any(term in domain for term in ['docs', 'documentation', 'github.io']):
            return 'documentation'
        
        # News sites
        if any(term in domain for term in ['news', 'times', 'post', 'guardian', 'reuters', 'cnn', 'bbc']):
            return 'news'
        
        # Blog platforms
        if any(term in domain for term in ['medium.com', 'dev.to', 'blog', 'wordpress']):
            return 'blog'
        
        return 'website'

    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the given patterns"""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in patterns)

    def _has_structured_content(self, content: str) -> bool:
        """Check if content has structured elements"""
        structure_indicators = [
            r'^#+\s',  # Markdown headers
            r'^\d+\.',  # Numbered lists
            r'^[•\-\*]\s',  # Bullet points
            r'\n\s*\n',  # Paragraph breaks
        ]
        return any(re.search(pattern, content, re.MULTILINE) for pattern in structure_indicators)

    def _likely_contains_code(self, content: str) -> bool:
        """Simple heuristic to detect code content"""
        code_indicators = [
            r'```',  # Code blocks
            r'def\s+\w+\(',  # Python functions
            r'function\s+\w+\(',  # JavaScript functions
            r'import\s+\w+',  # Import statements
            r'#include\s*<',  # C/C++ includes
            r'<[a-zA-Z]+[^>]*>',  # HTML tags
        ]
        return any(re.search(pattern, content) for pattern in code_indicators)

    def _likely_contains_math(self, content: str) -> bool:
        """Simple heuristic to detect mathematical content"""
        math_indicators = [
            r'\$[^$]+\$',  # LaTeX math
            r'\\[a-zA-Z]+\{',  # LaTeX commands
            r'\b(?:equation|theorem|proof|lemma)\b',  # Math terms
            r'[∀∃∈∉∪∩⊂⊃∑∏∫]',  # Math symbols
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in math_indicators)

    def _likely_technical_content(self, content: str, domain: str) -> bool:
        """Determine if content is likely technical"""
        
        # Technical domains
        technical_domains = ['github.com', 'stackoverflow.com', 'docs.', 'api.', 'developer.']
        if any(tech_domain in domain for tech_domain in technical_domains):
            return True
        
        # Technical vocabulary density
        technical_terms = len(re.findall(r'\b[A-Z]{2,}\b|\b\w{10,}\b', content))
        word_count = len(content.split())
        
        if word_count > 0:
            technical_ratio = technical_terms / word_count
            return technical_ratio > 0.02  # More than 2% technical terms
        
        return False

    # Summary analysis methods
    def _analyze_content_types(self, processed_captures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze distribution of content types"""
        content_types = {}
        for capture in processed_captures:
            content_type = capture['metadata']['content_category']
            content_types[content_type] = content_types.get(content_type, 0) + 1
        return content_types

    def _extract_domains(self, processed_captures: List[Dict[str, Any]]) -> List[str]:
        """Extract unique domains from processed captures"""
        domains = set()
        for capture in processed_captures:
            domain = capture['metadata']['domain']
            if domain != 'unknown':
                domains.add(domain)
        return list(domains)

    def _analyze_user_intents(self, processed_captures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze distribution of user intents"""
        intents = {}
        for capture in processed_captures:
            intent = capture['intent']
            intents[intent] = intents.get(intent, 0) + 1
        return intents

    def _calculate_average_content_length(self, processed_captures: List[Dict[str, Any]]) -> float:
        """Calculate average content length"""
        if not processed_captures:
            return 0.0
        
        total_words = sum(capture['metadata']['word_count'] for capture in processed_captures)
        return total_words / len(processed_captures)

        

        
