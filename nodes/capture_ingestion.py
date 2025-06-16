#!/usr/bin/env python3
"""
Capture Ingestion Node: This node handles the initial processing and validation of raw browsing data
from Chrome extension captures, preparing them for downstream analysis.
"""

class CaptureIngestionNode(BaseNode):
    """
    Node 1: Capture Ingestion
    
    Purpose: Collect and validate raw browsing data from Chrome extension
    
    Input: Raw capture data from browser extension via shared_state
    Process: Parse, validate, normalize, and clean capture data
    Output: Structured raw_captures to shared_state
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0

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
            'blog_post': [
                r'posted\s+on',
                r'by\s+.+\s+on',
                r'comments?\s*\(',
                r'share\s+this',
                r'medium\.com',
                r'dev\.to'
            ],
            'news_article': [
                r'published\s+\d+\s+hours?\s+ago'
            ]
        }

    async def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare for capture ingestion by validating input data structure. Namely, if url, content and timestamp is present for each captured note. 
        
        Args:
            shared_state: The shared state dictionary containing raw capture data
            
        Returns:
            Updated shared state with validation results
        """
        self.logger.info("Starting Capture Ingestion prep phase")
        
        shared_state.setdefault('pipeline_metadata', {})
        shared_state['pipeline_metadata']['capture_ingestion_start'] = datetime.now(timezone.utc).isoformat()
        
        raw_input = shared_state.get('raw_input', {})
        
        if not raw_input:
            self.logger.error("No raw input data found in shared state")
            shared_state['pipeline_metadata']['capture_ingestion_error'] = "No raw input data"
            return shared_state
        
        required_fields = ['url', 'content', 'timestamp']
        captures = raw_input if isinstance(raw_input, list) else [raw_input]
        
        valid_captures = []
        invalid_captures = []
        
        for i, capture in enumerate(captures):
            missing_fields = [field for field in required_fields if field not in capture]
            if missing_fields:
                self.logger.warning(f"Capture {i} missing required fields: {missing_fields}")
                invalid_captures.append({'index': i, 'missing_fields': missing_fields})
            else:
                valid_captures.append(capture)
        
        shared_state['validation_results'] = {
            'total_captures': len(captures),
            'valid_captures': len(valid_captures),
            'invalid_captures': len(invalid_captures),
            'invalid_details': invalid_captures
        }
        
        shared_state['captures_to_process'] = valid_captures
        
        self.logger.info(f"Prep complete: {len(valid_captures)} valid captures out of {len(captures)}")
        return shared_state
    

    async def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution: Process each capture through cleaning, normalization, and metadata extraction.
        
        Args:
            shared_state: The shared state dictionary
            
        Returns:
            Updated shared state with processed captures
        """
        self.logger.info("Starting Capture Ingestion core execution")
        
        captures_to_process = shared_state.get('captures_to_process', [])
        processed_captures = []
        
        for i, raw_capture in enumerate(captures_to_process):
            try:
                self.logger.debug(f"Processing capture {i+1}/{len(captures_to_process)}")
                processed_capture = self._process_single_capture(raw_capture, i)
                processed_captures.append(processed_capture)
                
            except Exception as e:
                self.logger.error(f"Error processing capture {i}: {str(e)}")
                continue
        
        shared_state['raw_captures'] = processed_captures
        shared_state['pipeline_metadata']['captures_processed'] = len(processed_captures)
        
        self.logger.info(f"Core execution complete: {len(processed_captures)} captures processed")
        return shared_state
