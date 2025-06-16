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


    def _process_single_capture(self, raw_capture: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
       Helper method: Process a single capture through all transformation steps.
        
        Args:
            raw_capture: Raw capture data from browser extension
            index: Index of capture in batch
            
        Returns:
            Processed capture with normalized structure
        """
        timestamp = self._parse_timestamp(raw_capture.get('timestamp'))
        capture_id = f"capture_{int(timestamp.timestamp() * 1000)}_{hash(raw_capture['url']) % 1000000:06d}"

        url_info = self._parse_url(raw_capture['url'])

        cleaned_content = self._clean_html_content(raw_capture['content'])
        content_metadata = self._extract_content_metadata(raw_capture, cleaned_content)
        behavior_metadata = self._analyze_user_behavior(raw_capture)

    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Helper method: Parse timestamp string into datetime object."""
        try:
            if isinstance(timestamp_str, (int, float)):
                return datetime.fromtimestamp(timestamp_str / 1000, tz=timezone.utc)
            return date_parser.parse(timestamp_str)
        except Exception:
            return datetime.now(timezone.utc)


    def _parse_url(self, url: str) -> Dict[str, str]:
        """Helper method: Extract domain and URL components."""
        try:
            parsed = urlparse(url)
            return {
                'domain': parsed.netloc.lower(),
                'scheme': parsed.scheme,
                'path': parsed.path,
                'query': parsed.query,
                'fragment': parsed.fragment
            }
        except Exception:
            return {'domain': 'unknown', 'scheme': '', 'path': '', 'query': '', 'fragment': ''}

    
    def _clean_html_content(self, html_content: str) -> str:
        """Helper method: Clean HTML and convert to readable text."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            text_content = self.html_converter.handle(str(soup))
            
            text_content = re.sub(r'\n\s*\n\s*\n', '\n\n', text_content)
            text_content = re.sub(r'[ \t]+', ' ', text_content)
            
            return text_content.strip()
            
        except Exception as e:
            self.logger.warning(f"Error cleaning HTML content: {str(e)}")
            return html_content
    

    def _extract_content_metadata(self, raw_capture: Dict[str, Any], cleaned_content: str) -> Dict[str, Any]:
        """Helper method: Extract metadata from page content."""
        try:
            soup = BeautifulSoup(raw_capture['content'], 'html.parser')
            
            title_tag = soup.find('title')
            page_title = title_tag.get_text().strip() if title_tag else 'Untitled'
            
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            heading_hierarchy = []
            for heading in headings:
                heading_hierarchy.append({
                    'level': int(heading.name[1]),
                    'text': heading.get_text().strip()[:100],
                    'id': heading.get('id', '')
                })
            
            links = soup.find_all('a', href=True)
            external_links = sum(1 for link in links if self._is_external_link(link['href'], raw_capture['url']))
            internal_links = len(links) - external_links
            
            has_code = bool(soup.find(['code', 'pre']) or re.search(r'```|`[^`]+`', cleaned_content))
            has_math = bool(re.search(r'\$[^$]+\$|\\\([^)]+\\\)|\\\[[^]]+\\\]', cleaned_content))
            has_data_tables = len(soup.find_all('table')) > 0
            
            citations = len(re.findall(r'\[[0-9]+\]|\([A-Za-z]+\s+et\s+al\.?,?\s+[0-9]{4}\)', cleaned_content))
            
            return {
                'page_title': page_title,
                'content_type': raw_capture.get('content_type', 'text/html'),
                'word_count': len(cleaned_content.split()),
                'heading_hierarchy': heading_hierarchy,
                'link_count': len(links),
                'list_items_count': len(soup.find_all(['li'])),
                'table_count': len(soup.find_all('table')),
                'image_count': len(soup.find_all('img')),
                'video_count': len(soup.find_all(['video', 'iframe'])),
                'has_code': has_code,
                'has_math': has_math,
                'has_data_tables': has_data_tables,
                'external_links': external_links,
                'internal_links': internal_links,
                'citations': citations
            }
            
        except Exception as e:
            self.logger.warning(f"Error extracting content metadata: {str(e)}")
            return {
                'page_title': 'Unknown',
                'content_type': 'text/html',
                'word_count': len(cleaned_content.split()),
                'heading_hierarchy': [],
                'link_count': 0,
                'list_items_count': 0,
                'table_count': 0,
                'image_count': 0,
                'video_count': 0,
                'has_code': False,
                'has_math': False,
                'has_data_tables': False,
                'external_links': 0,
                'internal_links': 0,
                'citations': 0
            }

    def _analyze_user_behavior(self, raw_capture: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method: Analyze user behavior patterns from capture data."""
        return {
            'time_on_page': raw_capture.get('dwell_time', raw_capture.get('time_on_page', 0)),
            'scroll_depth': raw_capture.get('scroll_depth_at_selection', raw_capture.get('scroll_depth', 0)),
            'viewport_size': raw_capture.get('viewport_size', 'unknown')
        }



        

        

        
