"""
Notion Note Generation Node: Creates rich, structured notes in Notion from pipeline analysis
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import requests
from urllib.parse import quote

from dotenv import load_dotenv
load_dotenv()

from pocketflow import Node as BaseNode


class NotionNoteGenerationNode(BaseNode):
    """
    Node 5: Notion Note Generation
    
    Purpose: Transform pipeline analysis into rich, structured Notion pages
    
    Input: All previous node outputs (captures, concepts, knowledge graph, historical analysis)
    Process: Create Notion databases and pages with rich formatting and connections
    Output: Notion page URLs and creation metadata
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Notion API configuration
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.notion_database_id = os.getenv('NOTION_DATABASE_ID')  # Optional: use existing database
        
        self.notion_api_url = "https://api.notion.com/v1"
        self.notion_version = "2022-06-28"
        
        if not self.notion_token:
            self.logger.error("NOTION_TOKEN environment variable not set")
            raise ValueError("Notion API token required")
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": self.notion_version
        }
        
        # Database structures for different content types
        self.database_schemas = self._init_database_schemas()
        
        self.emojis = {
            'session': '🧠',
            'concept': '💡',
            'source': '📚',
            'connection': '🔗',
            'gap': '⚠️',
            'recommendation': '✅',
            'high_priority': '🔥',
            'medium_priority': '⚡',
            'low_priority': '📝',
            'review': '🔄',
            'mastered': '⭐',
            'learning': '📈',
            'new': '🆕'
        }

    def _init_database_schemas(self) -> Dict[str, Any]:
        """Initialize database schema templates for different content types"""
        return {
            'learning_sessions': {
                'title': 'Smart Notes - Learning Sessions',
                'properties': {
                    'Session Title': {'title': {}},
                    'Date': {'date': {}},
                    'Theme': {'select': {'options': []}},
                    'Concepts Count': {'number': {}},
                    'Sources Count': {'number': {}},
                    'Connections Found': {'number': {}},
                    'Knowledge Gaps': {'number': {}},
                    'Status': {
                        'select': {
                            'options': [
                                {'name': 'Processing', 'color': 'yellow'},
                                {'name': 'Complete', 'color': 'green'},
                                {'name': 'Needs Review', 'color': 'orange'}
                            ]
                        }
                    },
                    'Priority': {
                        'select': {
                            'options': [
                                {'name': 'High', 'color': 'red'},
                                {'name': 'Medium', 'color': 'yellow'},
                                {'name': 'Low', 'color': 'gray'}
                            ]
                        }
                    }
                }
            },
            'concepts': {
                'title': 'Smart Notes - Concepts',
                'properties': {
                    'Concept': {'title': {}},
                    'Confidence Level': {
                        'select': {
                            'options': [
                                {'name': 'High', 'color': 'green'},
                                {'name': 'Medium', 'color': 'yellow'},
                                {'name': 'Low', 'color': 'red'},
                                {'name': 'New', 'color': 'gray'}
                            ]
                        }
                    },
                    'Learning Sessions': {'relation': {'database_id': ''}},
                    'Connected Concepts': {'relation': {'database_id': ''}},
                    'First Learned': {'date': {}},
                    'Last Reviewed': {'date': {}},
                    'Mastery Level': {'number': {}},
                    'Tags': {'multi_select': {'options': []}},
                    'Domain': {'select': {'options': []}}
                }
            },
            'sources': {
                'title': 'Smart Notes - Sources',
                'properties': {
                    'Title': {'title': {}},
                    'URL': {'url': {}},
                    'Domain': {'select': {'options': []}},
                    'Content Type': {
                        'select': {
                            'options': [
                                {'name': 'Research Paper', 'color': 'blue'},
                                {'name': 'Documentation', 'color': 'green'},
                                {'name': 'Blog Post', 'color': 'yellow'},
                                {'name': 'Tutorial', 'color': 'orange'},
                                {'name': 'General', 'color': 'gray'}
                            ]
                        }
                    },
                    'Knowledge Level': {
                        'select': {
                            'options': [
                                {'name': 'Advanced', 'color': 'red'},
                                {'name': 'Intermediate', 'color': 'yellow'},
                                {'name': 'Basic', 'color': 'green'}
                            ]
                        }
                    },
                    'Captured Date': {'date': {}},
                    'Word Count': {'number': {}},
                    'Has Code': {'checkbox': {}},
                    'Has Math': {'checkbox': {}},
                    'Learning Sessions': {'relation': {'database_id': ''}}
                }
            }
        }

    def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare for Notion note generation
        """
        self.logger.info("Starting Notion Note Generation prep phase")
        
        # Validate inputs from previous nodes
        required_data = {
            'session_id': shared_state.get('session_id'),
            'raw_captures': shared_state.get('raw_captures', []),
            'extracted_concepts': shared_state.get('extracted_concepts', {}),
            'knowledge_graph': shared_state.get('knowledge_graph', {}),
            'historical_connections': shared_state.get('historical_connections', {}),
            'knowledge_gaps': shared_state.get('knowledge_gaps', []),
            'learning_recommendations': shared_state.get('learning_recommendations', [])
        }
        
        missing_data = [key for key, value in required_data.items() if not value]
        if missing_data:
            self.logger.warning(f"Missing data for Notion generation: {missing_data}")
        
        # Test Notion API connection
        try:
            self._test_notion_connection()
            self.logger.info("Notion API connection successful")
        except Exception as e:
            self.logger.error(f"Notion API connection failed: {str(e)}")
            return {'error': f'Notion API connection failed: {str(e)}'}
        
        prep_data = {
            'session_data': {
                'session_id': required_data['session_id'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'theme': required_data['extracted_concepts'].get('session_theme', 'general'),
                'concepts_count': len(required_data['extracted_concepts'].get('learning_concepts', [])),
                'sources_count': len(required_data['raw_captures']),
                'connections_found': required_data['historical_connections'].get('total_connections_found', 0),
                'knowledge_gaps_count': len(required_data['knowledge_gaps'])
            },
            'content_data': required_data,
            'databases_needed': ['learning_sessions', 'concepts', 'sources']
        }
        
        self.logger.info(f"Prepared Notion generation for session: {prep_data['session_data']['session_id']}")
        return prep_data

    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution: Create Notion databases and pages
        """
        if 'error' in prep_result:
            return prep_result
            
        self.logger.info("Starting Notion Note Generation core execution")
        
        try:
            # Step 1: Ensure databases exist
            databases = self._ensure_databases_exist(prep_result['databases_needed'])
            
            # Step 2: Create/update concept entries
            concept_pages = self._create_concept_pages(
                prep_result['content_data']['extracted_concepts'],
                databases['concepts']
            )
            
            # Step 3: Create/update source entries  
            source_pages = self._create_source_pages(
                prep_result['content_data']['raw_captures'],
                databases['sources']
            )
            
            # Step 4: Create main session page
            session_page = self._create_session_page(
                prep_result['session_data'],
                prep_result['content_data'],
                databases['learning_sessions'],
                concept_pages,
                source_pages
            )
            
            # Step 5: Update concept relationships
            self._update_concept_relationships(
                concept_pages,
                prep_result['content_data']['historical_connections'],
                databases['concepts']
            )
            
            return {
                'session_page': session_page,
                'concept_pages': concept_pages,
                'source_pages': source_pages,
                'databases': databases,
                'notion_urls': {
                    'session': session_page.get('url'),
                    'concepts_db': f"{self.notion_api_url.replace('/v1', '')}/{databases['concepts']}",
                    'sources_db': f"{self.notion_api_url.replace('/v1', '')}/{databases['sources']}"
                },
                'creation_summary': {
                    'session_created': bool(session_page),
                    'concepts_created': len(concept_pages),
                    'sources_created': len(source_pages),
                    'total_pages': 1 + len(concept_pages) + len(source_pages)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Notion generation failed: {str(e)}")
            return {'error': f"Notion generation failed: {str(e)}"}

    def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """
        Post-processing: Store Notion results and URLs
        """
        self.logger.info("Notion Note Generation post-execution phase")
        
        if 'error' in exec_result:
            shared_state['notion_generation_error'] = exec_result['error']
            return "error"
        
        # Store Notion results in shared_state
        shared_state['notion_generation'] = {
            'session_page_url': exec_result['notion_urls']['session'],
            'databases': exec_result['databases'],
            'creation_summary': exec_result['creation_summary'],
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Update pipeline metadata
        shared_state['pipeline_metadata']['notion_generation_complete'] = True
        shared_state['pipeline_metadata']['notion_generation_summary'] = {
            'total_pages_created': exec_result['creation_summary']['total_pages'],
            'session_url': exec_result['notion_urls']['session'],
            'concepts_created': exec_result['creation_summary']['concepts_created'],
            'sources_created': exec_result['creation_summary']['sources_created']
        }
        
        self.logger.info(f"Notion generation complete - Session page: {exec_result['notion_urls']['session']}")
        return "default"

    def _test_notion_connection(self):
        """Test Notion API connection"""
        response = requests.get(
            f"{self.notion_api_url}/users/me",
            headers=self.headers
        )
        response.raise_for_status()

    def _ensure_databases_exist(self, needed_databases: List[str]) -> Dict[str, str]:
        """Ensure required Notion databases exist, create if needed"""
        databases = {}
        
        for db_type in needed_databases:
            if db_type in self.database_schemas:
                db_id = self._get_or_create_database(db_type)
                databases[db_type] = db_id
                self.logger.info(f"Database '{db_type}' ready: {db_id}")
        
        # Update relation database IDs in schemas
        self._update_relation_ids(databases)
        
        return databases

    def _get_or_create_database(self, db_type: str) -> str:
        """Get existing database or create new one"""
        # If user provided a specific database ID, use it
        if self.notion_database_id and db_type == 'learning_sessions':
            return self.notion_database_id
        
        # Search for existing database by title
        existing_db = self._search_database_by_title(self.database_schemas[db_type]['title'])
        if existing_db:
            return existing_db
        
        # Create new database
        return self._create_database(db_type)

    def _search_database_by_title(self, title: str) -> Optional[str]:
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

    def _create_database(self, db_type: str) -> str:
        """Create new Notion database"""
        schema = self.database_schemas[db_type]
        
        # Get parent page (use root if not specified)
        parent_page_id = os.getenv('NOTION_PARENT_PAGE_ID')
        if not parent_page_id:
            # Create in the workspace root
            parent = {"type": "page_id", "page_id": self._get_root_page_id()}
        else:
            parent = {"type": "page_id", "page_id": parent_page_id}
        
        database_data = {
            "parent": parent,
            "title": [{"type": "text", "text": {"content": schema['title']}}],
            "properties": schema['properties']
        }
        
        response = requests.post(
            f"{self.notion_api_url}/databases",
            headers=self.headers,
            json=database_data
        )
        response.raise_for_status()
        
        database_id = response.json()['id']
        self.logger.info(f"Created database '{db_type}': {database_id}")
        return database_id

    def _get_root_page_id(self) -> str:
        """Get a suitable root page ID for database creation"""
        # This is a simplified approach - in production, you'd want better parent page management
        try:
            response = requests.post(
                f"{self.notion_api_url}/search",
                headers=self.headers,
                json={"filter": {"property": "object", "value": "page"}}
            )
            response.raise_for_status()
            
            results = response.json().get('results', [])
            if results:
                return results[0]['id']
                
        except Exception:
            pass
        
        # Fallback: create a dedicated parent page
        return self._create_parent_page()

    def _create_parent_page(self) -> str:
        """Create a dedicated parent page for Smart Notes"""
        page_data = {
            "parent": {"type": "workspace"},
            "properties": {
                "title": [{"type": "text", "text": {"content": "🧠 Smart Notes System"}}]
            },
            "children": [
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": "🧠 Smart Notes System"}}]
                    }
                },
                {
                    "object": "block", 
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": "AI-powered learning notes and knowledge management system."}}]
                    }
                }
            ]
        }
        
        response = requests.post(
            f"{self.notion_api_url}/pages",
            headers=self.headers,
            json=page_data
        )
        response.raise_for_status()
        return response.json()['id']

    def _update_relation_ids(self, databases: Dict[str, str]):
        """Update relation database IDs in schemas"""
        if 'learning_sessions' in databases and 'concepts' in databases:
            self.database_schemas['concepts']['properties']['Learning Sessions']['relation']['database_id'] = databases['learning_sessions']
            self.database_schemas['sources']['properties']['Learning Sessions']['relation']['database_id'] = databases['learning_sessions']
            self.database_schemas['concepts']['properties']['Connected Concepts']['relation']['database_id'] = databases['concepts']

    def _create_concept_pages(self, extracted_concepts: Dict[str, Any], concepts_db_id: str) -> Dict[str, Any]:
        """Create or update concept pages in Notion"""
        concept_pages = {}
        learning_concepts = extracted_concepts.get('learning_concepts', [])
        confidence_scores = extracted_concepts.get('confidence_scores', {})
        
        for concept in learning_concepts:
            confidence = confidence_scores.get(concept, {})
            confidence_level = confidence.get('confidence_level', 'new')
            
            page_data = {
                "parent": {"database_id": concepts_db_id},
                "properties": {
                    "Concept": {"title": [{"text": {"content": concept}}]},
                    "Confidence Level": {"select": {"name": confidence_level.title()}},
                    "First Learned": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
                    "Last Reviewed": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
                    "Mastery Level": {"number": confidence.get('overall_confidence', 0.1) * 100}
                }
            }
            
            # Check if concept page already exists
            existing_page = self._find_existing_concept_page(concept, concepts_db_id)
            
            if existing_page:
                # Update existing page
                response = requests.patch(
                    f"{self.notion_api_url}/pages/{existing_page}",
                    headers=self.headers,
                    json={"properties": page_data["properties"]}
                )
            else:
                # Create new page
                response = requests.post(
                    f"{self.notion_api_url}/pages",
                    headers=self.headers,
                    json=page_data
                )
            
            if response.status_code in [200, 201]:
                concept_pages[concept] = response.json()
                self.logger.debug(f"Created/updated concept page: {concept}")
            else:
                self.logger.warning(f"Failed to create concept page for '{concept}': {response.text}")
        
        return concept_pages

    def _find_existing_concept_page(self, concept: str, database_id: str) -> Optional[str]:
        """Find existing concept page in database"""
        try:
            response = requests.post(
                f"{self.notion_api_url}/databases/{database_id}/query",
                headers=self.headers,
                json={
                    "filter": {
                        "property": "Concept",
                        "title": {"equals": concept}
                    }
                }
            )
            response.raise_for_status()
            
            results = response.json().get('results', [])
            if results:
                return results[0]['id']
                
        except Exception as e:
            self.logger.warning(f"Error searching for concept '{concept}': {str(e)}")
        
        return None

    def _create_source_pages(self, raw_captures: List[Dict[str, Any]], sources_db_id: str) -> Dict[str, Any]:
        """Create source pages in Notion"""
        source_pages = {}
        
        for capture in raw_captures:
            metadata = capture.get('metadata', {})
            
            page_data = {
                "parent": {"database_id": sources_db_id},
                "properties": {
                    "Title": {"title": [{"text": {"content": metadata.get('page_title', 'Untitled')}}]},
                    "URL": {"url": capture.get('url', '')},
                    "Domain": {"select": {"name": metadata.get('domain', 'unknown')}},
                    "Content Type": {"select": {"name": metadata.get('content_category', 'general').replace('_', ' ').title()}},
                    "Knowledge Level": {"select": {"name": metadata.get('knowledge_level', 'basic').title()}},
                    "Captured Date": {"date": {"start": metadata.get('timestamp', datetime.now(timezone.utc).isoformat())}},
                    "Word Count": {"number": metadata.get('word_count', 0)},
                    "Has Code": {"checkbox": metadata.get('has_code', False)},
                    "Has Math": {"checkbox": metadata.get('has_math', False)}
                }
            }
            
            try:
                response = requests.post(
                    f"{self.notion_api_url}/pages",
                    headers=self.headers,
                    json=page_data
                )
                
                if response.status_code == 201:
                    source_pages[capture.get('id', capture['url'])] = response.json()
                    self.logger.debug(f"Created source page: {metadata.get('page_title', 'Untitled')}")
                
            except Exception as e:
                self.logger.warning(f"Failed to create source page: {str(e)}")
        
        return source_pages

    def _create_session_page(self, session_data: Dict[str, Any], content_data: Dict[str, Any], 
                           sessions_db_id: str, concept_pages: Dict, source_pages: Dict) -> Dict[str, Any]:
        """Create the main learning session page"""
        
        # Determine session priority based on knowledge gaps and recommendations
        knowledge_gaps = content_data.get('knowledge_gaps', [])
        high_priority_gaps = [gap for gap in knowledge_gaps if gap.get('priority') == 'high']
        
        if high_priority_gaps:
            priority = 'High'
        elif len(knowledge_gaps) > 0:
            priority = 'Medium'
        else:
            priority = 'Low'
        
        # Create session page properties
        page_data = {
            "parent": {"database_id": sessions_db_id},
            "properties": {
                "Session Title": {"title": [{"text": {"content": f"Learning Session - {session_data['theme'].replace('_', ' ').title()}"}}]},
                "Date": {"date": {"start": session_data['timestamp']}},
                "Theme": {"select": {"name": session_data['theme'].replace('_', ' ').title()}},
                "Concepts Count": {"number": session_data['concepts_count']},
                "Sources Count": {"number": session_data['sources_count']},
                "Connections Found": {"number": session_data['connections_found']},
                "Knowledge Gaps": {"number": session_data['knowledge_gaps_count']},
                "Status": {"select": {"name": "Complete"}},
                "Priority": {"select": {"name": priority}}
            }
        }
        
        try:
            response = requests.post(
                f"{self.notion_api_url}/pages",
                headers=self.headers,
                json=page_data
            )
            response.raise_for_status()
            
            session_page = response.json()
            
            # Add rich content to the session page
            self._add_session_content(session_page['id'], content_data, concept_pages, source_pages)
            
            return session_page
            
        except Exception as e:
            self.logger.error(f"Failed to create session page: {str(e)}")
            return {}

    def _add_session_content(self, page_id: str, content_data: Dict[str, Any], 
                           concept_pages: Dict, source_pages: Dict):
        """Add rich content blocks to the session page"""
        
        blocks = []
        
        # Session Overview
        blocks.extend([
            {
                "object": "block",
                "type": "heading_1", 
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": f"{self.emojis['session']} Learning Session Overview"}}]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": f"Session completed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}. "}}
                    ]
                }
            }
        ])
        
        # Key Concepts Learned
        learning_concepts = content_data.get('extracted_concepts', {}).get('learning_concepts', [])
        if learning_concepts:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"{self.emojis['concept']} Key Concepts Learned"}}]
                }
            })
            
            for concept in learning_concepts[:5]:  # Limit to top 5
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": concept}}]
                    }
                })
        
        # Historical Connections
        historical_connections = content_data.get('historical_connections', {})
        if historical_connections.get('total_connections_found', 0) > 0:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"{self.emojis['connection']} Historical Connections"}}]
                }
            })
            
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": f"Found {historical_connections['total_connections_found']} connections to your existing knowledge base."}}
                    ]
                }
            })
        
        # Knowledge Gaps
        knowledge_gaps = content_data.get('knowledge_gaps', [])
        if knowledge_gaps:
            blocks.append({
                "object": "block",
                "type": "heading_2", 
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"{self.emojis['gap']} Knowledge Gaps Identified"}}]
                }
            })
            
            for gap in knowledge_gaps[:3]:  # Show top 3 gaps
                priority_emoji = self.emojis.get(f"{gap.get('priority', 'medium')}_priority", self.emojis['medium_priority'])
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"{priority_emoji} {gap.get('missing_concept', 'Unknown')} - {gap.get('recommended_action', 'Review recommended')}"}}
                        ]
                    }
                })
        
        # Learning Recommendations
        recommendations = content_data.get('learning_recommendations', [])
        if recommendations:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"{self.emojis['recommendation']} Next Steps"}}]
                }
            })
            
            for rec in recommendations[:4]:  # Show top 4 recommendations
                priority_emoji = self.emojis.get(f"{rec.get('priority', 'medium')}_priority", self.emojis['medium_priority'])
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": f"{priority_emoji} {rec.get('action', 'No action specified')}"}}],
                        "checked": False
                    }
                })
        
        # Captured Sources
        if source_pages:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"{self.emojis['source']} Captured Sources"}}]
                }
            })
            
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": f"Captured {len(source_pages)} sources during this learning session."}}]
                }
            })
        
        # Add all blocks to the page
        try:
            requests.patch(
                f"{self.notion_api_url}/blocks/{page_id}/children",
                headers=self.headers,
                json={"children": blocks}
            )
            self.logger.info("Successfully added content to session page")
            
        except Exception as e:
            self.logger.warning(f"Failed to add content to session page: {str(e)}")

    def _update_concept_relationships(self, concept_pages: Dict, historical_connections: Dict, concepts_db_id: str):
        """Update concept relationships based on historical connections"""
        direct_connections = historical_connections.get('direct_connections', [])
        semantic_connections = historical_connections.get('semantic_connections', [])
        
        all_connections = direct_connections + semantic_connections
        
        for connection in all_connections:
            new_concept = connection.get('new_concept')
            existing_concept = connection.get('existing_concept')
            
            if new_concept in concept_pages and existing_concept:
                # Find the existing concept page ID
                existing_concept_id = self._find_existing_concept_page(existing_concept, concepts_db_id)
                
                if existing_concept_id:
                    try:
                        # Update the new concept page to add relationship
                        new_concept_page_id = concept_pages[new_concept]['id']
                        
                        # Get current relations
                        current_page = requests.get(
                            f"{self.notion_api_url}/pages/{new_concept_page_id}",
                            headers=self.headers
                        ).json()
                        
                        current_relations = current_page.get('properties', {}).get('Connected Concepts', {}).get('relation', [])
                        
                        # Add new relation if not already present
                        relation_ids = [rel['id'] for rel in current_relations]
                        if existing_concept_id not in relation_ids:
                            current_relations.append({"id": existing_concept_id})
                            
                            # Update the page
                            requests.patch(
                                f"{self.notion_api_url}/pages/{new_concept_page_id}",
                                headers=self.headers,
                                json={
                                    "properties": {
                                        "Connected Concepts": {"relation": current_relations}
                                    }
                                }
                            )
                            
                            self.logger.debug(f"Updated relationship: {new_concept} → {existing_concept}")
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to update concept relationship: {str(e)}")


# Helper function for testing Notion connection
def test_notion_connection():
    """Test if Notion API is accessible and properly configured"""
    notion_token = os.getenv('NOTION_TOKEN')
    
    if not notion_token:
        print("❌ NOTION_TOKEN environment variable not set")
        print("   Set your Notion integration token:")
        print("   export NOTION_TOKEN='your_notion_token_here'")
        return False
    
    try:
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        response = requests.get(
            "https://api.notion.com/v1/users/me",
            headers=headers
        )
        response.raise_for_status()
        
        user_data = response.json()
        print(f"✅ Notion API connection successful!")
        print(f"   Connected as: {user_data.get('name', 'Unknown User')}")
        print(f"   User ID: {user_data.get('id', 'Unknown')}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Notion API connection failed: {str(e)}")
        print("   Check your NOTION_TOKEN and internet connection")
        return False
    except Exception as e:
        print(f"❌ Notion connection test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Test connection when run directly
    print("🧪 Testing Notion API Connection...")
    test_notion_connection()