"""
NotionDatabaseManager - Manage database schemas and creation
"""

import logging
import os
import time
from typing import Dict, Any
from .client import NotionClient

class NotionDatabaseManager:
    """Manage Notion database schemas and creation"""
    
    def __init__(self, notion_client: NotionClient):
        """Initialize with Notion client and database schemas"""
        self.logger = logging.getLogger(__name__)
        self.notion_client = notion_client
        self.database_schemas = self._init_enhanced_database_schemas()
    
    def _init_enhanced_database_schemas(self) -> Dict[str, Any]:
        """Initialize enhanced database schemas for topic-based organization"""
        return {
            'learning_sessions': {
                'title': '🧠 Smart Notes - Learning Sessions',
                'properties': {
                    'Session Title': {'title': {}},
                    'Date': {'date': {}},
                    'Topics Covered': {'multi_select': {'options': []}},
                    'Primary Theme': {'select': {'options': []}},
                    'Knowledge Level': {
                        'select': {
                            'options': [
                                {'name': 'Beginner', 'color': 'green'},
                                {'name': 'Intermediate', 'color': 'yellow'},
                                {'name': 'Advanced', 'color': 'red'},
                                {'name': 'Expert', 'color': 'purple'}
                            ]
                        }
                    },
                    'Topics Count': {'number': {}},
                    'Concepts Count': {'number': {}},
                    'Cross-References': {'number': {}},
                    'Completion Status': {
                        'select': {
                            'options': [
                                {'name': 'In Progress', 'color': 'yellow'},
                                {'name': 'Completed', 'color': 'green'},
                                {'name': 'Needs Review', 'color': 'orange'},
                                {'name': 'Archived', 'color': 'gray'}
                            ]
                        }
                    }
                }
            },
            'research_topics': {
                'title': '📚 Smart Notes - Research Topics',
                'properties': {
                    'Topic Name': {'title': {}},
                    'Domain': {'select': {'options': []}},
                    'Complexity Level': {
                        'select': {
                            'options': [
                                {'name': 'Foundational', 'color': 'green'},
                                {'name': 'Intermediate', 'color': 'yellow'},
                                {'name': 'Advanced', 'color': 'red'},
                                {'name': 'Cutting Edge', 'color': 'purple'}
                            ]
                        }
                    },
                    'Learning Status': {
                        'select': {
                            'options': [
                                {'name': 'New', 'color': 'gray'},
                                {'name': 'Learning', 'color': 'yellow'},
                                {'name': 'Understood', 'color': 'green'},
                                {'name': 'Mastered', 'color': 'blue'},
                                {'name': 'Teaching', 'color': 'purple'}
                            ]
                        }
                    },
                    'First Encountered': {'date': {}},
                    'Last Reviewed': {'date': {}},
                    'Session Count': {'number': {}},
                    'Concepts Count': {'number': {}},
                    'Practical Applications': {'number': {}},
                    'Knowledge Gaps': {'number': {}},
                    'Next Steps': {'rich_text': {}},
                    'Tags': {'multi_select': {'options': []}}
                }
            },
            'concept_library': {
                'title': '💡 Smart Notes - Concept Library',
                'properties': {
                    'Concept Name': {'title': {}},
                    'Topic': {'select': {'options': []}},
                    'Definition Quality': {
                        'select': {
                            'options': [
                                {'name': 'Clear', 'color': 'green'},
                                {'name': 'Partial', 'color': 'yellow'},
                                {'name': 'Unclear', 'color': 'red'},
                                {'name': 'Missing', 'color': 'gray'}
                            ]
                        }
                    },
                    'Understanding Level': {
                        'select': {
                            'options': [
                                {'name': 'Surface', 'color': 'red'},
                                {'name': 'Functional', 'color': 'yellow'},
                                {'name': 'Deep', 'color': 'green'},
                                {'name': 'Expert', 'color': 'blue'}
                            ]
                        }
                    },
                    'Confidence Score': {'number': {}},
                    'First Learned': {'date': {}},
                    'Times Encountered': {'number': {}},
                    'Prerequisites': {'multi_select': {'options': []}},
                    'Applications': {'multi_select': {'options': []}}
                }
            },
            'captured_content': {
                'title': '📄 Smart Notes - Captured Content',
                'properties': {
                    'Content Title': {'title': {}},
                    'Source URL': {'url': {}},
                    'Capture Date': {'date': {}},
                    'Content Type': {
                        'select': {
                            'options': [
                                {'name': 'Article', 'color': 'blue'},
                                {'name': 'Tutorial', 'color': 'green'},
                                {'name': 'Documentation', 'color': 'yellow'},
                                {'name': 'Blog Post', 'color': 'purple'},
                                {'name': 'Research Paper', 'color': 'red'},
                                {'name': 'General', 'color': 'gray'}
                            ]
                        }
                    },
                    'Word Count': {'number': {}},
                    'Related Topics': {'multi_select': {'options': []}},
                    'Content Preview': {'rich_text': {}},
                    'Processing Status': {
                        'select': {
                            'options': [
                                {'name': 'Captured', 'color': 'yellow'},
                                {'name': 'Processed', 'color': 'green'},
                                {'name': 'Archived', 'color': 'gray'}
                            ]
                        }
                    }
                }
            }
        }
    
    def ensure_enhanced_databases_exist(self) -> Dict[str, str]:
        """Ensure all enhanced databases exist and return their IDs"""
        databases = {}
        
        for db_type in ['learning_sessions', 'research_topics', 'concept_library']:
            if db_type in self.database_schemas:
                db_id = self._get_or_create_database(db_type)
                databases[db_type] = db_id
                self.logger.info(f"Enhanced database '{db_type}' ready: {db_id}")
                time.sleep(1)  # Rate limiting
        
        # Set up database relationships
        self._setup_enhanced_database_relationships(databases)
        return databases
    
    def _create_database(self, db_type: str) -> str:
        """Create new Notion database for given type"""
        schema = self.database_schemas[db_type]
        
        # Get parent page ID
        parent_page_id = os.getenv('NOTION_PARENT_PAGE_ID')
        if not parent_page_id:
            parent = {"type": "workspace"}
        else:
            parent = {"type": "page_id", "page_id": parent_page_id}
        
        database_data = {
            "parent": parent,
            "title": [{"type": "text", "text": {"content": schema['title']}}],
            "properties": schema['properties']
        }

        return self.notion_client.create_database(database_data)
    
    def _setup_enhanced_database_relationships(self, databases: Dict[str, str]):
        """Set up relationships between enhanced databases"""
        try:
            # Add relations to concept library
            if 'concept_library' in databases:
                properties = {
                    "Related Concepts": {
                        "relation": {
                            "database_id": databases['concept_library'],
                            "single_property": {}
                        }
                    },
                    "From Topics": {
                        "relation": {
                            "database_id": databases['research_topics'],
                            "single_property": {}
                        }
                    }
                }
                
                # Use the client to update database properties
                import requests
                response = requests.patch(
                    f"{self.notion_client.notion_api_url}/databases/{databases['concept_library']}",
                    headers=self.notion_client.headers,
                    json={"properties": properties}
                )
                
                if response.status_code != 200:
                    self.logger.warning(f"Failed to set up database relationships: {response.text}")
            
            self.logger.info("Enhanced database relationships configured")
            
        except Exception as e:
            self.logger.warning(f"Failed to set up database relationships: {str(e)}")
    
    def _get_or_create_database(self, db_type: str) -> str:
        """Get existing database or create new one"""
        # Search for existing database
        existing_db = self.notion_client.search_database_by_title(self.database_schemas[db_type]['title'])
        if existing_db:
            return existing_db
        
        # Create new database
        return self._create_database(db_type)