"""
NotionClient - Handle all Notion API interactions
"""

import json
import logging
import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

class NotionClient:
    """Handle all Notion API interactions"""
    
    def __init__(self):
        """Initialize Notion API client with headers and connection"""
        self.logger = logging.getLogger(__name__)
        
        self.notion_token = os.getenv('NOTION_TOKEN')
        if not self.notion_token:
            self.logger.error("NOTION_TOKEN environment variable not set")
            raise ValueError("Notion API token required")
        
        self.notion_api_url = "https://api.notion.com/v1"
        self.notion_version = "2022-06-28"
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": self.notion_version
        }
    
    def test_connection(self) -> bool:
        """Test Notion API connection"""
        try:
            response = requests.get(
                f"{self.notion_api_url}/users/me",
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            self.logger.error(f"Notion connection test failed: {str(e)}")
            return False
    
    def create_page(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Notion page"""
        try:
            # Use explicit JSON encoding
            json_data = json.dumps(page_data, ensure_ascii=False, default=str)
            
            response = requests.post(
                f"{self.notion_api_url}/pages",
                headers=self.headers,
                data=json_data.encode('utf-8'),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to create page: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error creating page: {str(e)}")
            return {}
    
    def create_database(self, database_data: Dict[str, Any]) -> str:
        """Create a new Notion database and return ID"""
        try:
            response = requests.post(
                f"{self.notion_api_url}/databases", 
                headers=self.headers, 
                json=database_data
            )
            response.raise_for_status()
            database_id = response.json()['id']
            self.logger.info(f"Created database: {database_id}")
            return database_id
        except Exception as e:
            self.logger.error(f"Database creation failed: {e}")
            if 'response' in locals():
                self.logger.error(f"Response: {response.text}")
            raise
    
    def search_database_by_title(self, title: str) -> Optional[str]:
        """Search for existing database by title"""
        try:
            response = requests.post(
                f"{self.notion_api_url}/search",
                headers=self.headers,
                json={
                    "query": title,
                    "filter": {"property": "object", "value": "database"}
                }
            )
            response.raise_for_status()
            
            results = response.json().get('results', [])
            for result in results:
                if result.get('title', [{}])[0].get('plain_text') == title:
                    return result['id']
            
        except Exception as e:
            self.logger.warning(f"Database search failed: {str(e)}")
        
        return None
    
    def add_blocks_to_page(self, page_id: str, blocks: List[Dict[str, Any]]) -> bool:
        """Add content blocks to a Notion page"""
        try:
            # Add content in batches
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch_blocks = blocks[i:i + batch_size]
                response = requests.patch(
                    f"{self.notion_api_url}/blocks/{page_id}/children",
                    headers=self.headers,
                    json={"children": batch_blocks}
                )
                if response.status_code != 200:
                    self.logger.error(f"Failed to add blocks: {response.status_code} - {response.text}")
                    return False
            
            return True
        except Exception as e:
            self.logger.warning(f"Failed to add blocks to page: {str(e)}")
            return False
    
    def update_page_properties(self, page_id: str, properties: Dict[str, Any]) -> bool:
        """Update page properties"""
        try:
            response = requests.patch(
                f"{self.notion_api_url}/pages/{page_id}",
                headers=self.headers,
                json={"properties": properties}
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Failed to update page properties: {str(e)}")
            return False
    
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> requests.Response:
        """Make HTTP request to Notion API with proper encoding"""
        url = f"{self.notion_api_url}/{endpoint.lstrip('/')}"
        
        if data:
            json_data = json.dumps(data, ensure_ascii=False, default=str)
            response = requests.request(
                method,
                url,
                headers=self.headers,
                data=json_data.encode('utf-8'),
                timeout=30
            )
        else:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=30
            )
        
        return response
    
    def _serialize_for_notion(self, obj: Any) -> Any:
        """Serialize object for Notion API with proper Unicode handling"""
        if isinstance(obj, dict):
            return {k: self._serialize_for_notion(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_notion(item) for item in obj]
        elif isinstance(obj, str):
            # Ensure proper UTF-8 encoding for strings
            return obj.encode('utf-8').decode('utf-8')
        elif obj is None:
            return None
        else:
            return str(obj)[:2000] 