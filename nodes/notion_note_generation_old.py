# """
# Notion Note Generation Node: Creates rich, structured notes in Notion from pipeline analysis
# """

# import json
# import logging
# import os
# from datetime import datetime, timezone
# from typing import Dict, List, Any, Optional
# from collections import defaultdict
# import requests
# from urllib.parse import quote

# from dotenv import load_dotenv
# load_dotenv()

# from pocketflow import Node as BaseNode
# from .llm_client import get_llm_client

# class NotionNoteGenerationNode(BaseNode):
#     """    
#     Enhanced Notion Note Generation with:
#     - Topic-based page organization
#     - Rich content generation using existing pipeline data
#     - Minimal additional LLM calls (1-2 total)
#     - Beautiful Notion formatting
#     - Cross-topic relationship mapping
    
#     Input: All previous node outputs (captures, concepts, knowledge graph, historical analysis)
#     Process: Create Notion databases and pages with rich formatting and connections
#     Output: Notion page URLs and creation metadata
#     """

#     def __init__(self):
#         super().__init__()
#         self.logger = logging.getLogger(__name__)
        
#         # Notion API configuration
#         self.notion_token = os.getenv('NOTION_TOKEN')
#         self.notion_database_id = os.getenv('NOTION_DATABASE_ID')  # Optional: use existing database
        
#         self.notion_api_url = "https://api.notion.com/v1"
#         self.notion_version = "2022-06-28"
        
#         if not self.notion_token:
#             self.logger.error("NOTION_TOKEN environment variable not set")
#             raise ValueError("Notion API token required")
        
#         self.headers = {
#             "Authorization": f"Bearer {self.notion_token}",
#             "Content-Type": "application/json",
#             "Notion-Version": self.notion_version
#         }

#         # LLM for minimal enhancement
#         self.llm_client = None
#         self._initialize_llm()
        
#         # Enhanced database schemas for topic organization
#         self.database_schemas = self._init_enhanced_database_schemas()

#         # Rich formatting templates
#         self.formatting_templates = self._init_formatting_templates()

#         # Topic clustering strategies (rule-based to avoid LLM calls)
#         self.topic_indicators = {
#             'machine_learning': ['machine learning', 'ml', 'neural network', 'deep learning', 'algorithm', 'model training'],
#             'artificial_intelligence': ['artificial intelligence', 'ai', 'cognitive', 'intelligent systems'],
#             'data_science': ['data science', 'statistics', 'data analysis', 'visualization', 'big data'],
#             'software_engineering': ['programming', 'software', 'development', 'coding', 'engineering'],
#             'business_strategy': ['business', 'strategy', 'management', 'entrepreneurship', 'leadership'],
#             'psychology': ['psychology', 'cognitive', 'behavior', 'mental', 'psychological'],
#             'research_methods': ['research', 'methodology', 'experiment', 'study', 'analysis'],
#             'technology': ['technology', 'tech', 'innovation', 'digital', 'computing']
#         }
        
#         self.emojis = {
#             'session': '🧠',
#             'concept': '💡',
#             'source': '📚',
#             'connection': '🔗',
#             'gap': '⚠️',
#             'recommendation': '✅',
#             'high_priority': '🔥',
#             'medium_priority': '⚡',
#             'low_priority': '📝',
#             'review': '🔄',
#             'mastered': '⭐',
#             'learning': '📈',
#             'new': '🆕'
#         }

#     def _initialize_llm(self):
#         """Initialize LLM for minimal enhancement calls"""
#         try:
#             self.llm_client = get_llm_client()
#             self.logger.info(f"LLM initialized for enhanced Notion generation: {self.llm_client.get_provider_name()}")
#         except Exception as e:
#             self.logger.warning(f"LLM not available for enhanced features: {str(e)}")
#             self.llm_client = None

#     def _init_enhanced_database_schemas(self) -> Dict[str, Any]:
#         """Enhanced database schemas for topic-based organization"""
#         return {
#             'learning_sessions': {
#                 'title': '🧠 Smart Notes - Learning Sessions',
#                 'properties': {
#                     'Session Title': {'title': {}},
#                     'Date': {'date': {}},
#                     'Topics Covered': {'multi_select': {'options': []}},
#                     'Primary Theme': {'select': {'options': []}},
#                     'Knowledge Level': {
#                         'select': {
#                             'options': [
#                                 {'name': 'Beginner', 'color': 'green'},
#                                 {'name': 'Intermediate', 'color': 'yellow'},
#                                 {'name': 'Advanced', 'color': 'red'},
#                                 {'name': 'Expert', 'color': 'purple'}
#                             ]
#                         }
#                     },
#                     'Topics Count': {'number': {}},
#                     'Concepts Count': {'number': {}},
#                     'Cross-References': {'number': {}},
#                     'Completion Status': {
#                         'select': {
#                             'options': [
#                                 {'name': 'In Progress', 'color': 'yellow'},
#                                 {'name': 'Completed', 'color': 'green'},
#                                 {'name': 'Needs Review', 'color': 'orange'},
#                                 {'name': 'Archived', 'color': 'gray'}
#                             ]
#                         }
#                     }
#                 }
#             },
#             'research_topics': {
#                 'title': '📚 Smart Notes - Research Topics',
#                 'properties': {
#                     'Topic Name': {'title': {}},
#                     'Domain': {'select': {'options': []}},
#                     'Complexity Level': {
#                         'select': {
#                             'options': [
#                                 {'name': 'Foundational', 'color': 'green'},
#                                 {'name': 'Intermediate', 'color': 'yellow'},
#                                 {'name': 'Advanced', 'color': 'red'},
#                                 {'name': 'Cutting Edge', 'color': 'purple'}
#                             ]
#                         }
#                     },
#                     'Learning Status': {
#                         'select': {
#                             'options': [
#                                 {'name': 'New', 'color': 'gray'},
#                                 {'name': 'Learning', 'color': 'yellow'},
#                                 {'name': 'Understood', 'color': 'green'},
#                                 {'name': 'Mastered', 'color': 'blue'},
#                                 {'name': 'Teaching', 'color': 'purple'}
#                             ]
#                         }
#                     },
#                     'First Encountered': {'date': {}},
#                     'Last Reviewed': {'date': {}},
#                     'Session Count': {'number': {}},
#                     'Concepts Count': {'number': {}},
#                     'Practical Applications': {'number': {}},
#                     'Knowledge Gaps': {'number': {}},
#                     'Next Steps': {'rich_text': {}},
#                     'Tags': {'multi_select': {'options': []}}
#                 }
#             },
#             'concept_library': {
#                 'title': '💡 Smart Notes - Concept Library',
#                 'properties': {
#                     'Concept Name': {'title': {}},
#                     'Topic': {'select': {'options': []}},
#                     'Definition Quality': {
#                         'select': {
#                             'options': [
#                                 {'name': 'Clear', 'color': 'green'},
#                                 {'name': 'Partial', 'color': 'yellow'},
#                                 {'name': 'Unclear', 'color': 'red'},
#                                 {'name': 'Missing', 'color': 'gray'}
#                             ]
#                         }
#                     },
#                     'Understanding Level': {
#                         'select': {
#                             'options': [
#                                 {'name': 'Surface', 'color': 'red'},
#                                 {'name': 'Functional', 'color': 'yellow'},
#                                 {'name': 'Deep', 'color': 'green'},
#                                 {'name': 'Expert', 'color': 'blue'}
#                             ]
#                         }
#                     },
#                     'Confidence Score': {'number': {}},
#                     'First Learned': {'date': {}},
#                     'Times Encountered': {'number': {}},
#                     'Prerequisites': {'multi_select': {'options': []}},
#                     'Applications': {'multi_select': {'options': []}}
#                 }
#             }
#         }

#     def _init_formatting_templates(self) -> Dict[str, Any]:
#         """Initialize rich Notion formatting templates"""
#         return {
#             'topic_page_structure': {
#                 'header_with_emoji': True,
#                 'overview_callout': True,
#                 'progress_tracking': True,
#                 'concept_toggles': True,
#                 'application_examples': True,
#                 'cross_references': True,
#                 'next_steps_checklist': True
#             },
#             'content_blocks': {
#                 'overview_callout': {
#                     'type': 'callout',
#                     'icon': '🎯',
#                     'color': 'blue_background'
#                 },
#                 'key_insight': {
#                     'type': 'callout',
#                     'icon': '💡',
#                     'color': 'yellow_background'
#                 },
#                 'important_note': {
#                     'type': 'callout',
#                     'icon': '⚠️',
#                     'color': 'orange_background'
#                 },
#                 'success_tip': {
#                     'type': 'callout',
#                     'icon': '✅',
#                     'color': 'green_background'
#                 },
#                 'research_question': {
#                     'type': 'callout',
#                     'icon': '🤔',
#                     'color': 'purple_background'
#                 }
#             }
#         }

#     def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
#         """
#         Prepare for Notion note generation
#         """
#         self.logger.info("Starting Notion Note Generation prep phase")
        
#         # Validate inputs from previous nodes
#         pipeline_data = {
#             'session_id': shared_state.get('session_id'),
#             'raw_captures': shared_state.get('raw_captures', []),
#             'extracted_concepts': shared_state.get('extracted_concepts', {}),
#             'knowledge_graph': shared_state.get('knowledge_graph', {}),
#             'historical_connections': shared_state.get('historical_connections', {}),
#             'knowledge_gaps': shared_state.get('knowledge_gaps', []),
#             'learning_recommendations': shared_state.get('learning_recommendations', []),
#             'batch_metrics': shared_state.get('batch_metrics', {})
#         }

#         try:
#             self._test_notion_connection()
#             self.logger.info("Notion API connection successful")
#         except Exception as e:
#             self.logger.error(f"Notion API connection failed: {str(e)}")
#             return {'error': f'Notion API connection failed: {str(e)}'}

#         topic_organization = self._intelligent_topic_clustering(
#             pipeline_data['raw_captures'],
#             pipeline_data['extracted_concepts'].get('learning_concepts', [])
#         )

#         user_context = {
#             'knowledge_level': self._assess_session_knowledge_level(pipeline_data),
#             'learning_style': 'progressive',
#             'session_theme': pipeline_data['extracted_concepts'].get('session_theme', 'general')
#         }

#         enhanced_topics = {}
#         for topic_name, topic_data in topic_organization.items():
#             rich_content = self._generate_rich_topic_content(topic_data, user_context)
#             enhanced_topics[topic_name] = {
#                 **topic_data,
#                 'rich_content': rich_content
#             }
        
#         prep_data = {
#             'pipeline_data': pipeline_data,
#             'topic_organization': enhanced_topics,
#             'session_metadata': {
#                 'session_id': pipeline_data['session_id'],
#                 'timestamp': datetime.now(timezone.utc).isoformat(),
#                 'topics_identified': len(enhanced_topics),
#                 'total_concepts': len(pipeline_data['extracted_concepts'].get('learning_concepts', [])),
#                 'knowledge_level': self._assess_session_knowledge_level(pipeline_data),
#                 'enhancement_level': 'intelligent_clustering_with_rich_content'
#             }
#         }

#         return prep_data

#     def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
#         """
#         Core execution: Create topic organized Notion pages
#         """
#         if 'error' in prep_result:
#             return prep_result
            
#         self.logger.info("Starting Notion Note Generation core execution")

#         pipeline_data = prep_result['pipeline_data']
#         topic_organization = prep_result['topic_organization']
#         session_metadata = prep_result['session_metadata']
        
#         try:
#             # Step 1: Ensure enhanced databases exist
#             databases = self._ensure_enhanced_databases_exist()
            
#             # Step 2: Create topic pages (one per topic)
#             topic_pages = {}
#             for topic_name, enhanced_topic_data in topic_organization.items():
#                 rich_content = enhanced_topic_data.get('rich_content', {})
                
#                 topic_page = self._create_enhanced_topic_page(
#                     topic_name, 
#                     enhanced_topic_data, 
#                     rich_content,
#                     databases['research_topics'], 
#                     pipeline_data
#                 )
#                 if topic_page:
#                     topic_pages[topic_name] = topic_page
            
#             # Step 3: Create enhanced concept library entries
#             concept_entries = self._create_enhanced_concept_library_entries(
#                 pipeline_data['extracted_concepts'], 
#                 databases['concept_library'], 
#                 topic_organization
#             )
            
#             # Step 4: Enhanced synthesis
#             synthesis_insights = self._create_master_session_synthesis(
#                 topic_organization, 
#                 {},
#                 pipeline_data
#             )
            
#             # Step 5: Enhanced master page
#             master_session_page = self._create_enhanced_master_session_page(
#                 session_metadata, 
#                 pipeline_data, 
#                 topic_pages, 
#                 synthesis_insights,
#                 databases['learning_sessions']
#             )
            
#             # Step 6: Update database relationships
#             self._update_enhanced_database_relationships(databases, topic_pages, concept_entries, master_session_page)
            
#             return {
#                 'master_session_page': master_session_page,
#                 'topic_pages': topic_pages,
#                 'concept_entries': concept_entries,
#                 'synthesis_insights': synthesis_insights,
#                 'databases': databases,
#                 'creation_summary': {
#                     'session_created': bool(master_session_page),
#                     'topic_pages_created': len(topic_pages),
#                     'concepts_created': len(concept_entries),
#                     'sources_created': len(pipeline_data['raw_captures']),
#                     'total_pages': 1 + len(topic_pages) + len(concept_entries),
#                     'topics_covered': list(topic_organization.keys()),
#                     'enhancement_features_used': [
#                         'intelligent_topic_clustering',
#                         'rich_content_generation', 
#                         'cross_topic_synthesis',
#                         'interactive_progress_tracking',
#                         'memory_aids_integration'
#                     ]
#                 },
#                 'session_page_url': self._get_page_url(master_session_page),
#                 'notion_urls': {
#                     'master_session': self._get_page_url(master_session_page),
#                     'topic_pages': {name: self._get_page_url(page) for name, page in topic_pages.items()},
#                     'databases': {
#                         'sessions': f"https://notion.so/{databases['learning_sessions'].replace('-', '')}",
#                         'topics': f"https://notion.so/{databases['research_topics'].replace('-', '')}",
#                         'concepts': f"https://notion.so/{databases['concept_library'].replace('-', '')}"
#                     }
#                 }
#             }
#         except Exception as e:
#             self.logger.error(f"Enhanced Notion generation failed: {str(e)}")
#             return {'error': f"Enhanced Notion generation failed: {str(e)}"}


#     def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
#         """
#         Post-processing: Store enhanced Notion results
#         """
#         self.logger.info("Notion Note Generation post-execution phase")
        
#         if 'error' in exec_result:
#             shared_state['notion_generation_error'] = exec_result['error']
#             return "error"
        
#         # Store Notion results in shared_state
#         shared_state['notion_generation'] = {
#             'master_session_url': exec_result['notion_urls']['master_session'],
#             'topic_pages': exec_result['notion_urls']['topic_pages'],
#             'databases': exec_result['databases'],
#             'creation_summary': exec_result['creation_summary'],
#             'synthesis_insights': exec_result['synthesis_insights'],
#             'generated_at': datetime.now(timezone.utc).isoformat(),
#             'enhancement_level': 'rich_topic_organized'
#         }
        
#         # Update pipeline metadata
#         shared_state['pipeline_metadata']['notion_generation_complete'] = True
#         shared_state['pipeline_metadata']['notion_generation_summary'] = {
#             'total_pages_created': exec_result['creation_summary']['total_pages'],
#             'master_session_url': exec_result['notion_urls']['master_session'],
#             'topic_pages_created': exec_result['creation_summary']['topic_pages_created'],
#             'concepts_documented': exec_result['creation_summary']['concepts_created'],
#             'topics_covered': exec_result['creation_summary']['topics_covered']
#         }
        
#         self.logger.info(f"Enhanced Notion generation complete - {exec_result['creation_summary']['total_pages']} pages created")
#         return "default"


#     def _prepare_content_for_clustering(self, captures: List[Dict], concepts: List[str]) -> str:
#         """Prepare content summary for LLM clustering analysis"""
#         content_summary = []
        
#         for i, capture in enumerate(captures[:10]):  # Limit for prompt size
#             title = capture.get('title', f'Source {i+1}')
#             content_preview = capture.get('content', '')[:200]
#             content_summary.append(f"[{title}]: {content_preview}...")
        
#         return '\n'.join(content_summary)

#     def _assign_captures_to_topics(self, llm_topics: List[Dict], captures: List[Dict], concepts: List[str]) -> Dict[str, Any]:
#         """Assign captures and concepts to LLM-identified topics"""
#         topic_organization = {}
        
#         for topic_info in llm_topics:
#             topic_name = topic_info.get('topic_name', 'Unknown Topic')
#             related_concepts = topic_info.get('related_concepts', [])
            
#             # Find captures that relate to this topic
#             topic_captures = []
#             topic_concepts = []
            
#             # Match captures by content similarity
#             topic_keywords = topic_name.lower().split() + [c.lower() for c in related_concepts]
            
#             for capture in captures:
#                 content = (capture.get('content', '') + ' ' + capture.get('title', '')).lower()
#                 if any(keyword in content for keyword in topic_keywords):
#                     topic_captures.append(capture)
            
#             # Match concepts
#             for concept in concepts:
#                 if concept.lower() in [c.lower() for c in related_concepts] or \
#                    any(keyword in concept.lower() for keyword in topic_keywords):
#                     topic_concepts.append(concept)
            
#             # Only include topics with content
#             if topic_captures or topic_concepts:
#                 topic_organization[topic_name] = {
#                     'topic_name': topic_name,
#                     'scope': topic_info.get('scope', f'Study of {topic_name.lower()}'),
#                     'complexity': topic_info.get('complexity_level', 'intermediate'),
#                     'learning_objectives': topic_info.get('learning_objectives', []),
#                     'captures': topic_captures,
#                     'concepts': topic_concepts,
#                     'confidence': topic_info.get('confidence', 0.7),
#                     'source_count': len(topic_captures)
#                 }
        
#         return topic_organization


#     def _fallback_rule_based_clustering(self, captures: List[Dict], concepts: List[str]) -> Dict[str, Any]:
#         """Fallback rule-based clustering when LLM is unavailable"""
#         return self._identify_topics_from_content(captures, concepts)


#     def _create_enhanced_topic_page(self, topic_name: str, enhanced_topic_data: Dict[str, Any], 
#                                rich_content: Dict[str, Any], topics_db_id: str, 
#                                pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Create enhanced topic page with rich content"""
#         try:
#             self.logger.info(f"Creating topic page for: {topic_name}")

#             learning_objectives = enhanced_topic_data.get('learning_objectives', [])
#             self.logger.info(f"Learning objectives: {learning_objectives}, type: {type(learning_objectives)}")
            
#             # Determine topic emoji and color theme
#             topic_emoji, color_theme = self._get_topic_visual_theme(topic_name)
#             self.logger.info(f"Topic emoji: {topic_emoji}, type: {type(topic_emoji)}")

#             # Ensure all values are properly converted to strings and handle Unicode properly
#             complexity = str(enhanced_topic_data.get('complexity', 'Intermediate')).title()
#             learning_sequence = enhanced_topic_data.get('learning_sequence', ['Continue learning'])
#             next_step = str(learning_sequence[0]) if learning_sequence else 'Continue learning'
            
#             # Clean the emoji to avoid Unicode issues
#             clean_emoji = str(topic_emoji).encode('utf-8').decode('utf-8') if topic_emoji else '📚'
            
#             # Format the title properly - ensure clean string concatenation
#             page_title = f"{clean_emoji} {str(topic_name)}"
#             domain_name = str(self._classify_domain(topic_name))
            
#             # Create database entry for topic with proper string formatting
#             page_data = {
#                 "parent": {"database_id": str(topics_db_id)},
#                 "properties": {
#                     "Topic Name": {
#                         "title": [
#                             {
#                                 "text": {
#                                     "content": page_title
#                                 }
#                             }
#                         ]
#                     },
#                     "Domain": {
#                         "select": {
#                             "name": domain_name
#                         }
#                     },
#                     "Complexity Level": {
#                         "select": {
#                             "name": complexity
#                         }
#                     },
#                     "Learning Status": {
#                         "select": {
#                             "name": "Learning"
#                         }
#                     },
#                     "First Encountered": {
#                         "date": {
#                             "start": datetime.now(timezone.utc).isoformat()
#                         }
#                     },
#                     "Last Reviewed": {
#                         "date": {
#                             "start": datetime.now(timezone.utc).isoformat()
#                         }
#                     },
#                     "Session Count": {
#                         "number": 1
#                     },
#                     "Concepts Count": {
#                         "number": len(enhanced_topic_data.get('concepts', []))
#                     },
#                     "Practical Applications": {
#                         "number": len(enhanced_topic_data.get('practical_applications', []))
#                     },
#                     "Knowledge Gaps": {
#                         "number": len([gap for gap in pipeline_data.get('knowledge_gaps', []) 
#                                     if self._gap_relates_to_topic(gap, topic_name)])
#                     },
#                     "Next Steps": {
#                         "rich_text": [
#                             {
#                                 "text": {
#                                     "content": next_step
#                                 }
#                             }
#                         ]
#                     }
#                 }
#             }
            
#             self.logger.info(f"Page data structure: {json.dumps(page_data, indent=2, default=str, ensure_ascii=False)}")

#             try:
#                 # Use explicit JSON encoding to handle Unicode properly
#                 json_data = json.dumps(page_data, ensure_ascii=False, default=str)
                
#                 response = requests.post(
#                     f"{self.notion_api_url}/pages",
#                     headers=self.headers,
#                     data=json_data.encode('utf-8'),
#                     timeout=30
#                 )
                
#                 # Check response status
#                 if response.status_code != 200:
#                     self.logger.error(f"Notion API error {response.status_code}: {response.text}")
#                     return {}
                
#                 topic_page = response.json()
                
#                 # Add rich content to the page
#                 self._add_rich_topic_content(topic_page['id'], topic_name, enhanced_topic_data, pipeline_data, color_theme)
                
#                 return topic_page
                
#             except requests.exceptions.HTTPError as e:
#                 self.logger.error(f"HTTP error creating topic page for '{topic_name}': {str(e)}")
#                 if hasattr(e.response, 'text'):
#                     self.logger.error(f"Response text: {e.response.text}")
#                 return {}
#             except json.JSONDecodeError as e:
#                 self.logger.error(f"JSON decode error for '{topic_name}': {str(e)}")
#                 return {}
#             except Exception as e:
#                 self.logger.error(f"Failed to create enhanced topic page for '{topic_name}': {str(e)}")
#                 import traceback
#                 self.logger.error(traceback.format_exc())
#                 return {}
                
#         except Exception as e:
#             self.logger.error(f"Error creating topic page for '{topic_name}': {str(e)}")
#             import traceback
#             self.logger.error(traceback.format_exc())
#             return {}


#     def _create_enhanced_concept_library_entries(self, extracted_concepts: Dict[str, Any], 
#                                            concepts_db_id: str, topic_organization: Dict[str, Any]) -> List[Dict[str, Any]]:
#         """Create enhanced concept library entries"""
#         entries = []
#         learning_concepts = extracted_concepts.get('learning_concepts', [])
#         key_terms = extracted_concepts.get('key_terms', {})
        
#         for concept in learning_concepts:
#             try:
#                 # Find which topic this concept belongs to
#                 topic_name = 'General'
#                 for t_name, t_data in topic_organization.items():
#                     if concept in t_data.get('concepts', []):
#                         topic_name = t_name
#                         break
                
#                 # Get definition quality based on key_terms
#                 definition_quality = "Clear" if concept in key_terms else "Partial"
                
#                 # Ensure all values are properly formatted as strings
#                 entry_data = {
#                     "parent": {"database_id": str(concepts_db_id)},
#                     "properties": {
#                         "Concept Name": {
#                             "title": [
#                                 {
#                                     "text": {
#                                         "content": str(concept)
#                                     }
#                                 }
#                             ]
#                         },
#                         "Topic": {
#                             "select": {
#                                 "name": str(topic_name)
#                             }
#                         },
#                         "Definition Quality": {
#                             "select": {
#                                 "name": str(definition_quality)
#                             }
#                         },
#                         "Understanding Level": {
#                             "select": {
#                                 "name": "Functional"
#                             }
#                         },
#                         "Confidence Score": {
#                             "number": 75 if definition_quality == "Clear" else 60
#                         },
#                         "First Learned": {
#                             "date": {
#                                 "start": datetime.now(timezone.utc).isoformat()
#                             }
#                         },
#                         "Times Encountered": {
#                             "number": 1
#                         }
#                     }
#                 }
                
#                 # Use explicit JSON encoding
#                 json_data = json.dumps(entry_data, ensure_ascii=False, default=str)
                
#                 response = requests.post(
#                     f"{self.notion_api_url}/pages", 
#                     headers=self.headers, 
#                     data=json_data.encode('utf-8'),
#                     timeout=30
#                 )
                
#                 if response.status_code == 200:
#                     entry = response.json()
#                     # Add concept content if available
#                     if concept in key_terms:
#                         self._add_concept_content(entry['id'], concept, key_terms[concept])
#                     entries.append(entry)
#                 else:
#                     self.logger.error(f"Failed to create concept entry for {concept}: {response.status_code} - {response.text}")
                    
#             except Exception as e:
#                 self.logger.error(f"Error creating concept entry for {concept}: {str(e)}")
#                 continue
        
#         return entries


#     def _create_enhanced_master_session_page(self, session_metadata: Dict[str, Any], 
#                                        pipeline_data: Dict[str, Any], topic_pages: Dict[str, Any], 
#                                        synthesis_insights: Dict[str, Any], sessions_db_id: str) -> Dict[str, Any]:
#         """Create enhanced master session page"""
        
#         try:
#             # Generate session story for memory reconstruction
#             session_story = self._generate_session_story(pipeline_data, session_metadata)
#             session_theme = pipeline_data['extracted_concepts'].get('session_theme', 'Knowledge Exploration')
            
#             session_title = session_story.get('title', session_theme.replace('_', ' ').title())
#             primary_theme = session_theme.replace('_', ' ').title()
#             knowledge_level = str(session_metadata['knowledge_level'])
            
#             # Safely create multi_select values - limit to 10 and ensure strings
#             topics_covered = []
#             for topic in list(topic_pages.keys())[:10]:  # Limit to 10 topics
#                 # Clean topic name for Notion
#                 clean_topic = str(topic).strip()
#                 if clean_topic:  # Only add non-empty topics
#                     topics_covered.append({"name": clean_topic})
            
#             page_data = {
#                 "parent": {"database_id": str(sessions_db_id)},
#                 "properties": {
#                     "Session Title": {
#                         "title": [
#                             {
#                                 "text": {
#                                     "content": f"🧠 {str(session_title)}"
#                                 }
#                             }
#                         ]
#                     },
#                     "Date": {
#                         "date": {
#                             "start": session_metadata['timestamp']
#                         }
#                     },
#                     "Topics Covered": {
#                         "multi_select": topics_covered
#                     },
#                     "Primary Theme": {
#                         "select": {
#                             "name": str(primary_theme)
#                         }
#                     },
#                     "Knowledge Level": {
#                         "select": {
#                             "name": knowledge_level
#                         }
#                     },
#                     "Topics Count": {
#                         "number": len(topic_pages)
#                     },
#                     "Concepts Count": {
#                         "number": session_metadata['total_concepts']
#                     },
#                     "Cross-References": {
#                         "number": pipeline_data.get('historical_connections', {}).get('total_connections_found', 0)
#                     },
#                     "Completion Status": {
#                         "select": {
#                             "name": "Completed"
#                         }
#                     }
#                 }
#             }
            
#             # Use explicit JSON encoding
#             json_data = json.dumps(page_data, ensure_ascii=False, default=str)
            
#             response = requests.post(
#                 f"{self.notion_api_url}/pages", 
#                 headers=self.headers, 
#                 data=json_data.encode('utf-8'),
#                 timeout=30
#             )
            
#             if response.status_code == 200:
#                 master_page = response.json()
                
#                 # Add memory-focused content
#                 self._add_memory_focused_master_content(master_page['id'], session_story, pipeline_data, topic_pages)
#                 return master_page
#             else:
#                 self.logger.error(f"Failed to create master session page: {response.status_code} - {response.text}")
#                 return {}
                
#         except Exception as e:
#             self.logger.error(f"Error creating master session page: {str(e)}")
#             import traceback
#             self.logger.error(traceback.format_exc())
#             return {}


#     def _generate_session_story(self, pipeline_data: Dict, session_metadata: Dict) -> Dict[str, Any]:
#         """Generate compelling session narrative for memory reconstruction"""
        
#         if not self.llm_client or not self.llm_client.is_available():
#             return self._create_basic_session_story(pipeline_data, session_metadata)
        
#         try:
#             concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
#             session_theme = pipeline_data['extracted_concepts'].get('session_theme', 'exploration')
            
#             story_prompt = f"""Create a memorable learning session story:

#     SESSION DATA:
#     - Theme: {session_theme}
#     - Concepts learned: {', '.join(concepts[:10])}
#     - Knowledge level: {session_metadata['knowledge_level']}
#     - Total topics: {session_metadata.get('topics_identified', 1)}

#     Write a 2-3 sentence story that captures:
#     1. What sparked this learning session
#     2. The intellectual journey taken
#     3. Key breakthroughs achieved

#     Use second person ("You discovered...", "This led you to...") for personal connection.
#     Also provide a compelling session title.

#     Return JSON: {{"title": "session title", "story": "2-3 sentence narrative", "spark": "what triggered learning", "breakthrough": "key insight gained"}}"""

#             messages = [
#                 {"role": "system", "content": "Create memorable learning narratives that help users recollect their intellectual journeys."},
#                 {"role": "user", "content": story_prompt}
#             ]
            
#             request_params = self.llm_client.set_provider_specific_defaults(temperature=0.4, max_tokens=400)
#             response_text = self.llm_client.chat_completion(messages, **request_params)
#             return json.loads(response_text)
            
#         except Exception as e:
#             self.logger.warning(f"Session story generation failed: {str(e)}")
#             return self._create_basic_session_story(pipeline_data, session_metadata)


#     def _create_basic_session_story(self, pipeline_data: Dict, session_metadata: Dict) -> Dict[str, Any]:
#         """Create basic session story when LLM unavailable"""
#         concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
#         theme = pipeline_data['extracted_concepts'].get('session_theme', 'exploration')
        
#         return {
#             'title': f"Deep Dive: {theme.replace('_', ' ').title()}",
#             'story': f"You explored {theme.replace('_', ' ')} by diving into {len(concepts)} key concepts. This session built your understanding through practical examples and real-world applications.",
#             'spark': f"Curiosity about {theme.replace('_', ' ')}",
#             'breakthrough': f"Understanding how {concepts[0] if concepts else 'core concepts'} work in practice"
#         }


#     def _add_memory_focused_master_content(self, page_id: str, session_story: Dict, 
#                                         pipeline_data: Dict, topic_pages: Dict):
#         """Add memory-focused content to master session page"""
        
#         blocks = []
        
#         # Hero section with session story
#         blocks.extend(self._create_session_hero_section(session_story, pipeline_data))
        
#         # Quick scan takeaways
#         blocks.extend(self._create_quick_scan_section(pipeline_data, topic_pages))
        
#         # Topic navigation with memory anchors
#         blocks.extend(self._create_topic_navigation_section(topic_pages))
        
#         # Questions that arose
#         blocks.extend(self._create_curiosity_section(pipeline_data))
        
#         # Knowledge connections found
#         blocks.extend(self._create_connections_highlight(pipeline_data))
        
#         # Strategic next steps
#         blocks.extend(self._create_strategic_actions(pipeline_data))
        
#         try:
#             # Add content in batches
#             batch_size = 100
#             for i in range(0, len(blocks), batch_size):
#                 batch_blocks = blocks[i:i + batch_size]
#                 requests.patch(
#                     f"{self.notion_api_url}/blocks/{page_id}/children",
#                     headers=self.headers,
#                     json={"children": batch_blocks}
#                 )
            
#             self.logger.info("Memory-focused master content added successfully")
#         except Exception as e:
#             self.logger.warning(f"Failed to add master content: {str(e)}")


#     def _create_connections_highlight(self, pipeline_data):
#         """Create knowledge connections highlight section"""
#         blocks = []
        
#         historical_connections = pipeline_data.get('historical_connections', {})
#         connections_count = historical_connections.get('total_connections_found', 0)
        
#         if connections_count > 0:
#             blocks.append({
#                 "object": "block",
#                 "type": "heading_2",
#                 "heading_2": {
#                     "rich_text": [{"type": "text", "text": {"content": "🔗 Knowledge Connections Found"}}]
#                 }
#             })
            
#             blocks.append({
#                 "object": "block",
#                 "type": "callout",
#                 "callout": {
#                     "rich_text": [{"type": "text", "text": {"content": f"Discovered {connections_count} connections to your existing knowledge, strengthening cross-domain understanding."}}],
#                     "icon": {"emoji": "🌟"},
#                     "color": "yellow_background"
#                 }
#             })
        
#         return blocks


#     def _create_contextual_sources_section(self, topic_data):
#         """Create sources section with context"""
#         blocks = []
        
#         captures = topic_data.get('captures', [])
#         if not captures:
#             return blocks
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "📚 Learning Sources"}}]
#             }
#         })
        
#         for capture in captures[:5]:  # Limit to 5 most important
#             title = capture.get('title', 'Untitled Source')
#             url = capture.get('url', '')
#             content_preview = capture.get('content', '')[:100] + "..." if len(capture.get('content', '')) > 100 else capture.get('content', '')
            
#             if url and url != 'unknown':
#                 blocks.append({
#                     "object": "block",
#                     "type": "callout",
#                     "callout": {
#                         "rich_text": [
#                             {"type": "text", "text": {"content": "📖 "}},
#                             {"type": "text", "text": {"content": title}, "link": {"url": url}},
#                             {"type": "text", "text": {"content": f"\n{content_preview}"}}
#                         ],
#                         "icon": {"emoji": "📖"},
#                         "color": "gray_background"
#                     }
#                 })
#             else:
#                 blocks.append({
#                     "object": "block",
#                     "type": "callout",
#                     "callout": {
#                         "rich_text": [{"type": "text", "text": {"content": f"📄 {title}\n{content_preview}"}}],
#                         "icon": {"emoji": "📄"},
#                         "color": "gray_background"
#                     }
#                 })
        
#         return blocks


#     def _create_session_hero_section(self, session_story: Dict, pipeline_data: Dict) -> List[Dict]:
#         """Create compelling hero section with session story"""
#         blocks = []
        
#         # Session title with story
#         title = session_story.get('title', 'Learning Session')
#         story = session_story.get('story', 'A journey of discovery and understanding.')
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_1",
#             "heading_1": {
#                 "rich_text": [{"type": "text", "text": {"content": f"🧠 {title}"}}],
#                 "color": "blue"
#             }
#         })
        
#         # Story callout
#         blocks.append({
#             "object": "block",
#             "type": "callout",
#             "callout": {
#                 "rich_text": [{"type": "text", "text": {"content": story}}],
#                 "icon": {"emoji": "✨"},
#                 "color": "blue_background"
#             }
#         })
        
#         # What sparked this learning
#         spark = session_story.get('spark', 'Intellectual curiosity')
#         blocks.append({
#             "object": "block",
#             "type": "quote",
#             "quote": {
#                 "rich_text": [{"type": "text", "text": {"content": f"🔥 What sparked this: {spark}"}}],
#                 "color": "orange"
#             }
#         })
        
#         return blocks


#     def _create_quick_scan_section(self, pipeline_data: Dict, topic_pages: Dict) -> List[Dict]:
#         """Create scannable takeaways for quick recall"""
#         blocks = []
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "⚡ Quick Scan - Key Takeaways"}}]
#             }
#         })
        
#         # Extract key insights
#         concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
#         connections = pipeline_data.get('historical_connections', {}).get('total_connections_found', 0)
        
#         takeaways = [
#             f"🧠 Mastered {len(concepts)} new concepts across {len(topic_pages)} topics",
#             f"🔗 Found {connections} connections to existing knowledge" if connections > 0 else None,
#             f"💡 Key breakthrough: {concepts[0]}" if concepts else None,
#             f"📚 Explored {len(topic_pages)} distinct knowledge areas"
#         ]
        
#         for takeaway in takeaways:
#             if takeaway:
#                 blocks.append({
#                     "object": "block",
#                     "type": "bulleted_list_item",
#                     "bulleted_list_item": {
#                         "rich_text": [{"type": "text", "text": {"content": takeaway}}]
#                     }
#                 })
        
#         return blocks


#     def _create_topic_navigation_section(self, topic_pages: Dict) -> List[Dict]:
#         """Create topic navigation with visual memory anchors"""
#         blocks = []
        
#         if not topic_pages:
#             return blocks
            
#         blocks.append({
#             "object": "block",
#             "type": "heading_2", 
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "🗺️ Knowledge Areas Explored"}}]
#             }
#         })
        
#         for topic_name, topic_page in topic_pages.items():
#             topic_emoji, _ = self._get_topic_visual_theme(topic_name)
#             topic_url = self._get_page_url(topic_page)
            
#             if topic_url:
#                 blocks.append({
#                     "object": "block",
#                     "type": "callout",
#                     "callout": {
#                         "rich_text": [
#                             {"type": "text", "text": {"content": f"{topic_emoji} "}},
#                             {"type": "text", "text": {"content": topic_name}, "link": {"url": topic_url}}
#                         ],
#                         "icon": {"emoji": topic_emoji},
#                         "color": "gray_background"
#                     }
#                 })
#             else:
#                 blocks.append({
#                     "object": "block",
#                     "type": "paragraph",
#                     "paragraph": {
#                         "rich_text": [{"type": "text", "text": {"content": f"{topic_emoji} {topic_name}"}}]
#                     }
#                 })
        
#         return blocks


#     def _create_curiosity_section(self, pipeline_data: Dict) -> List[Dict]:
#         """Create section for questions that arose during learning"""
#         blocks = []
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "🤔 Questions That Emerged"}}]
#             }
#         })
        
#         # Generate curiosity questions based on concepts
#         concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        
#         if self.llm_client and self.llm_client.is_available():
#             try:
#                 curiosity_prompt = f"""Generate 3-4 natural questions that would arise after learning about: {', '.join(concepts[:8])}

#     Questions should:
#     - Show intellectual curiosity
#     - Point toward deeper exploration  
#     - Connect to practical applications
#     - Drive continued learning

#     Return as simple list of questions."""

#                 messages = [
#                     {"role": "system", "content": "Generate thought-provoking questions that drive continued learning."},
#                     {"role": "user", "content": curiosity_prompt}
#                 ]
                
#                 request_params = self.llm_client.set_provider_specific_defaults(temperature=0.3, max_tokens=300)
#                 response_text = self.llm_client.chat_completion(messages, **request_params)
                
#                 # Parse questions from response
#                 questions = [q.strip('- ').strip() for q in response_text.split('\n') if q.strip() and '?' in q]
                
#             except Exception as e:
#                 self.logger.warning(f"Curiosity question generation failed: {str(e)}")
#                 questions = self._generate_basic_curiosity_questions(concepts)
#         else:
#             questions = self._generate_basic_curiosity_questions(concepts)
        
#         for question in questions[:4]:
#             blocks.append({
#                 "object": "block",
#                 "type": "callout",
#                 "callout": {
#                     "rich_text": [{"type": "text", "text": {"content": question}}],
#                     "icon": {"emoji": "🤔"},
#                     "color": "purple_background"
#                 }
#             })
        
#         return blocks


#     def _generate_basic_curiosity_questions(self, concepts: List[str]) -> List[str]:
#         """Generate basic curiosity questions when LLM unavailable"""
#         if not concepts:
#             return ["What should I explore next?", "How can I apply this knowledge?"]
        
#         return [
#             f"How does {concepts[0]} work in real-world applications?",
#             f"What are the limitations of {concepts[1] if len(concepts) > 1 else concepts[0]}?",
#             f"How do these concepts connect to other fields I'm interested in?",
#             "What problems can I solve with this new knowledge?"
#         ]


#     def _create_strategic_actions(self, pipeline_data: Dict) -> List[Dict]:
#         """Create actionable next steps section"""
#         blocks = []
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "🎯 What to Do Next"}}]
#             }
#         })
        
#         # Get recommendations from pipeline
#         recommendations = pipeline_data.get('learning_recommendations', [])
#         concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        
#         # Create actionable steps
#         actions = []
        
#         # High priority actions from recommendations
#         high_priority = [r for r in recommendations if r.get('priority') == 'high']
#         for rec in high_priority[:2]:
#             action = rec.get('action', rec.get('recommended_action', ''))
#             if action:
#                 actions.append(f"🔥 {action}")
        
#         # Practice/application actions
#         if concepts:
#             actions.append(f"🛠️ Practice applying {concepts[0]} in a real project")
#             actions.append(f"👥 Teach {concepts[0]} to someone else to solidify understanding")
        
#         # Review actions
#         actions.append("📅 Schedule review of key concepts in 3 days")
        
#         for action in actions[:5]:
#             blocks.append({
#                 "object": "block",
#                 "type": "to_do",
#                 "to_do": {
#                     "rich_text": [{"type": "text", "text": {"content": action}}],
#                     "checked": False
#                 }
#             })
        
#         return blocks


#     def _update_enhanced_database_relationships(self, databases: Dict[str, str], 
#                                               topic_pages: Dict[str, Any], concept_entries: List[Dict[str, Any]], 
#                                               master_session_page: Dict[str, Any]):
#         """Update enhanced database relationships"""
#         try:
#             # Link concept entries to topic pages
#             for concept_entry in concept_entries:
#                 concept_id = concept_entry.get('id')
#                 if concept_id:
#                     # Find related topic page
#                     concept_name = concept_entry.get('properties', {}).get('Concept Name', {}).get('title', [{}])[0].get('plain_text', '')
#                     for topic_name, topic_page in topic_pages.items():
#                         topic_data = next((data for name, data in topic_pages.items() if name == topic_name), {})
#                         if concept_name in str(topic_data):
#                             # Update concept with topic relation
#                             try:
#                                 requests.patch(
#                                     f"{self.notion_api_url}/pages/{concept_id}",
#                                     headers=self.headers,
#                                     json={
#                                         "properties": {
#                                             "From Topics": {
#                                                 "relation": [{"id": topic_page.get('id')}]
#                                             }
#                                         }
#                                     }
#                                 )
#                             except Exception as e:
#                                 self.logger.warning(f"Failed to link concept to topic: {str(e)}")
            
#             self.logger.info("Enhanced database relationships updated")
#         except Exception as e:
#             self.logger.warning(f"Failed to update enhanced database relationships: {str(e)}")


#     def _add_interactive_elements(self, rich_content: Dict[str, Any], topic_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Add interactive elements to rich content"""
#         if not rich_content:
#             rich_content = {}
        
#         # Add interactive progress tracking
#         rich_content['interactive_elements'] = {
#             'progress_tracker': {
#                 'milestones': [
#                     {'title': 'Understand core concepts', 'completed': False},
#                     {'title': 'Practice applications', 'completed': False},
#                     {'title': 'Connect to existing knowledge', 'completed': False}
#                 ]
#             },
#             'self_assessment': {
#                 'questions': [
#                     f"Can you explain {topic_data.get('topic_name', 'this topic')} in your own words?",
#                     f"What real-world applications do you see for {topic_data.get('topic_name', 'this topic')}?",
#                     f"How does {topic_data.get('topic_name', 'this topic')} connect to what you already know?"
#                 ]
#             },
#             'review_schedule': {
#                 'intervals': ['1 day', '3 days', '1 week', '2 weeks', '1 month'],
#                 'next_review': '1 day'
#             }
#         }
        
#         return rich_content


#     def _generate_basic_topic_content(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Generate basic topic content when LLM is unavailable"""
#         topic_name = topic_data.get('topic_name', 'Topic')
#         concepts = topic_data.get('concepts', [])
        
#         return {
#             'executive_summary': {
#                 'overview': f"Comprehensive study of {topic_name.lower()} covering key concepts and practical applications.",
#                 'importance': f"Understanding {topic_name.lower()} is essential for building foundational knowledge in this domain."
#             },
#             'concepts_deep_dive': {
#                 'concepts': [
#                     {
#                         'name': concept,
#                         'explanation': f"Key concept in {topic_name.lower()}",
#                         'examples': [f"Example application of {concept}"],
#                         'analogies': [f"Think of {concept} like a fundamental building block"]
#                     } for concept in concepts[:5]
#                 ]
#             },
#             'practical_applications': {
#                 'applications': topic_data.get('practical_applications', [f"Apply {topic_name.lower()} concepts in real-world scenarios"])
#             },
#             'learning_progression': {
#                 'milestones': [
#                     {'title': f'Understand {topic_name.lower()} fundamentals', 'description': 'Master core concepts'},
#                     {'title': f'Practice {topic_name.lower()} applications', 'description': 'Apply knowledge practically'},
#                     {'title': f'Synthesize {topic_name.lower()} knowledge', 'description': 'Connect to broader understanding'}
#                 ]
#             },
#             'memory_aids': {
#                 'mnemonics': [f"Remember {topic_name.lower()} through practical examples"],
#                 'spaced_repetition': {
#                     'schedule': [
#                         {'topics': concepts[:3], 'timing': 'Review in 1 day'},
#                         {'topics': concepts[:3], 'timing': 'Review in 3 days'},
#                         {'topics': concepts[:3], 'timing': 'Review in 1 week'}
#                     ]
#                 }
#             }
#         }


#     def _create_basic_master_synthesis(self, all_topics: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Create basic master synthesis when LLM is unavailable"""
#         topic_count = len(all_topics)
#         total_concepts = sum(len(topic_data.get('concepts', [])) for topic_data in all_topics.values())
        
#         return {
#             'session_overview': {
#                 'title': f'Multi-Topic Learning Session ({topic_count} Topics)',
#                 'narrative': f'Comprehensive learning session covering {topic_count} topics with {total_concepts} concepts explored.',
#                 'key_insights': [f'Explored {topic_count} interconnected topics', f'Mastered {total_concepts} new concepts']
#             },
#             'topic_relationship_map': {
#                 'relationships': [f'{topic1} connects to {topic2} through shared concepts' 
#                                for i, topic1 in enumerate(all_topics.keys()) 
#                                for j, topic2 in enumerate(all_topics.keys()) 
#                                if i < j][:3]
#             },
#             'strategic_next_steps': {
#                 'high_impact_priorities': [
#                     'Review and consolidate learning across all topics',
#                     'Practice applying concepts from different topics together',
#                     'Identify and fill knowledge gaps discovered',
#                     'Connect new learning to existing knowledge base'
#                 ]
#             },
#             'synthesis_insights': {
#                 'cross_connections': topic_count * (topic_count - 1) // 2,
#                 'knowledge_integration_score': min(topic_count * 20, 100),
#                 'learning_efficiency': 'high' if topic_count <= 3 else 'moderate'
#             }
#         }


#     def _get_page_url(self, page: Dict[str, Any]) -> str:
#         """Get Notion page URL"""
#         if not page or 'id' not in page:
#             return ""
        
#         page_id = page['id'].replace('-', '')
#         return f"https://notion.so/{page_id}"


#     def _add_concept_content(self, page_id: str, concept_name: str, definition: str):
#         """Add content to a concept page"""
#         blocks = [
#             {
#                 "object": "block",
#                 "type": "heading_1",
#                 "heading_1": {
#                     "rich_text": [{"type": "text", "text": {"content": f"💡 {concept_name}"}}]
#                 }
#             },
#             {
#                 "object": "block",
#                 "type": "callout",
#                 "callout": {
#                     "rich_text": [{"type": "text", "text": {"content": definition}}],
#                     "icon": {"emoji": "📚"},
#                     "color": "blue_background"
#                 }
#             }
#         ]
        
#         try:
#             requests.patch(
#                 f"{self.notion_api_url}/blocks/{page_id}/children",
#                 headers=self.headers,
#                 json={"children": blocks}
#             )
#         except Exception as e:
#             self.logger.warning(f"Failed to add content to concept page: {str(e)}")


#     def _enhance_topics_with_llm(self, topic_organization: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
#         """
#         Enhance topics with a single strategic LLM call
#         """
#         if not self.llm_client or not topic_organization:
#             return self._enhance_topics_without_llm(topic_organization, pipeline_data)
            
#         topics_summary = []
#         for topic_name, topic_data in topic_organization.items():
#             topics_summary.append({
#                 'name': topic_name,
#                 'concepts': topic_data['concepts'][:5],
#                 'source_count': topic_data['source_count'],
#                 'sample_content': topic_data['captures'][0].get('content', '')[:200] if topic_data['captures'] else ''
#             })

#         prompt = f"""Enhance these research topics with rich learning context:

# TOPICS: {json.dumps(topics_summary, indent=2)}

# USER CONTEXT:
# - Session Theme: {pipeline_data['extracted_concepts'].get('session_theme', 'general')}
# - Knowledge Level: {self._assess_session_knowledge_level(pipeline_data)}

# For each topic, provide enhanced_description, learning_outcomes, learning_sequence, key_insights, and practical_applications.

# Return JSON format: {{"topic_name": {{"enhanced_description": "...", "learning_outcomes": [...], ...}}}}"""

#         try:
#             messages = [
#                 {"role": "system", "content": "You are an expert learning designer. Return only valid JSON."},
#                 {"role": "user", "content": prompt}
#             ]
            
#             request_params = self.llm_client.set_provider_specific_defaults(temperature=0.4, max_tokens=1500)
#             response_text = self.llm_client.chat_completion(messages, **request_params)
#             llm_enhancements = json.loads(response_text)
            
#             for topic_name, topic_data in topic_organization.items():
#                 if topic_name in llm_enhancements:
#                     topic_data.update(llm_enhancements[topic_name])
            
#             return topic_organization
            
#         except Exception as e:
#             self.logger.warning(f"LLM enhancement failed: {str(e)}")
#             return self._enhance_topics_without_llm(topic_organization, pipeline_data)


#     def _enhance_topics_without_llm(self, topic_organization: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Enhance topics using rule-based methods"""
#         for topic_name, topic_data in topic_organization.items():
#             topic_data.update({
#                 'enhanced_description': f"Comprehensive exploration of {topic_name.lower()} concepts and applications",
#                 'learning_outcomes': [
#                     f"Understand core {topic_name.lower()} principles",
#                     f"Apply {topic_name.lower()} concepts practically",
#                     f"Connect {topic_name.lower()} to related fields"
#                 ],
#                 'learning_sequence': [
#                     "Review foundational concepts",
#                     "Explore practical applications", 
#                     "Synthesize with existing knowledge"
#                 ],
#                 'key_insights': [f"Key insight about {concept}" for concept in topic_data['concepts'][:3]],
#                 'memory_aids': [f"Remember {topic_name.lower()} through practical examples"],
#                 'pedagogical_approach': 'progressive_discovery'
#             })
        
#         return topic_organization


#     def _intelligent_topic_clustering(self, captures: List[Dict], learning_concepts: List[str]) -> Dict[str, Any]:
#         """
#         Phase 1: Intelligent Topic Clustering & Organization
#         Enhanced semantic clustering using LLM analysis
#         """
#         if not self.llm_client or not self.llm_client.is_available():
#             return self._fallback_rule_based_clustering(captures, learning_concepts)
        
#         try:
#             # Prepare content for analysis
#             content_summary = self._prepare_content_for_clustering(captures, learning_concepts)
            
#             clustering_prompt = f"""
#             Analyze this learning session and identify 3-7 distinct, coherent research topics:
            
#             LEARNING CONCEPTS: {', '.join(learning_concepts[:15])}
            
#             CONTENT SOURCES: 
#             {content_summary}
            
#             For each topic, provide:
#             {{
#                 "topic_name": "Clear, descriptive name",
#                 "scope": "What this topic encompasses", 
#                 "complexity_level": "beginner|intermediate|advanced|expert",
#                 "learning_objectives": ["specific objective 1", "objective 2", "objective 3"],
#                 "prerequisite_topics": ["prerequisite 1", "prerequisite 2"],
#                 "related_concepts": ["concept from the list above"],
#                 "confidence": 0.0-1.0
#             }}
            
#             Group concepts and sources logically. Ensure topics are:
#             - Semantically coherent (concepts naturally belong together)
#             - Appropriately scoped (not too broad or narrow)
#             - Build logical learning progression
            
#             Return JSON: {{"topics": [topic_objects]}}
#             """
            
#             messages = [
#                 {"role": "system", "content": "You are an expert learning architect who creates coherent topic clusters for optimal learning."},
#                 {"role": "user", "content": clustering_prompt}
#             ]
            
#             request_params = self.llm_client.set_provider_specific_defaults(
#                 temperature=0.3,
#                 max_tokens=2000
#             )
            
#             response_text = self.llm_client.chat_completion(messages, **request_params)
#             clustering_result = json.loads(response_text)
            
#             # Process and assign captures to topics
#             return self._assign_captures_to_topics(
#                 clustering_result['topics'], 
#                 captures, 
#                 learning_concepts
#             )
            
#         except Exception as e:
#             self.logger.warning(f"Intelligent clustering failed: {str(e)}, falling back to rule-based")
#             return self._fallback_rule_based_clustering(captures, learning_concepts)


#     def _generate_rich_topic_content(self, topic_data: Dict, user_context: Dict) -> Dict[str, Any]:
#         """Generate memory-focused content that helps users recollect their learning journey"""
    
#         if not self.llm_client or not self.llm_client.is_available():
#             return self._generate_memory_focused_content_basic(topic_data, user_context)
    
#         try:
#             topic_name = topic_data['topic_name']
#             concepts = topic_data['concepts'][:8]
#             captures = topic_data.get('captures', [])
        
#         # Single strategic LLM call for memory-focused content
#             memory_prompt = f"""Create memory-focused learning content for: {topic_name}

# LEARNING CONTEXT:
# - Concepts encountered: {', '.join(concepts)}
# - User level: {user_context.get('knowledge_level', 'intermediate')}
# - Session theme: {user_context.get('session_theme', 'exploration')}
# - Sources: {len(captures)} articles/resources

# Generate content that helps users REMEMBER and RECOLLECT their learning:

# 1. LEARNING STORY (2-3 sentences):
#    - What intellectual journey did they take?
#    - What sparked curiosity about {topic_name}?
   
# 2. CONCEPT MEMORY CARDS (for each concept):
#    - One-line essence: "X is like Y because Z"
#    - Why it matters personally
#    - Quick memory trigger

# 3. CURIOSITY QUESTIONS (3-4 questions):
#    - What would naturally arise in a curious mind?
#    - Point toward deeper exploration
   
# 4. PERSONAL RELEVANCE:
#    - Why does {topic_name} matter for their goals?
#    - How to apply this knowledge practically?

# Return JSON with learning_story, concept_cards, curiosity_questions, personal_relevance."""

#             messages = [
#                 {"role": "system", "content": "Create memorable, personal learning content that helps users recollect their intellectual journey."},
#                 {"role": "user", "content": memory_prompt}
#             ]
        
#             request_params = self.llm_client.set_provider_specific_defaults(temperature=0.4, max_tokens=1800)
#             response_text = self.llm_client.chat_completion(messages, **request_params)
#             memory_content = json.loads(response_text)
        
#             # Enhance with visual elements
#             return self._add_memory_aids(memory_content, topic_data)
        
#         except Exception as e:
#             self.logger.warning(f"Memory-focused content generation failed: {str(e)}")
#         return self._generate_memory_focused_content_basic(topic_data, user_context)

    
#     def _generate_memory_focused_content_basic(self, topic_data: Dict, user_context: Dict) -> Dict[str, Any]:
#         """Basic memory-focused content when LLM unavailable"""
#         topic_name = str(topic_data.get('topic_name', 'Topic'))
#         concepts = topic_data.get('concepts', [])
        
#         # Ensure concepts are strings
#         clean_concepts = []
#         for concept in concepts:
#             if isinstance(concept, str):
#                 clean_concepts.append(concept.strip())
#             else:
#                 clean_concepts.append(str(concept).strip())
        
#         # Remove empty concepts
#         clean_concepts = [c for c in clean_concepts if c]
        
#         concept_cards = []
#         for concept in clean_concepts[:5]:
#             concept_cards.append({
#                 'concept': concept,
#                 'essence': f"{concept} is a fundamental building block in {topic_name.lower()}",
#                 'memory_trigger': f"Think of {concept} when you see {topic_name.lower()} applications",
#                 'personal_relevance': f"Useful for understanding {topic_name.lower()} systems"
#             })
        
#         curiosity_questions = []
#         for concept in clean_concepts[:3]:
#             curiosity_questions.append(f"How does {concept} work in practice?")
        
#         if not curiosity_questions:
#             curiosity_questions = [f"What problems does {topic_name.lower()} solve?"]
        
#         return {
#             'learning_story': f"You dove into {topic_name.lower()} to understand {clean_concepts[0] if clean_concepts else 'key concepts'}. This builds on your {user_context.get('session_theme', 'general')} learning journey.",
#             'concept_cards': concept_cards,
#             'curiosity_questions': curiosity_questions,
#             'personal_relevance': f"Understanding {topic_name.lower()} helps you build expertise in this domain"
#         }


#     def _add_memory_aids(self, memory_content: Dict, topic_data: Dict) -> Dict[str, Any]:
#         """Add visual and structural memory aids"""
#         topic_emoji, color_theme = self._get_topic_visual_theme(topic_data['topic_name'])
        
#         # Safely get concept cards
#         concept_cards = memory_content.get('concept_cards', [])
        
#         # Ensure concept cards are properly formatted
#         formatted_concept_cards = []
#         for card in concept_cards:
#             if isinstance(card, dict):
#                 formatted_concept_cards.append({
#                     'concept': str(card.get('concept', 'Unknown')),
#                     'essence': str(card.get('essence', 'Key concept')),
#                     'memory_trigger': str(card.get('memory_trigger', 'Important concept'))
#                 })
#             elif isinstance(card, str):
#                 formatted_concept_cards.append({
#                     'concept': str(card),
#                     'essence': 'Key concept in this topic',
#                     'memory_trigger': f'Remember when studying {topic_data["topic_name"]}'
#                 })
        
#         memory_content.update({
#             'visual_theme': {
#                 'emoji': str(topic_emoji),
#                 'color': str(color_theme),
#                 'memory_anchor': f"{topic_emoji} {topic_data['topic_name']}"
#             },
#             'quick_scan_takeaways': self._extract_scannable_insights(topic_data),
#             'spaced_review_schedule': {
#                 'review_in_1_day': formatted_concept_cards[:2],
#                 'review_in_3_days': formatted_concept_cards[2:4],
#                 'review_in_1_week': formatted_concept_cards[4:6]
#             },
#             'concept_cards': formatted_concept_cards  # Update with properly formatted cards
#         })
        
#         return memory_content


#     def _extract_scannable_insights(self, topic_data: Dict) -> List[str]:
#         """Extract 3-5 bullet points for 10-second scanning"""
#         concepts = topic_data.get('concepts', [])
#         captures = topic_data.get('captures', [])
    
#         insights = []
#         if concepts:
#             insights.append(f"🧠 Mastered {len(concepts)} core concepts in {topic_data['topic_name']}")
#         if captures:
#             insights.append(f"📚 Explored {len(captures)} quality sources")
    
#         # Add concept-specific insights
#         for concept in concepts[:3]:
#             insights.append(f"💡 Understood how {concept} works")
    
#         return insights[:5]


#     def _create_master_session_synthesis(self, all_topics: Dict, synthesis_insights: Dict, pipeline_data: Dict) -> Dict[str, Any]:
#         """
#         Phase 4: Cross-Topic Synthesis & Master Page
#         Creates comprehensive master session page with novel insights
#         """
#         if not self.llm_client or not self.llm_client.is_available():
#             return self._create_basic_master_synthesis(all_topics, pipeline_data)
        
#         try:
#             # Prepare synthesis data
#             topic_summary = {name: {
#                 'concepts': data['concepts'][:5],
#                 'complexity': data.get('complexity', 'intermediate'),
#                 'connections': data.get('cross_topic_connections', [])
#             } for name, data in all_topics.items()}
            
#             synthesis_prompt = f"""
#             Synthesize this multi-topic learning session into strategic insights:
            
#             TOPICS COVERED: {json.dumps(topic_summary, indent=2)}
            
#             KNOWLEDGE CONNECTIONS: {pipeline_data.get('historical_connections', {}).get('total_connections_found', 0)}
#             KNOWLEDGE GAPS: {len(pipeline_data.get('knowledge_gaps', []))}
            
#             Generate comprehensive synthesis:
            
#             1. SESSION OVERVIEW:
#             - Unifying theme across all topics
#             - Learning journey narrative
#             - Key insights discovered
            
#             2. TOPIC RELATIONSHIP MAP:
#             - How topics build upon each other
#             - Prerequisites and dependencies
#             - Synergistic combinations
            
#             3. STRATEGIC NEXT STEPS:
#             - High-impact learning priorities
#             - Knowledge gap filling strategy
#             - Advanced exploration paths
            
#             4. KNOWLEDGE INTEGRATION:
#             - How to apply learnings together
#             - Cross-domain applications
#             - Real-world project ideas
            
#             Return rich JSON with actionable insights and beautiful narrative structure.
#             """
            
#             messages = [
#                 {"role": "system", "content": "You are an expert learning synthesizer who creates coherent learning narratives and strategic insights."},
#                 {"role": "user", "content": synthesis_prompt}
#             ]
            
#             request_params = self.llm_client.set_provider_specific_defaults(
#                 temperature=0.4,
#                 max_tokens=2500
#             )
            
#             response_text = self.llm_client.chat_completion(messages, **request_params)
#             synthesis_result = json.loads(response_text)
            
#             return synthesis_result
            
#         except Exception as e:
#             self.logger.warning(f"Master synthesis failed: {str(e)}")
#             return self._create_basic_master_synthesis(all_topics, pipeline_data)


#     def _identify_topics_from_content(self, raw_captures: List[Dict], learning_concepts: List[str]) -> Dict[str, Any]:
#         """
#         Identify topics using rule-based analysis of content and concepts
#         """
#         topic_scores = defaultdict(lambda: {'captures': [], 'concepts': [], 'score': 0})
        
#         # Analyze each capture for topic indicators
#         for capture in raw_captures:
#             content = (capture.get('content', '') + ' ' + capture.get('title', '')).lower()
            
#             for topic, indicators in self.topic_indicators.items():
#                 score = sum(1 for indicator in indicators if indicator in content)
#                 if score > 0:
#                     topic_scores[topic]['captures'].append(capture)
#                     topic_scores[topic]['score'] += score
        
#         # Analyze concepts for topic alignment
#         all_concepts_text = ' '.join(learning_concepts).lower()
#         for topic, indicators in self.topic_indicators.items():
#             concept_score = sum(1 for indicator in indicators if indicator in all_concepts_text)
#             if concept_score > 0:
#                 topic_scores[topic]['concepts'].extend([c for c in learning_concepts if any(ind in c.lower() for ind in indicators)])
#                 topic_scores[topic]['score'] += concept_score * 2  # Weight concepts higher
        
#         # Filter and clean topics
#         filtered_topics = {}
#         for topic, data in topic_scores.items():
#             if data['score'] >= 2:  # Minimum threshold
#                 filtered_topics[topic.replace('_', ' ').title()] = {
#                     'topic_name': topic.replace('_', ' ').title(),
#                     'scope': f"Study of {topic.replace('_', ' ').lower()}",
#                     'captures': data['captures'],
#                     'concepts': list(set(data['concepts'])),
#                     'confidence': min(data['score'] / 10.0, 1.0),
#                     'source_count': len(data['captures']),
#                     'practical_applications': self._extract_practical_applications(data['captures'])
#                 }
        
#         # If no clear topics found, create a general topic
#         if not filtered_topics:
#             filtered_topics['General Learning'] = {
#                 'topic_name': 'General Learning',
#                 'scope': 'General knowledge exploration',
#                 'captures': raw_captures,
#                 'concepts': learning_concepts,
#                 'confidence': 0.5,
#                 'source_count': len(raw_captures),
#                 'practical_applications': self._extract_practical_applications(raw_captures)
#             }
        
#         return filtered_topics


#     def _add_rich_topic_content(self, page_id: str, topic_name: str, topic_data: Dict[str, Any], 
#                                pipeline_data: Dict[str, Any], color_theme: str):
#         """Add memory-focused content to topic page"""
    
#         rich_content = topic_data.get('rich_content', {})
        
#         blocks = []
        
#         # Hero section with learning story
#         blocks.extend(self._create_topic_hero_with_story(topic_name, topic_data, rich_content, color_theme))
        
#         # Visual concept cards for memory
#         blocks.extend(self._create_visual_concept_cards_section(rich_content, topic_data))
        
#         # Personal relevance section
#         blocks.extend(self._create_personal_relevance_section(rich_content, topic_name))
        
#         # Quick scan insights
#         blocks.extend(self._create_topic_quick_scan(rich_content, topic_data))
        
#         # Curiosity questions
#         blocks.extend(self._create_topic_curiosity_questions(rich_content, topic_name))
        
#         # Sources with context
#         blocks.extend(self._create_contextual_sources_section(topic_data))
        
#         # Spaced repetition schedule
#         blocks.extend(self._create_spaced_review_section(rich_content))
        
#         try:
#             # Add content in batches
#             batch_size = 100
#             for i in range(0, len(blocks), batch_size):
#                 batch_blocks = blocks[i:i + batch_size]
#                 requests.patch(
#                     f"{self.notion_api_url}/blocks/{page_id}/children",
#                     headers=self.headers,
#                     json={"children": batch_blocks}
#                 )
            
#             self.logger.info(f"Memory-focused topic content added: {topic_name}")
#         except Exception as e:
#             self.logger.warning(f"Failed to add topic content '{topic_name}': {str(e)}")


#     def _create_topic_hero_with_story(self, topic_name: str, topic_data: Dict, rich_content: Dict, color_theme: str) -> List[Dict]:
#         """Create topic hero section with learning story"""
#         blocks = []
        
#         topic_emoji, _ = self._get_topic_visual_theme(topic_name)
#         learning_story = rich_content.get('learning_story', f'Your exploration of {topic_name.lower()} concepts and applications.')
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_1",
#             "heading_1": {
#                 "rich_text": [{"type": "text", "text": {"content": f"{topic_emoji} {topic_name}"}}],
#                 "color": "blue"
#             }
#         })
        
#         blocks.append({
#             "object": "block",
#             "type": "callout",
#             "callout": {
#                 "rich_text": [{"type": "text", "text": {"content": learning_story}}],
#                 "icon": {"emoji": "✨"},
#                 "color": f"{color_theme}_background"
#             }
#         })
        
#         return blocks


#     def _create_visual_concept_cards_section(self, rich_content: Dict, topic_data: Dict) -> List[Dict]:
#         """Create visual concept cards for memory"""
#         blocks = []
        
#         concept_cards = rich_content.get('concept_cards', [])
#         if not concept_cards:
#             return blocks
        
#         blocks.append({
#             "object": "block", 
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "🎴 Concept Memory Cards"}}]
#             }
#         })
        
#         for card in concept_cards[:6]:
#             # Safely extract concept information
#             if isinstance(card, dict):
#                 concept = str(card.get('concept', 'Unknown')).strip()
#                 essence = str(card.get('essence', 'Key concept in this topic')).strip()
#                 memory_trigger = str(card.get('memory_trigger', f'Remember when thinking about {concept}')).strip()
#             else:
#                 # Handle case where card is not a dict
#                 concept = str(card).strip()
#                 essence = 'Key concept in this topic'
#                 memory_trigger = f'Remember when thinking about {concept}'
            
#             # Only create card if we have a valid concept name
#             if concept and concept != 'Unknown':
#                 blocks.append({
#                     "object": "block",
#                     "type": "callout",
#                     "callout": {
#                         "rich_text": [
#                             {"type": "text", "text": {"content": f"💡 {concept}\n"}, "annotations": {"bold": True}},
#                             {"type": "text", "text": {"content": f"{essence}\n\n"}},
#                             {"type": "text", "text": {"content": f"🧠 Memory trigger: {memory_trigger}"}, "annotations": {"italic": True}}
#                         ],
#                         "icon": {"emoji": "💡"},
#                         "color": "yellow_background"
#                     }
#                 })
        
#         return blocks


#     def _create_personal_relevance_section(self, rich_content: Dict, topic_name: str) -> List[Dict]:
#         """Create personal relevance section"""
#         blocks = []
        
#         personal_relevance = rich_content.get('personal_relevance', f'Understanding {topic_name.lower()} builds your expertise in this domain.')
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "🎯 Why This Matters to You"}}]
#             }
#         })
        
#         blocks.append({
#             "object": "block",
#             "type": "callout",
#             "callout": {
#                 "rich_text": [{"type": "text", "text": {"content": personal_relevance}}],
#                 "icon": {"emoji": "🎯"},
#                 "color": "green_background"
#             }
#         })
        
#         return blocks


#     def _create_topic_quick_scan(self, rich_content: Dict, topic_data: Dict) -> List[Dict]:
#         """Create quick scan section for topic"""
#         blocks = []
        
#         quick_scan = rich_content.get('quick_scan_takeaways', [])
#         if not quick_scan:
#             # Generate from topic data
#             concepts = topic_data.get('concepts', [])
#             quick_scan = [
#                 f"💡 Learned {len(concepts)} key concepts",
#                 f"📚 From {len(topic_data.get('captures', []))} sources",
#                 f"🎯 Focus: {concepts[0] if concepts else 'Core principles'}"
#             ]
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_3",
#             "heading_3": {
#                 "rich_text": [{"type": "text", "text": {"content": "⚡ Quick Scan"}}]
#             }
#         })
        
#         for insight in quick_scan[:4]:
#             blocks.append({
#                 "object": "block",
#                 "type": "bulleted_list_item",
#                 "bulleted_list_item": {
#                     "rich_text": [{"type": "text", "text": {"content": insight}}]
#                 }
#             })
        
#         return blocks


#     def _create_topic_curiosity_questions(self, rich_content: Dict, topic_name: str) -> List[Dict]:
#         """Create curiosity questions section for topic"""
#         blocks = []
        
#         curiosity_questions = rich_content.get('curiosity_questions', [
#             f"How does {topic_name.lower()} apply in different industries?",
#             f"What are the cutting-edge developments in {topic_name.lower()}?",
#             f"What challenges remain unsolved in {topic_name.lower()}?"
#         ])
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "🤔 Questions to Explore Further"}}]
#             }
#         })
        
#         # Ensure questions are strings
#         for question in curiosity_questions[:4]:
#             question_text = str(question).strip() if question else f"What can I learn more about {topic_name.lower()}?"
            
#             if question_text:  # Only add non-empty questions
#                 blocks.append({
#                     "object": "block",
#                     "type": "callout",
#                     "callout": {
#                         "rich_text": [{"type": "text", "text": {"content": question_text}}],
#                         "icon": {"emoji": "🤔"},
#                         "color": "purple_background"
#                     }
#                 })
        
#         return blocks


#     def _create_spaced_review_section(self, rich_content: Dict) -> List[Dict]:
#         """Create spaced repetition review schedule"""
#         blocks = []
        
#         review_schedule = rich_content.get('spaced_review_schedule', {})
#         if not review_schedule:
#             return blocks
        
#         blocks.append({
#             "object": "block",
#             "type": "heading_2",
#             "heading_2": {
#                 "rich_text": [{"type": "text", "text": {"content": "📅 Spaced Review Schedule"}}]
#             }
#         })
        
#         review_items = [
#             ("1 day", review_schedule.get('review_in_1_day', [])),
#             ("3 days", review_schedule.get('review_in_3_days', [])),
#             ("1 week", review_schedule.get('review_in_1_week', []))
#         ]
        
#         for timing, concepts in review_items:
#             if concepts:
#                 # Convert concepts to strings properly - handle both dict and string formats
#                 concept_list = []
#                 for c in concepts[:3]:  # Limit to 3 concepts
#                     if isinstance(c, dict):
#                         # If it's a dict, get the 'concept' key or convert to string
#                         concept_name = c.get('concept', str(c))
#                     elif isinstance(c, str):
#                         concept_name = c
#                     else:
#                         concept_name = str(c)
                    
#                     # Clean the concept name and ensure it's a string
#                     clean_concept = str(concept_name).strip()
#                     if clean_concept:  # Only add non-empty concepts
#                         concept_list.append(clean_concept)
                
#                 # Only create the block if we have valid concepts
#                 if concept_list:
#                     concept_text = ', '.join(concept_list)
#                     blocks.append({
#                         "object": "block",
#                         "type": "to_do",
#                         "to_do": {
#                             "rich_text": [{"type": "text", "text": {"content": f"📚 Review in {timing}: {concept_text}"}}],
#                             "checked": False
#                         }
#                     })
        
#         return blocks


#     # Helper methods for database and utility functions
#     def _get_or_create_database(self, db_type: str) -> str:
#         """Get existing database or create new one"""
#         # Search for existing database
#         existing_db = self._search_database_by_title(self.database_schemas[db_type]['title'])
#         if existing_db:
#             return existing_db
        
#         # Create new database
#         return self._create_database(db_type)


#     def _search_database_by_title(self, title: str) -> Optional[str]:
#         """Search for existing database by title"""
#         try:
#             response = requests.post(
#                 f"{self.notion_api_url}/search",
#                 headers=self.headers,
#                 json={
#                     "query": title,
#                     "filter": {"property": "object", "value": "database"}
#                 }
#             )
#             response.raise_for_status()
            
#             results = response.json().get('results', [])
#             for result in results:
#                 if result.get('title', [{}])[0].get('plain_text') == title:
#                     return result['id']
            
#         except Exception as e:
#             self.logger.warning(f"Database search failed: {str(e)}")
        
#         return None


#     def _create_database(self, db_type: str) -> str:
#         """Create new Notion database"""
#         schema = self.database_schemas[db_type]
        
#         # Get parent page ID
#         parent_page_id = os.getenv('NOTION_PARENT_PAGE_ID')
#         if not parent_page_id:
#             parent = {"type": "workspace"}
#         else:
#             parent = {"type": "page_id", "page_id": parent_page_id}
        
#         database_data = {
#             "parent": parent,
#             "title": [{"type": "text", "text": {"content": schema['title']}}],
#             "properties": schema['properties']
#         }

#         try:
#             response = requests.post(f"{self.notion_api_url}/databases", headers=self.headers, json=database_data)
#             response.raise_for_status()
#             database_id = response.json()['id']
#             self.logger.info(f"Created database '{db_type}': {database_id}")
#             return database_id
#         except Exception as e:
#             self.logger.error(f"Database creation failed for {db_type}: {e}")
#             self.logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
#             raise


#     def _ensure_enhanced_databases_exist(self) -> Dict[str, str]:
#         """Ensure all enhanced databases exist"""
#         import time

#         databases = {}
        
#         for db_type in ['learning_sessions', 'research_topics', 'concept_library']:
#             if db_type in self.database_schemas:
#                 db_id = self._get_or_create_database(db_type)
#                 databases[db_type] = db_id
#                 self.logger.info(f"Enhanced database '{db_type}' ready: {db_id}")

#                 time.sleep(1)
        
#         # Set up database relationships
#         self._setup_enhanced_database_relationships(databases)
#         return databases


#     def _setup_enhanced_database_relationships(self, databases: Dict[str, str]):
#         """Set up relationships between enhanced databases"""
#         try:
#             # Add relations to concept library
#             if 'concept_library' in databases:
#                 requests.patch(
#                     f"{self.notion_api_url}/databases/{databases['concept_library']}",
#                     headers=self.headers,
#                     json={
#                         "properties": {
#                             "Related Concepts": {
#                                 "relation": {
#                                     "database_id": databases['concept_library'],
#                                     "single_property": {}
#                                 }
#                             },
#                             "From Topics": {
#                                 "relation": {
#                                     "database_id": databases['research_topics'],
#                                     "single_property": {}
#                                 }
#                             }
#                         }
#                     }
#                 )
            
#             self.logger.info("Enhanced database relationships configured")
            
#         except Exception as e:
#             self.logger.warning(f"Failed to set up database relationships: {str(e)}")


#     def _test_notion_connection(self):
#         """Test Notion API connection"""
#         response = requests.get(
#             f"{self.notion_api_url}/users/me",
#             headers=self.headers
#         )
#         response.raise_for_status()


#     # Helper methods for visual themes and classifications
#     def _get_topic_visual_theme(self, topic_name: str) -> tuple:
#         """Get emoji and color theme for topic"""
#         topic_lower = topic_name.lower()
    
#         theme_map = {
#             'machine learning': ('🤖', 'blue'),
#             'artificial intelligence': ('🧠', 'purple'),
#             'data science': ('📊', 'green'),
#             'software engineering': ('💻', 'gray'),
#             'business strategy': ('📈', 'red'),
#             'psychology': ('🧭', 'orange'),
#             'research methods': ('🔬', 'brown'),
#             'technology': ('⚡', 'yellow'),
#             'react': ('⚛️', 'blue'),
#             'javascript': ('🟨', 'yellow'),
#             'programming': ('💻', 'blue'),
#             'web development': ('🌐', 'green'),
#             'frontend': ('🎨', 'purple'),
#             'hooks': ('⚛️', 'blue'),
#             'state management': ('🔄', 'orange'),
#             'performance': ('⚡', 'yellow'),
#             'optimization': ('🚀', 'red')
#         }
        
#         for key, (emoji, color) in theme_map.items():
#             if key in topic_lower:
#                 # Ensure emoji is properly encoded
#                 clean_emoji = str(emoji).encode('utf-8').decode('utf-8')
#                 return clean_emoji, color
        
#         return '📚', 'blue'  # Default


#     def _serialize_for_notion(self, obj):
#         """Serialize object for Notion API with proper Unicode handling"""
#         if isinstance(obj, dict):
#             return {k: self._serialize_for_notion(v) for k, v in obj.items()}
#         elif isinstance(obj, list):
#             return [self._serialize_for_notion(item) for item in obj]
#         elif isinstance(obj, str):
#             # Ensure proper UTF-8 encoding for strings
#             return obj.encode('utf-8').decode('utf-8')
#         elif obj is None:
#             return None
#         else:
#             return str(obj)


#     def _classify_domain(self, topic_name: str) -> str:
#         """Classify topic into domain"""
#         topic_lower = topic_name.lower()
        
#         if any(term in topic_lower for term in ['machine learning', 'ai', 'artificial intelligence']):
#             return 'Artificial Intelligence'
#         elif any(term in topic_lower for term in ['data', 'statistics', 'analysis']):
#             return 'Data Science'
#         elif any(term in topic_lower for term in ['business', 'strategy', 'management']):
#             return 'Business'
#         elif any(term in topic_lower for term in ['psychology', 'cognitive', 'behavior']):
#             return 'Psychology'
#         elif any(term in topic_lower for term in ['software', 'programming', 'engineering']):
#             return 'Technology'
#         else:
#             return 'General'


#     def _assess_session_knowledge_level(self, pipeline_data: Dict[str, Any]) -> str:
#         """Assess overall session knowledge level"""
#         complexity = pipeline_data['extracted_concepts'].get('complexity_assessment', {}).get('overall_level', 'intermediate')
#         concepts_count = len(pipeline_data['extracted_concepts'].get('learning_concepts', []))
        
#         if complexity == 'advanced' or concepts_count > 10:
#             return 'Advanced'
#         elif complexity == 'basic' and concepts_count < 5:
#             return 'Beginner'
#         else:
#             return 'Intermediate'


#     def _assess_topic_complexity(self, captures: List[Dict], concepts: List[str]) -> str:
#         """Assess complexity of a specific topic"""
#         if len(concepts) > 8:
#             return 'Advanced'
#         elif len(concepts) > 4:
#             return 'Intermediate'
#         else:
#             return 'Foundational'


#     def _extract_learning_objectives(self, captures: List[Dict], concepts: List[str]) -> List[str]:
#         """Extract learning objectives from captures and concepts"""
#         objectives = []
        
#         # Generate objectives based on concepts
#         if concepts:
#             objectives.append(f"Understand {len(concepts)} core concepts")
#             objectives.append(f"Apply {concepts[0] if concepts else 'key principles'} in practice")
#             objectives.append("Connect new knowledge to existing understanding")
        
#         return objectives


#     def _extract_practical_applications(self, captures: List[Dict]) -> List[str]:
#         """Extract practical applications from capture content"""
#         applications = []
        
#         for capture in captures:
#             content = capture.get('content', '').lower()
            
#             # Look for application indicators
#             if 'example' in content or 'application' in content:
#                 applications.append(f"Practical example from {capture.get('title', 'source')}")
#             elif 'use case' in content:
#                 applications.append(f"Use case identified in {capture.get('title', 'source')}")
#             elif 'implement' in content or 'practice' in content:
#                 applications.append(f"Implementation guidance from {capture.get('title', 'source')}")
        
#         # Add generic applications if none found
#         if not applications:
#             applications = [
#                 "Apply concepts to real-world scenarios",
#                 "Practice through hands-on exercises",
#                 "Teach concepts to others"
#             ]
        
#         return applications[:5]  # Limit to 5


#     def _gap_relates_to_topic(self, gap: Dict[str, Any], topic_name: str) -> bool:
#         """Check if a knowledge gap relates to a specific topic"""
#         gap_concept = gap.get('missing_concept', '').lower()
#         topic_keywords = topic_name.lower().split()
        
#         return any(keyword in gap_concept for keyword in topic_keywords)