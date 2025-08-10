"""
Notion Note Generation Node: Creates rich, structured notes in Notion from pipeline analysis
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict
import requests
from urllib.parse import quote

from dotenv import load_dotenv
load_dotenv()

from pocketflow import Node as BaseNode
from .llm_client import get_llm_client

class NotionNoteGenerationNode(BaseNode):
    """    
    Enhanced Notion Note Generation with:
    - Topic-based page organization
    - Rich content generation using existing pipeline data
    - Minimal additional LLM calls (1-2 total)
    - Beautiful Notion formatting
    - Cross-topic relationship mapping
    
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

        # LLM for minimal enhancement
        self.llm_client = None
        self._initialize_llm()
        
        # Enhanced database schemas for topic organization
        self.database_schemas = self._init_enhanced_database_schemas()

        # Rich formatting templates
        self.formatting_templates = self._init_formatting_templates()

        # Topic clustering strategies (rule-based to avoid LLM calls)
        self.topic_indicators = {
            'machine_learning': ['machine learning', 'ml', 'neural network', 'deep learning', 'algorithm', 'model training'],
            'artificial_intelligence': ['artificial intelligence', 'ai', 'cognitive', 'intelligent systems'],
            'data_science': ['data science', 'statistics', 'data analysis', 'visualization', 'big data'],
            'software_engineering': ['programming', 'software', 'development', 'coding', 'engineering'],
            'business_strategy': ['business', 'strategy', 'management', 'entrepreneurship', 'leadership'],
            'psychology': ['psychology', 'cognitive', 'behavior', 'mental', 'psychological'],
            'research_methods': ['research', 'methodology', 'experiment', 'study', 'analysis'],
            'technology': ['technology', 'tech', 'innovation', 'digital', 'computing']
        }
        
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

    def _initialize_llm(self):
        """Initialize LLM for minimal enhancement calls"""
        try:
            self.llm_client = get_llm_client()
            self.logger.info(f"LLM initialized for enhanced Notion generation: {self.llm_client.get_provider_name()}")
        except Exception as e:
            self.logger.warning(f"LLM not available for enhanced features: {str(e)}")
            self.llm_client = None

    def _init_enhanced_database_schemas(self) -> Dict[str, Any]:
        """Enhanced database schemas for topic-based organization"""
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
                    'Applications': {'multi_select': {'options': []}},
                    'Related Concepts': {'relation': {'database_id': ''}}
                }
            }
        }

    def _init_formatting_templates(self) -> Dict[str, Any]:
        """Initialize rich Notion formatting templates"""
        return {
            'topic_page_structure': {
                'header_with_emoji': True,
                'overview_callout': True,
                'progress_tracking': True,
                'concept_toggles': True,
                'application_examples': True,
                'cross_references': True,
                'next_steps_checklist': True
            },
            'content_blocks': {
                'overview_callout': {
                    'type': 'callout',
                    'icon': '🎯',
                    'color': 'blue_background'
                },
                'key_insight': {
                    'type': 'callout',
                    'icon': '💡',
                    'color': 'yellow_background'
                },
                'important_note': {
                    'type': 'callout',
                    'icon': '⚠️',
                    'color': 'orange_background'
                },
                'success_tip': {
                    'type': 'callout',
                    'icon': '✅',
                    'color': 'green_background'
                },
                'research_question': {
                    'type': 'callout',
                    'icon': '🤔',
                    'color': 'purple_background'
                }
            }
        }

    def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare for Notion note generation
        """
        self.logger.info("Starting Notion Note Generation prep phase")
        
        # Validate inputs from previous nodes
        pipeline_data = {
            'session_id': shared_state.get('session_id'),
            'raw_captures': shared_state.get('raw_captures', []),
            'extracted_concepts': shared_state.get('extracted_concepts', {}),
            'knowledge_graph': shared_state.get('knowledge_graph', {}),
            'historical_connections': shared_state.get('historical_connections', {}),
            'knowledge_gaps': shared_state.get('knowledge_gaps', []),
            'learning_recommendations': shared_state.get('learning_recommendations', []),
            'batch_metrics': shared_state.get('batch_metrics', {})
        }

        try:
            self._test_notion_connection()
            self.logger.info("Notion API connection successful")
        except Exception as e:
            self.logger.error(f"Notion API connection failed: {str(e)}")
            return {'error': f'Notion API connection failed: {str(e)}'}

        topic_organization = self._intelligent_topic_clustering(
            pipeline_data['raw_captures'],
            pipeline_data['extracted_concepts'].get('learning_concepts', [])
        )

        user_context = {
            'knowledge_level': self._assess_session_knowledge_level(pipeline_data),
            'learning_style': 'progressive',
            'session_theme': pipeline_data['extracted_concepts'].get('session_theme', 'general')
        }

        enhanced_topics = {}
        for topic_name, topic_data in topic_organization.items():
            rich_content = self._generate_rich_topic_content(topic_data, user_context)
            enhanced_topics[topic_name] = {
                **topic_data,
                'rich_content': rich_content
            }
        
        prep_data = {
            'pipeline_data': pipeline_data,
            'topic_organization': enhanced_topics,
            'session_metadata': {
                'session_id': pipeline_data['session_id'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'topics_identified': len(enhanced_topics),
                'total_concepts': len(pipeline_data['extracted_concepts'].get('learning_concepts', [])),
                'knowledge_level': self._assess_session_knowledge_level(pipeline_data),
                'enhancement_level': 'intelligent_clustering_with_rich_content'
            }
        }

        return prep_data

    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution: Create topic organized Notion pages
        """
        if 'error' in prep_result:
            return prep_result
            
        self.logger.info("Starting Notion Note Generation core execution")

        pipeline_data = prep_result['pipeline_data']
        topic_organization = prep_result['topic_organization']
        session_metadata = prep_result['session_metadata']
        
        try:
            # Step 1: Ensure enhanced databases exist
            databases = self._ensure_enhanced_databases_exist()
            
            # Step 2: Create topic pages (one per topic)
            topic_pages = {}
            for topic_name, enhanced_topic_data in topic_organization.items():
                rich_content = enhanced_topic_data.get('rich_content', {})
                
                topic_page = self._create_enhanced_topic_page(
                    topic_name, 
                    enhanced_topic_data, 
                    rich_content,
                    databases['research_topics'], 
                    pipeline_data
                )
                if topic_page:
                    topic_pages[topic_name] = topic_page
            
            # Step 3: Create enhanced concept library entries
            concept_entries = self._create_enhanced_concept_library_entries(
                pipeline_data['extracted_concepts'], 
                databases['concept_library'], 
                topic_organization
            )
            
            # Step 4: Enhanced synthesis
            synthesis_insights = self._create_master_session_synthesis(
                topic_organization, 
                {},
                pipeline_data
            )
            
            # Step 5: Enhanced master page
            master_session_page = self._create_enhanced_master_session_page(
                session_metadata, 
                pipeline_data, 
                topic_pages, 
                synthesis_insights,
                databases['learning_sessions']
            )
            
            # Step 6: Update database relationships
            self._update_enhanced_database_relationships(databases, topic_pages, concept_entries, master_session_page)
            
            return {
                'master_session_page': master_session_page,
                'topic_pages': topic_pages,
                'concept_entries': concept_entries,
                'synthesis_insights': synthesis_insights,
                'databases': databases,
                'creation_summary': {
                    'session_created': bool(master_session_page),
                    'topic_pages_created': len(topic_pages),
                    'concepts_created': len(concept_entries),
                    'sources_created': len(pipeline_data['raw_captures']),
                    'total_pages': 1 + len(topic_pages) + len(concept_entries),
                    'topics_covered': list(topic_organization.keys()),
                    'enhancement_features_used': [
                        'intelligent_topic_clustering',
                        'rich_content_generation', 
                        'cross_topic_synthesis',
                        'interactive_progress_tracking',
                        'memory_aids_integration'
                    ]
                },
                'session_page_url': self._get_page_url(master_session_page),
                'notion_urls': {
                    'master_session': self._get_page_url(master_session_page),
                    'topic_pages': {name: self._get_page_url(page) for name, page in topic_pages.items()},
                    'databases': {
                        'sessions': f"https://notion.so/{databases['learning_sessions'].replace('-', '')}",
                        'topics': f"https://notion.so/{databases['research_topics'].replace('-', '')}",
                        'concepts': f"https://notion.so/{databases['concept_library'].replace('-', '')}"
                    }
                }
            }
        except Exception as e:
            self.logger.error(f"Enhanced Notion generation failed: {str(e)}")
            return {'error': f"Enhanced Notion generation failed: {str(e)}"}

    def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """
        Post-processing: Store enhanced Notion results
        """
        self.logger.info("Notion Note Generation post-execution phase")
        
        if 'error' in exec_result:
            shared_state['notion_generation_error'] = exec_result['error']
            return "error"
        
        # Store Notion results in shared_state
        shared_state['notion_generation'] = {
            'master_session_url': exec_result['notion_urls']['master_session'],
            'topic_pages': exec_result['notion_urls']['topic_pages'],
            'databases': exec_result['databases'],
            'creation_summary': exec_result['creation_summary'],
            'synthesis_insights': exec_result['synthesis_insights'],
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'enhancement_level': 'rich_topic_organized'
        }
        
        # Update pipeline metadata
        shared_state['pipeline_metadata']['notion_generation_complete'] = True
        shared_state['pipeline_metadata']['notion_generation_summary'] = {
            'total_pages_created': exec_result['creation_summary']['total_pages'],
            'master_session_url': exec_result['notion_urls']['master_session'],
            'topic_pages_created': exec_result['creation_summary']['topic_pages_created'],
            'concepts_documented': exec_result['creation_summary']['concepts_created'],
            'topics_covered': exec_result['creation_summary']['topics_covered']
        }
        
        self.logger.info(f"Enhanced Notion generation complete - {exec_result['creation_summary']['total_pages']} pages created")
        return "default"

    # ========== MISSING METHOD IMPLEMENTATIONS ==========

    def _prepare_content_for_clustering(self, captures: List[Dict], concepts: List[str]) -> str:
        """Prepare content summary for LLM clustering analysis"""
        content_summary = []
        
        for i, capture in enumerate(captures[:10]):  # Limit for prompt size
            title = capture.get('title', f'Source {i+1}')
            content_preview = capture.get('content', '')[:200]
            content_summary.append(f"[{title}]: {content_preview}...")
        
        return '\n'.join(content_summary)

    def _assign_captures_to_topics(self, llm_topics: List[Dict], captures: List[Dict], concepts: List[str]) -> Dict[str, Any]:
        """Assign captures and concepts to LLM-identified topics"""
        topic_organization = {}
        
        for topic_info in llm_topics:
            topic_name = topic_info.get('topic_name', 'Unknown Topic')
            related_concepts = topic_info.get('related_concepts', [])
            
            # Find captures that relate to this topic
            topic_captures = []
            topic_concepts = []
            
            # Match captures by content similarity
            topic_keywords = topic_name.lower().split() + [c.lower() for c in related_concepts]
            
            for capture in captures:
                content = (capture.get('content', '') + ' ' + capture.get('title', '')).lower()
                if any(keyword in content for keyword in topic_keywords):
                    topic_captures.append(capture)
            
            # Match concepts
            for concept in concepts:
                if concept.lower() in [c.lower() for c in related_concepts] or \
                   any(keyword in concept.lower() for keyword in topic_keywords):
                    topic_concepts.append(concept)
            
            # Only include topics with content
            if topic_captures or topic_concepts:
                topic_organization[topic_name] = {
                    'topic_name': topic_name,
                    'scope': topic_info.get('scope', f'Study of {topic_name.lower()}'),
                    'complexity': topic_info.get('complexity_level', 'intermediate'),
                    'learning_objectives': topic_info.get('learning_objectives', []),
                    'captures': topic_captures,
                    'concepts': topic_concepts,
                    'confidence': topic_info.get('confidence', 0.7),
                    'source_count': len(topic_captures)
                }
        
        return topic_organization

    def _fallback_rule_based_clustering(self, captures: List[Dict], concepts: List[str]) -> Dict[str, Any]:
        """Fallback rule-based clustering when LLM is unavailable"""
        return self._identify_topics_from_content(captures, concepts)

    def _create_enhanced_topic_page(self, topic_name: str, enhanced_topic_data: Dict[str, Any], 
                                   rich_content: Dict[str, Any], topics_db_id: str, 
                                   pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced topic page with rich content"""
        # Determine topic emoji and color theme
        topic_emoji, color_theme = self._get_topic_visual_theme(topic_name)
        
        # Create database entry for topic
        page_data = {
            "parent": {"database_id": topics_db_id},
            "properties": {
                "Topic Name": {"title": [{"text": {"content": f"{topic_emoji} {topic_name}"}}]},
                "Domain": {"select": {"name": self._classify_domain(topic_name)}},
                "Complexity Level": {"select": {"name": enhanced_topic_data.get('complexity', 'Intermediate')}},
                "Learning Status": {"select": {"name": "Learning"}},
                "First Encountered": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
                "Last Reviewed": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
                "Session Count": {"number": 1},
                "Concepts Count": {"number": len(enhanced_topic_data.get('concepts', []))},
                "Practical Applications": {"number": len(enhanced_topic_data.get('practical_applications', []))},
                "Knowledge Gaps": {"number": len([gap for gap in pipeline_data.get('knowledge_gaps', []) if self._gap_relates_to_topic(gap, topic_name)])},
                "Next Steps": {"rich_text": [{"text": {"content": enhanced_topic_data.get('learning_sequence', ['Continue learning'])[0] if enhanced_topic_data.get('learning_sequence') else 'Continue learning'}}]}
            }
        }
        
        try:
            response = requests.post(
                f"{self.notion_api_url}/pages",
                headers=self.headers,
                json=page_data
            )
            response.raise_for_status()
            
            topic_page = response.json()
            
            # Add rich content to the page
            self._add_rich_topic_content(topic_page['id'], topic_name, enhanced_topic_data, pipeline_data, color_theme)
            
            return topic_page
            
        except Exception as e:
            self.logger.error(f"Failed to create enhanced topic page for '{topic_name}': {str(e)}")
            return {}

    def _create_enhanced_concept_library_entries(self, extracted_concepts: Dict[str, Any], 
                                               concepts_db_id: str, topic_organization: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create enhanced concept library entries"""
        entries = []
        learning_concepts = extracted_concepts.get('learning_concepts', [])
        key_terms = extracted_concepts.get('key_terms', {})
        
        for concept in learning_concepts:
            # Find which topic this concept belongs to
            topic_name = 'General'
            for t_name, t_data in topic_organization.items():
                if concept in t_data.get('concepts', []):
                    topic_name = t_name
                    break
            
            # Get definition quality based on key_terms
            definition_quality = "Clear" if concept in key_terms else "Partial"
            
            entry_data = {
                "parent": {"database_id": concepts_db_id},
                "properties": {
                    "Concept Name": {"title": [{"text": {"content": concept}}]},
                    "Topic": {"select": {"name": topic_name}},
                    "Definition Quality": {"select": {"name": definition_quality}},
                    "Understanding Level": {"select": {"name": "Functional"}},
                    "Confidence Score": {"number": 75 if definition_quality == "Clear" else 60},
                    "First Learned": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
                    "Times Encountered": {"number": 1}
                }
            }
            
            try:
                response = requests.post(f"{self.notion_api_url}/pages", headers=self.headers, json=entry_data)
                if response.status_code == 201:
                    entry = response.json()
                    # Add concept content if available
                    if concept in key_terms:
                        self._add_concept_content(entry['id'], concept, key_terms[concept])
                    entries.append(entry)
            except Exception as e:
                self.logger.warning(f"Failed to create concept entry for {concept}: {str(e)}")
        
        return entries

    def _create_enhanced_master_session_page(self, session_metadata: Dict[str, Any], 
                                           pipeline_data: Dict[str, Any], topic_pages: Dict[str, Any], 
                                           synthesis_insights: Dict[str, Any], sessions_db_id: str) -> Dict[str, Any]:
        """Create enhanced master session page"""
        
        session_theme = pipeline_data['extracted_concepts'].get('session_theme', 'Knowledge Exploration')
        session_title = f"Learning Journey: {session_theme.replace('_', ' ').title()}"
        
        # Create database entry
        page_data = {
            "parent": {"database_id": sessions_db_id},
            "properties": {
                "Session Title": {"title": [{"text": {"content": session_title}}]},
                "Date": {"date": {"start": session_metadata['timestamp']}},
                "Topics Covered": {"multi_select": [{"name": topic} for topic in list(topic_pages.keys())[:10]]},
                "Primary Theme": {"select": {"name": session_theme.replace('_', ' ').title()}},
                "Knowledge Level": {"select": {"name": session_metadata['knowledge_level']}},
                "Topics Count": {"number": len(topic_pages)},
                "Concepts Count": {"number": session_metadata['total_concepts']},
                "Cross-References": {"number": pipeline_data.get('historical_connections', {}).get('total_connections_found', 0)},
                "Completion Status": {"select": {"name": "Completed"}}
            }
        }
        
        try:
            response = requests.post(
                f"{self.notion_api_url}/pages",
                headers=self.headers,
                json=page_data
            )
            response.raise_for_status()
            
            master_page = response.json()
            
            # Add rich content to master page
            self._add_master_session_content(master_page['id'], session_metadata, pipeline_data, topic_pages, synthesis_insights)
            
            return master_page
            
        except Exception as e:
            self.logger.error(f"Failed to create enhanced master session page: {str(e)}")
            return {}

    def _update_enhanced_database_relationships(self, databases: Dict[str, str], 
                                              topic_pages: Dict[str, Any], concept_entries: List[Dict[str, Any]], 
                                              master_session_page: Dict[str, Any]):
        """Update enhanced database relationships"""
        try:
            # Link concept entries to topic pages
            for concept_entry in concept_entries:
                concept_id = concept_entry.get('id')
                if concept_id:
                    # Find related topic page
                    concept_name = concept_entry.get('properties', {}).get('Concept Name', {}).get('title', [{}])[0].get('plain_text', '')
                    for topic_name, topic_page in topic_pages.items():
                        topic_data = next((data for name, data in topic_pages.items() if name == topic_name), {})
                        if concept_name in str(topic_data):
                            # Update concept with topic relation
                            try:
                                requests.patch(
                                    f"{self.notion_api_url}/pages/{concept_id}",
                                    headers=self.headers,
                                    json={
                                        "properties": {
                                            "From Topics": {
                                                "relation": [{"id": topic_page.get('id')}]
                                            }
                                        }
                                    }
                                )
                            except Exception as e:
                                self.logger.warning(f"Failed to link concept to topic: {str(e)}")
            
            self.logger.info("Enhanced database relationships updated")
        except Exception as e:
            self.logger.warning(f"Failed to update enhanced database relationships: {str(e)}")

    def _add_interactive_elements(self, rich_content: Dict[str, Any], topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add interactive elements to rich content"""
        if not rich_content:
            rich_content = {}
        
        # Add interactive progress tracking
        rich_content['interactive_elements'] = {
            'progress_tracker': {
                'milestones': [
                    {'title': 'Understand core concepts', 'completed': False},
                    {'title': 'Practice applications', 'completed': False},
                    {'title': 'Connect to existing knowledge', 'completed': False}
                ]
            },
            'self_assessment': {
                'questions': [
                    f"Can you explain {topic_data.get('topic_name', 'this topic')} in your own words?",
                    f"What real-world applications do you see for {topic_data.get('topic_name', 'this topic')}?",
                    f"How does {topic_data.get('topic_name', 'this topic')} connect to what you already know?"
                ]
            },
            'review_schedule': {
                'intervals': ['1 day', '3 days', '1 week', '2 weeks', '1 month'],
                'next_review': '1 day'
            }
        }
        
        return rich_content

    def _generate_basic_topic_content(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic topic content when LLM is unavailable"""
        topic_name = topic_data.get('topic_name', 'Topic')
        concepts = topic_data.get('concepts', [])
        
        return {
            'executive_summary': {
                'overview': f"Comprehensive study of {topic_name.lower()} covering key concepts and practical applications.",
                'importance': f"Understanding {topic_name.lower()} is essential for building foundational knowledge in this domain."
            },
            'concepts_deep_dive': {
                'concepts': [
                    {
                        'name': concept,
                        'explanation': f"Key concept in {topic_name.lower()}",
                        'examples': [f"Example application of {concept}"],
                        'analogies': [f"Think of {concept} like a fundamental building block"]
                    } for concept in concepts[:5]
                ]
            },
            'practical_applications': {
                'applications': topic_data.get('practical_applications', [f"Apply {topic_name.lower()} concepts in real-world scenarios"])
            },
            'learning_progression': {
                'milestones': [
                    {'title': f'Understand {topic_name.lower()} fundamentals', 'description': 'Master core concepts'},
                    {'title': f'Practice {topic_name.lower()} applications', 'description': 'Apply knowledge practically'},
                    {'title': f'Synthesize {topic_name.lower()} knowledge', 'description': 'Connect to broader understanding'}
                ]
            },
            'memory_aids': {
                'mnemonics': [f"Remember {topic_name.lower()} through practical examples"],
                'spaced_repetition': {
                    'schedule': [
                        {'topics': concepts[:3], 'timing': 'Review in 1 day'},
                        {'topics': concepts[:3], 'timing': 'Review in 3 days'},
                        {'topics': concepts[:3], 'timing': 'Review in 1 week'}
                    ]
                }
            }
        }

    def _create_applications_showcase(self, rich_content: Dict[str, Any]) -> List[Dict]:
        """Create practical applications showcase"""
        blocks = []
        
        applications = rich_content.get('practical_applications', {}).get('applications', [])
        if not applications:
            return blocks
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🚀 Practical Applications Showcase"}}]
            }
        })
        
        for i, app in enumerate(applications[:4]):
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": app}}],
                    "icon": {"emoji": "🛠️"},
                    "color": "green_background"
                }
            })
        
        return blocks

    def _create_connection_visualization(self, rich_content: Dict[str, Any], topic_data: Dict[str, Any]) -> List[Dict]:
        """Create connection visualization section"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🕸️ Knowledge Connections"}}]
            }
        })
        
        # Cross-topic connections from rich content
        connections = rich_content.get('cross_topic_connections', {})
        if connections:
            connection_list = connections.get('connections', [])
            for connection in connection_list[:3]:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": f"🔗 {connection}"}}]
                    }
                })
        else:
            # Default connections based on topic concepts
            concepts = topic_data.get('concepts', [])
            if concepts:
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": f"This topic connects through shared concepts: {', '.join(concepts[:3])}"}}],
                        "icon": {"emoji": "🔗"},
                        "color": "blue_background"
                    }
                })
        
        return blocks

    def _create_knowledge_gap_indicators(self, topic_data: Dict[str, Any]) -> List[Dict]:
        """Create knowledge gap indicators"""
        blocks = []
        
        # Identify potential gaps based on topic complexity
        complexity = topic_data.get('complexity', 'intermediate')
        concepts = topic_data.get('concepts', [])
        
        if complexity in ['advanced', 'expert'] or len(concepts) > 6:
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "⚠️ Potential Knowledge Gaps"}}]
                }
            })
            
            gaps = [
                f"Prerequisites for understanding {concepts[0] if concepts else 'advanced concepts'}",
                f"Mathematical foundations underlying {topic_data.get('topic_name', 'this topic')}",
                f"Historical context of {topic_data.get('topic_name', 'this field')}"
            ]
            
            for gap in gaps[:2]:
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": gap}}],
                        "icon": {"emoji": "⚠️"},
                        "color": "orange_background"
                    }
                })
        
        return blocks

    def _create_strategic_next_steps(self, rich_content: Dict[str, Any], topic_data: Dict[str, Any]) -> List[Dict]:
        """Create strategic next steps section"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🎯 Strategic Next Steps"}}]
            }
        })
        
        # Get strategic steps from rich content or generate defaults
        strategic_steps = rich_content.get('strategic_next_steps', {})
        priorities = strategic_steps.get('high_impact_priorities', [])
        
        if not priorities:
            # Generate default strategic steps
            topic_name = topic_data.get('topic_name', 'this topic')
            priorities = [
                f"Practice applying {topic_name.lower()} concepts in real scenarios",
                f"Connect {topic_name.lower()} to related domains you're studying",
                f"Teach {topic_name.lower()} concepts to someone else",
                f"Find advanced resources on {topic_name.lower()}"
            ]
        
        for priority in priorities[:4]:
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": f"🔥 {priority}"}}],
                    "checked": False
                }
            })
        
        return blocks

    def _create_reflection_framework(self, topic_data: Dict[str, Any]) -> List[Dict]:
        """Create reflection and self-assessment framework"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🤔 Reflection & Self-Assessment"}}]
            }
        })
        
        topic_name = topic_data.get('topic_name', 'this topic')
        
        # Self-assessment questions
        reflection_questions = [
            f"What aspects of {topic_name.lower()} do I understand well?",
            f"Where do I need more practice with {topic_name.lower()}?",
            f"How can I apply {topic_name.lower()} in my current projects?",
            f"What questions do I still have about {topic_name.lower()}?"
        ]
        
        for question in reflection_questions:
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": question}}],
                    "icon": {"emoji": "🤔"},
                    "color": "purple_background"
                }
            })
        
        # Add reflection space
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "📝 My Reflections"}}]
            }
        })
        
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "Write your thoughts, insights, and questions here..."}}]
            }
        })
        
        return blocks

    def _create_basic_master_synthesis(self, all_topics: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic master synthesis when LLM is unavailable"""
        topic_count = len(all_topics)
        total_concepts = sum(len(topic_data.get('concepts', [])) for topic_data in all_topics.values())
        
        return {
            'session_overview': {
                'title': f'Multi-Topic Learning Session ({topic_count} Topics)',
                'narrative': f'Comprehensive learning session covering {topic_count} topics with {total_concepts} concepts explored.',
                'key_insights': [f'Explored {topic_count} interconnected topics', f'Mastered {total_concepts} new concepts']
            },
            'topic_relationship_map': {
                'relationships': [f'{topic1} connects to {topic2} through shared concepts' 
                               for i, topic1 in enumerate(all_topics.keys()) 
                               for j, topic2 in enumerate(all_topics.keys()) 
                               if i < j][:3]
            },
            'strategic_next_steps': {
                'high_impact_priorities': [
                    'Review and consolidate learning across all topics',
                    'Practice applying concepts from different topics together',
                    'Identify and fill knowledge gaps discovered',
                    'Connect new learning to existing knowledge base'
                ]
            },
            'synthesis_insights': {
                'cross_connections': topic_count * (topic_count - 1) // 2,
                'knowledge_integration_score': min(topic_count * 20, 100),
                'learning_efficiency': 'high' if topic_count <= 3 else 'moderate'
            }
        }

    def _get_page_url(self, page: Dict[str, Any]) -> str:
        """Get Notion page URL"""
        if not page or 'id' not in page:
            return ""
        
        page_id = page['id'].replace('-', '')
        return f"https://notion.so/{page_id}"

    def _add_concept_content(self, page_id: str, concept_name: str, definition: str):
        """Add content to a concept page"""
        blocks = [
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": f"💡 {concept_name}"}}]
                }
            },
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": definition}}],
                    "icon": {"emoji": "📚"},
                    "color": "blue_background"
                }
            }
        ]
        
        try:
            requests.patch(
                f"{self.notion_api_url}/blocks/{page_id}/children",
                headers=self.headers,
                json={"children": blocks}
            )
        except Exception as e:
            self.logger.warning(f"Failed to add content to concept page: {str(e)}")

    def _add_master_session_content(self, page_id: str, session_metadata: Dict[str, Any], 
                                   pipeline_data: Dict[str, Any], topic_pages: Dict[str, Any],
                                   synthesis_insights: Dict[str, Any]):
        """Add enhanced content to master session page"""
        blocks = []
        
        # Session header
        session_theme = pipeline_data['extracted_concepts'].get('session_theme', 'Knowledge Exploration')
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": f"🧠 Learning Journey: {session_theme.replace('_', ' ').title()}"}}]
            }
        })
        
        # Session overview from synthesis
        session_overview = synthesis_insights.get('session_overview', {})
        overview_text = session_overview.get('narrative', f"Comprehensive learning session covering {len(topic_pages)} topics with {session_metadata['total_concepts']} concepts explored.")
        
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": overview_text}}],
                "icon": {"emoji": "🎯"},
                "color": "blue_background"
            }
        })
        
        # Topic navigation
        if topic_pages:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📚 Topics Explored"}}]
                }
            })
            
            for topic_name, topic_page in topic_pages.items():
                topic_url = self._get_page_url(topic_page)
                if topic_url:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": "📖 "}},
                                {"type": "text", "text": {"content": topic_name}, "link": {"url": topic_url}}
                            ]
                        }
                    })
                else:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": f"📖 {topic_name}"}}]
                        }
                    })
        
        # Key insights
        key_concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        if key_concepts:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "💡 Key Insights Discovered"}}]
                }
            })
            
            for concept in key_concepts[:8]:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": concept}}]
                    }
                })
        
        # Knowledge connections
        historical_connections = pipeline_data.get('historical_connections', {})
        connections_count = historical_connections.get('total_connections_found', 0)
        
        if connections_count > 0:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🔗 Knowledge Connections"}}]
                }
            })
            
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": f"Found {connections_count} connections to your existing knowledge base, strengthening understanding across domains."}}],
                    "icon": {"emoji": "🌟"},
                    "color": "yellow_background"
                }
            })
        
        # Strategic next steps from synthesis
        strategic_steps = synthesis_insights.get('strategic_next_steps', {})
        priorities = strategic_steps.get('high_impact_priorities', [])
        
        if priorities:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🎯 Strategic Next Steps"}}]
                }
            })
            
            for priority in priorities[:5]:
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": f"🔥 {priority}"}}],
                        "checked": False
                    }
                })
        
        # Add all blocks to the page
        try:
            # Notion has a limit on blocks per request, so batch them
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch_blocks = blocks[i:i + batch_size]
                requests.patch(
                    f"{self.notion_api_url}/blocks/{page_id}/children",
                    headers=self.headers,
                    json={"children": batch_blocks}
                )
            
            self.logger.info("Successfully added enhanced content to master session page")
        except Exception as e:
            self.logger.warning(f"Failed to add content to master session page: {str(e)}")

    # ========== FIXED EXISTING METHODS ==========

    def _enhance_topics_with_llm(self, topic_organization: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance topics with a single strategic LLM call
        """
        if not self.llm_client or not topic_organization:
            return self._enhance_topics_without_llm(topic_organization, pipeline_data)
            
        topics_summary = []
        for topic_name, topic_data in topic_organization.items():
            topics_summary.append({
                'name': topic_name,
                'concepts': topic_data['concepts'][:5],
                'source_count': topic_data['source_count'],
                'sample_content': topic_data['captures'][0].get('content', '')[:200] if topic_data['captures'] else ''
            })

        prompt = f"""Enhance these research topics with rich learning context:

TOPICS: {json.dumps(topics_summary, indent=2)}

USER CONTEXT:
- Session Theme: {pipeline_data['extracted_concepts'].get('session_theme', 'general')}
- Knowledge Level: {self._assess_session_knowledge_level(pipeline_data)}

For each topic, provide enhanced_description, learning_outcomes, learning_sequence, key_insights, and practical_applications.

Return JSON format: {{"topic_name": {{"enhanced_description": "...", "learning_outcomes": [...], ...}}}}"""

        try:
            messages = [
                {"role": "system", "content": "You are an expert learning designer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(temperature=0.4, max_tokens=1500)
            response_text = self.llm_client.chat_completion(messages, **request_params)
            llm_enhancements = json.loads(response_text)
            
            for topic_name, topic_data in topic_organization.items():
                if topic_name in llm_enhancements:
                    topic_data.update(llm_enhancements[topic_name])
            
            return topic_organization
            
        except Exception as e:
            self.logger.warning(f"LLM enhancement failed: {str(e)}")
            return self._enhance_topics_without_llm(topic_organization, pipeline_data)

    def _enhance_topics_without_llm(self, topic_organization: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance topics using rule-based methods"""
        for topic_name, topic_data in topic_organization.items():
            topic_data.update({
                'enhanced_description': f"Comprehensive exploration of {topic_name.lower()} concepts and applications",
                'learning_outcomes': [
                    f"Understand core {topic_name.lower()} principles",
                    f"Apply {topic_name.lower()} concepts practically",
                    f"Connect {topic_name.lower()} to related fields"
                ],
                'learning_sequence': [
                    "Review foundational concepts",
                    "Explore practical applications", 
                    "Synthesize with existing knowledge"
                ],
                'key_insights': [f"Key insight about {concept}" for concept in topic_data['concepts'][:3]],
                'memory_aids': [f"Remember {topic_name.lower()} through practical examples"],
                'pedagogical_approach': 'progressive_discovery'
            })
        
        return topic_organization

    # ========== REMAINING HELPER METHODS ==========

    def _intelligent_topic_clustering(self, captures: List[Dict], learning_concepts: List[str]) -> Dict[str, Any]:
        """
        Phase 1: Intelligent Topic Clustering & Organization
        Enhanced semantic clustering using LLM analysis
        """
        if not self.llm_client or not self.llm_client.is_available():
            return self._fallback_rule_based_clustering(captures, learning_concepts)
        
        try:
            # Prepare content for analysis
            content_summary = self._prepare_content_for_clustering(captures, learning_concepts)
            
            clustering_prompt = f"""
            Analyze this learning session and identify 3-7 distinct, coherent research topics:
            
            LEARNING CONCEPTS: {', '.join(learning_concepts[:15])}
            
            CONTENT SOURCES: 
            {content_summary}
            
            For each topic, provide:
            {{
                "topic_name": "Clear, descriptive name",
                "scope": "What this topic encompasses", 
                "complexity_level": "beginner|intermediate|advanced|expert",
                "learning_objectives": ["specific objective 1", "objective 2", "objective 3"],
                "prerequisite_topics": ["prerequisite 1", "prerequisite 2"],
                "related_concepts": ["concept from the list above"],
                "confidence": 0.0-1.0
            }}
            
            Group concepts and sources logically. Ensure topics are:
            - Semantically coherent (concepts naturally belong together)
            - Appropriately scoped (not too broad or narrow)
            - Build logical learning progression
            
            Return JSON: {{"topics": [topic_objects]}}
            """
            
            messages = [
                {"role": "system", "content": "You are an expert learning architect who creates coherent topic clusters for optimal learning."},
                {"role": "user", "content": clustering_prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.3,
                max_tokens=2000
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            clustering_result = json.loads(response_text)
            
            # Process and assign captures to topics
            return self._assign_captures_to_topics(
                clustering_result['topics'], 
                captures, 
                learning_concepts
            )
            
        except Exception as e:
            self.logger.warning(f"Intelligent clustering failed: {str(e)}, falling back to rule-based")
            return self._fallback_rule_based_clustering(captures, learning_concepts)

    def _generate_rich_topic_content(self, topic_data: Dict, user_context: Dict) -> Dict[str, Any]:
        """
        Phase 2: Rich Content Generation Per Topic
        Creates comprehensive, engaging content adapted to user's knowledge level
        """
        if not self.llm_client or not self.llm_client.is_available():
            return self._generate_basic_topic_content(topic_data)
        
        try:
            knowledge_level = user_context.get('knowledge_level', 'intermediate')
            learning_style = user_context.get('learning_style', 'progressive')
            
            content_prompt = f"""
            Create rich, engaging learning content for this topic:
            
            TOPIC: {topic_data['topic_name']}
            SCOPE: {topic_data['scope']}
            CONCEPTS: {', '.join(topic_data['concepts'][:10])}
            USER LEVEL: {knowledge_level}
            LEARNING STYLE: {learning_style}
            
            Generate comprehensive content:
            
            1. EXECUTIVE SUMMARY (adapted to {knowledge_level} level):
            - Compelling hook that captures attention
            - Clear overview with appropriate depth
            - Why this topic matters now
            
            2. CORE CONCEPTS DEEP DIVE:
            - Progressive complexity building
            - Rich examples and analogies
            - Visual metaphors for complex ideas
            - Memory aids and mnemonics
            
            3. PRACTICAL APPLICATIONS:
            - Real-world use cases
            - Hands-on exercises
            - Project ideas
            
            4. LEARNING PROGRESSION:
            - Step-by-step mastery path
            - Milestone checkpoints
            - Self-assessment criteria
            
            5. CROSS-TOPIC CONNECTIONS:
            - How this connects to other domains
            - Prerequisites clarified
            - Advanced applications
            
            6. MEMORY AIDS & RETENTION:
            - Mnemonics for key concepts
            - Spaced repetition schedule
            - Review checkpoints
            
            Return structured JSON with rich content for each section.
            """
            
            messages = [
                {"role": "system", "content": "You are an expert learning designer creating engaging, memorable educational content."},
                {"role": "user", "content": content_prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.4,
                max_tokens=2500
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            rich_content = json.loads(response_text)
            
            # Enhance with interactive elements
            return self._add_interactive_elements(rich_content, topic_data)
            
        except Exception as e:
            self.logger.warning(f"Rich content generation failed: {str(e)}")
            return self._generate_basic_topic_content(topic_data)

    def _create_master_session_synthesis(self, all_topics: Dict, synthesis_insights: Dict, pipeline_data: Dict) -> Dict[str, Any]:
        """
        Phase 4: Cross-Topic Synthesis & Master Page
        Creates comprehensive master session page with novel insights
        """
        if not self.llm_client or not self.llm_client.is_available():
            return self._create_basic_master_synthesis(all_topics, pipeline_data)
        
        try:
            # Prepare synthesis data
            topic_summary = {name: {
                'concepts': data['concepts'][:5],
                'complexity': data.get('complexity', 'intermediate'),
                'connections': data.get('cross_topic_connections', [])
            } for name, data in all_topics.items()}
            
            synthesis_prompt = f"""
            Synthesize this multi-topic learning session into strategic insights:
            
            TOPICS COVERED: {json.dumps(topic_summary, indent=2)}
            
            KNOWLEDGE CONNECTIONS: {pipeline_data.get('historical_connections', {}).get('total_connections_found', 0)}
            KNOWLEDGE GAPS: {len(pipeline_data.get('knowledge_gaps', []))}
            
            Generate comprehensive synthesis:
            
            1. SESSION OVERVIEW:
            - Unifying theme across all topics
            - Learning journey narrative
            - Key insights discovered
            
            2. TOPIC RELATIONSHIP MAP:
            - How topics build upon each other
            - Prerequisites and dependencies
            - Synergistic combinations
            
            3. STRATEGIC NEXT STEPS:
            - High-impact learning priorities
            - Knowledge gap filling strategy
            - Advanced exploration paths
            
            4. KNOWLEDGE INTEGRATION:
            - How to apply learnings together
            - Cross-domain applications
            - Real-world project ideas
            
            Return rich JSON with actionable insights and beautiful narrative structure.
            """
            
            messages = [
                {"role": "system", "content": "You are an expert learning synthesizer who creates coherent learning narratives and strategic insights."},
                {"role": "user", "content": synthesis_prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.4,
                max_tokens=2500
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            synthesis_result = json.loads(response_text)
            
            return synthesis_result
            
        except Exception as e:
            self.logger.warning(f"Master synthesis failed: {str(e)}")
            return self._create_basic_master_synthesis(all_topics, pipeline_data)

    # Existing methods remain the same...
    def _identify_topics_from_content(self, raw_captures: List[Dict], learning_concepts: List[str]) -> Dict[str, Any]:
        """
        Identify topics using rule-based analysis of content and concepts
        """
        topic_scores = defaultdict(lambda: {'captures': [], 'concepts': [], 'score': 0})
        
        # Analyze each capture for topic indicators
        for capture in raw_captures:
            content = (capture.get('content', '') + ' ' + capture.get('title', '')).lower()
            
            for topic, indicators in self.topic_indicators.items():
                score = sum(1 for indicator in indicators if indicator in content)
                if score > 0:
                    topic_scores[topic]['captures'].append(capture)
                    topic_scores[topic]['score'] += score
        
        # Analyze concepts for topic alignment
        all_concepts_text = ' '.join(learning_concepts).lower()
        for topic, indicators in self.topic_indicators.items():
            concept_score = sum(1 for indicator in indicators if indicator in all_concepts_text)
            if concept_score > 0:
                topic_scores[topic]['concepts'].extend([c for c in learning_concepts if any(ind in c.lower() for ind in indicators)])
                topic_scores[topic]['score'] += concept_score * 2  # Weight concepts higher
        
        # Filter and clean topics
        filtered_topics = {}
        for topic, data in topic_scores.items():
            if data['score'] >= 2:  # Minimum threshold
                filtered_topics[topic.replace('_', ' ').title()] = {
                    'topic_name': topic.replace('_', ' ').title(),
                    'scope': f"Study of {topic.replace('_', ' ').lower()}",
                    'captures': data['captures'],
                    'concepts': list(set(data['concepts'])),
                    'confidence': min(data['score'] / 10.0, 1.0),
                    'source_count': len(data['captures']),
                    'practical_applications': self._extract_practical_applications(data['captures'])
                }
        
        # If no clear topics found, create a general topic
        if not filtered_topics:
            filtered_topics['General Learning'] = {
                'topic_name': 'General Learning',
                'scope': 'General knowledge exploration',
                'captures': raw_captures,
                'concepts': learning_concepts,
                'confidence': 0.5,
                'source_count': len(raw_captures),
                'practical_applications': self._extract_practical_applications(raw_captures)
            }
        
        return filtered_topics

    def _add_rich_topic_content(self, page_id: str, topic_name: str, topic_data: Dict[str, Any], 
                               pipeline_data: Dict[str, Any], color_theme: str):
        """
        Add beautifully structured content to the topic page
        """
        blocks = []
        
        # Topic Overview Callout
        blocks.extend(self._create_topic_overview_section(topic_name, topic_data, color_theme))
        
        # Learning Progress Tracker
        blocks.extend(self._create_progress_tracking_section(topic_data))
        
        # Core Concepts Deep Dive
        blocks.extend(self._create_concepts_deep_dive_section(topic_data, pipeline_data))
        
        # Practical Applications
        blocks.extend(self._create_applications_section(topic_data))
        
        # Knowledge Connections
        blocks.extend(self._create_connections_section(topic_name, topic_data, pipeline_data))
        
        # Sources and References
        blocks.extend(self._create_sources_section(topic_data))
        
        # Next Steps and Action Items
        blocks.extend(self._create_next_steps_section(topic_data, pipeline_data))
        
        # Research Questions and Reflection
        blocks.extend(self._create_reflection_section(topic_name, topic_data))
        
        # Add all content to the page
        try:
            # Notion has a limit on blocks per request, so batch them
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch_blocks = blocks[i:i + batch_size]
                requests.patch(
                    f"{self.notion_api_url}/blocks/{page_id}/children",
                    headers=self.headers,
                    json={"children": batch_blocks}
                )
            
            self.logger.info(f"Successfully added rich content to topic page: {topic_name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to add content to topic page '{topic_name}': {str(e)}")

    def _create_topic_overview_section(self, topic_name: str, topic_data: Dict[str, Any], color_theme: str) -> List[Dict]:
        """Create compelling topic overview section"""
        blocks = []
        
        # Main title with emoji
        topic_emoji, _ = self._get_topic_visual_theme(topic_name)
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": f"{topic_emoji} {topic_name}"}}],
                "color": "blue"
            }
        })
        
        # Overview callout
        description = topic_data.get('enhanced_description', f'Deep dive into {topic_name.lower()} concepts and applications')
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": description}}],
                "icon": {"emoji": "🎯"},
                "color": f"{color_theme}_background"
            }
        })
        
        # Learning objectives
        learning_outcomes = topic_data.get('learning_outcomes', [])
        if learning_outcomes:
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "🎯 Learning Objectives"}}]
                }
            })
            
            for outcome in learning_outcomes[:4]:  # Limit to top 4
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": outcome}}]
                    }
                })
        
        blocks.append({"object": "block", "type": "divider", "divider": {}})
        return blocks

    def _create_progress_tracking_section(self, topic_data: Dict[str, Any]) -> List[Dict]:
        """Create interactive progress tracking section"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📈 Learning Progress"}}]
            }
        })
        
        # Learning sequence as checkboxes
        learning_sequence = topic_data.get('learning_sequence', ['Review concepts', 'Practice applications', 'Connect to other knowledge'])
        
        for step in learning_sequence:
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": step}}],
                    "checked": False
                }
            })
        
        return blocks

    def _create_concepts_deep_dive_section(self, topic_data: Dict[str, Any], pipeline_data: Dict[str, Any]) -> List[Dict]:
        """Create rich concepts explanation section"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "💡 Core Concepts"}}]
            }
        })
        
        concepts = topic_data.get('concepts', [])
        key_insights = topic_data.get('key_insights', [])
        
        # Get concept explanations from extracted_concepts if available
        concept_explanations = pipeline_data['extracted_concepts'].get('key_terms', {})
        
        for i, concept in enumerate(concepts[:6]):  # Limit to top 6 concepts
            # Create toggle for each concept
            concept_content = []
            
            # Add explanation if available
            if concept in concept_explanations:
                concept_content.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": concept_explanations[concept]}}]
                    }
                })
            
            # Add insight if available
            if i < len(key_insights):
                concept_content.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": key_insights[i]}}],
                        "icon": {"emoji": "💡"},
                        "color": "yellow_background"
                    }
                })
            
            # Create toggle block
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": f"🔍 {concept}"}}],
                    "children": concept_content if concept_content else [{
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": f"Key concept in {topic_data.get('topic_name', 'this topic')} - explore further through your sources."}}]
                        }
                    }]
                }
            })
        
        return blocks

    def _create_applications_section(self, topic_data: Dict[str, Any]) -> List[Dict]:
        """Create practical applications section"""
        blocks = []
        
        applications = topic_data.get('practical_applications', [])
        if not applications:
            return blocks
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🛠️ Practical Applications"}}]
            }
        })
        
        for app in applications[:5]:  # Limit to top 5
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": app}}],
                    "icon": {"emoji": "🚀"},
                    "color": "green_background"
                }
            })
        
        return blocks

    def _create_connections_section(self, topic_name: str, topic_data: Dict[str, Any], pipeline_data: Dict[str, Any]) -> List[Dict]:
        """Create knowledge connections section"""
        blocks = []
        
        # Find connections from historical analysis
        historical_connections = pipeline_data.get('historical_connections', {})
        direct_connections = historical_connections.get('direct_connections', [])
        semantic_connections = historical_connections.get('semantic_connections', [])
        
        # Filter connections related to this topic
        topic_connections = []
        topic_keywords = topic_name.lower().split()
        
        for conn in direct_connections + semantic_connections:
            new_concept = conn.get('new_concept', '').lower()
            existing_concept = conn.get('existing_concept', '').lower()
            
            if any(keyword in new_concept or keyword in existing_concept for keyword in topic_keywords):
                topic_connections.append(conn)
        
        if topic_connections:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🔗 Knowledge Connections"}}]
                }
            })
            
            for conn in topic_connections[:4]:  # Top 4 connections
                connection_strength = conn.get('connection_strength', 'moderate')
                emoji = "🔥" if connection_strength == 'strong' else "⚡"
                explanation = conn.get('explanation', 'Related concepts discovered')
                
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": f"{emoji} {explanation}"}}]
                    }
                })
        
        return blocks

    def _create_sources_section(self, topic_data: Dict[str, Any]) -> List[Dict]:
        """Create sources and references section"""
        blocks = []
        
        captures = topic_data.get('captures', [])
        if not captures:
            return blocks
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📚 Sources & References"}}]
            }
        })
        
        for capture in captures[:8]:  # Limit to top 8 sources
            title = capture.get('title', 'Untitled Source')
            url = capture.get('url', '')
            content_preview = capture.get('content', '')[:150] + "..." if len(capture.get('content', '')) > 150 else capture.get('content', '')
            
            # Create rich source block
            source_blocks = []
            
            if url and url != 'unknown':
                source_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "🔗 ", "link": None}},
                            {"type": "text", "text": {"content": title}, "link": {"url": url}}
                        ]
                    }
                })
            else:
                source_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": f"📄 {title}"}}]
                    }
                })
            
            if content_preview.strip():
                source_blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": [{"type": "text", "text": {"content": content_preview}}]
                    }
                })
            
            # Add as toggle for clean organization
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": f"📖 {title}"}}],
                    "children": source_blocks
                }
            })
        
        return blocks

    def _create_next_steps_section(self, topic_data: Dict[str, Any], pipeline_data: Dict[str, Any]) -> List[Dict]:
        """Create actionable next steps section"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🎯 Next Steps & Action Items"}}]
            }
        })
        
        # Get recommendations from pipeline
        recommendations = pipeline_data.get('learning_recommendations', [])
        topic_keywords = topic_data.get('concepts', [])
        
        # Filter recommendations relevant to this topic
        relevant_recommendations = []
        for rec in recommendations:
            rec_text = (rec.get('action', '') + ' ' + rec.get('concept', '')).lower()
            if any(keyword.lower() in rec_text for keyword in topic_keywords):
                relevant_recommendations.append(rec)
        
        # Add topic-specific next steps
        learning_sequence = topic_data.get('learning_sequence', [])
        for step in learning_sequence[1:]:  # Skip first step (already in progress tracker)
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": f"📚 {step}"}}],
                    "checked": False
                }
            })
        
        # Add relevant recommendations
        for rec in relevant_recommendations[:3]:
            priority_emoji = {"high": "🔥", "medium": "⚡", "low": "📝"}.get(rec.get('priority', 'medium'), "📝")
            action = rec.get('action', rec.get('recommended_action', 'Continue learning'))
            
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": f"{priority_emoji} {action}"}}],
                    "checked": False
                }
            })
        
        return blocks

    def _create_reflection_section(self, topic_name: str, topic_data: Dict[str, Any]) -> List[Dict]:
        """Create reflection and research questions section"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🤔 Reflection & Research Questions"}}]
            }
        })
        
        # Generate thought-provoking questions
        reflection_questions = [
            f"How does {topic_name.lower()} connect to my other areas of study?",
            f"What real-world problems could I solve with {topic_name.lower()}?",
            f"What aspects of {topic_name.lower()} do I find most challenging?",
            f"How has my understanding of {topic_name.lower()} evolved?",
            f"What would I teach someone else about {topic_name.lower()}?"
        ]
        
        for question in reflection_questions:
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": question}}],
                    "icon": {"emoji": "🤔"},
                    "color": "purple_background"
                }
            })
        
        # Add space for personal notes
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "📝 Personal Notes & Insights"}}]
            }
        })
        
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "Add your personal insights, questions, and connections here..."}}]
            }
        })
        
        return blocks

    # Helper methods for database and utility functions
    def _get_or_create_database(self, db_type: str) -> str:
        """Get existing database or create new one"""
        # Search for existing database
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

        response = requests.post(f"{self.notion_api_url}/databases", headers=self.headers, json=database_data)
        response.raise_for_status()
        
        database_id = response.json()['id']
        self.logger.info(f"Created database '{db_type}': {database_id}")
        return database_id

    def _ensure_enhanced_databases_exist(self) -> Dict[str, str]:
        """Ensure all enhanced databases exist"""
        databases = {}
        
        for db_type in ['learning_sessions', 'research_topics', 'concept_library']:
            if db_type in self.database_schemas:
                db_id = self._get_or_create_database(db_type)
                databases[db_type] = db_id
                self.logger.info(f"Enhanced database '{db_type}' ready: {db_id}")
        
        # Set up database relationships
        self._setup_enhanced_database_relationships(databases)
        return databases

    def _setup_enhanced_database_relationships(self, databases: Dict[str, str]):
        """Set up relationships between enhanced databases"""
        try:
            # Add relations to concept library
            if 'concept_library' in databases:
                requests.patch(
                    f"{self.notion_api_url}/databases/{databases['concept_library']}",
                    headers=self.headers,
                    json={
                        "properties": {
                            "Related Concepts": {
                                "relation": {
                                    "database_id": databases['concept_library'],
                                    "dual_property": {}
                                }
                            },
                            "From Topics": {
                                "relation": {
                                    "database_id": databases['research_topics'],
                                    "single_property": {}
                                }
                            }
                        }
                    }
                )
            
            self.logger.info("Enhanced database relationships configured")
            
        except Exception as e:
            self.logger.warning(f"Failed to set up database relationships: {str(e)}")

    def _test_notion_connection(self):
        """Test Notion API connection"""
        response = requests.get(
            f"{self.notion_api_url}/users/me",
            headers=self.headers
        )
        response.raise_for_status()

    # Helper methods for visual themes and classifications
    def _get_topic_visual_theme(self, topic_name: str) -> tuple:
        """Get emoji and color theme for topic"""
        topic_lower = topic_name.lower()
        
        theme_map = {
            'machine learning': ('🤖', 'blue'),
            'artificial intelligence': ('🧠', 'purple'),
            'data science': ('📊', 'green'),
            'software engineering': ('💻', 'gray'),
            'business strategy': ('📈', 'red'),
            'psychology': ('🧭', 'orange'),
            'research methods': ('🔬', 'brown'),
            'technology': ('⚡', 'yellow')
        }
        
        for key, (emoji, color) in theme_map.items():
            if key in topic_lower:
                return emoji, color
        
        return '📚', 'blue'  # Default

    def _classify_domain(self, topic_name: str) -> str:
        """Classify topic into domain"""
        topic_lower = topic_name.lower()
        
        if any(term in topic_lower for term in ['machine learning', 'ai', 'artificial intelligence']):
            return 'Artificial Intelligence'
        elif any(term in topic_lower for term in ['data', 'statistics', 'analysis']):
            return 'Data Science'
        elif any(term in topic_lower for term in ['business', 'strategy', 'management']):
            return 'Business'
        elif any(term in topic_lower for term in ['psychology', 'cognitive', 'behavior']):
            return 'Psychology'
        elif any(term in topic_lower for term in ['software', 'programming', 'engineering']):
            return 'Technology'
        else:
            return 'General'

    def _assess_session_knowledge_level(self, pipeline_data: Dict[str, Any]) -> str:
        """Assess overall session knowledge level"""
        complexity = pipeline_data['extracted_concepts'].get('complexity_assessment', {}).get('overall_level', 'intermediate')
        concepts_count = len(pipeline_data['extracted_concepts'].get('learning_concepts', []))
        
        if complexity == 'advanced' or concepts_count > 10:
            return 'Advanced'
        elif complexity == 'basic' and concepts_count < 5:
            return 'Beginner'
        else:
            return 'Intermediate'

    def _assess_topic_complexity(self, captures: List[Dict], concepts: List[str]) -> str:
        """Assess complexity of a specific topic"""
        if len(concepts) > 8:
            return 'Advanced'
        elif len(concepts) > 4:
            return 'Intermediate'
        else:
            return 'Foundational'

    def _extract_learning_objectives(self, captures: List[Dict], concepts: List[str]) -> List[str]:
        """Extract learning objectives from captures and concepts"""
        objectives = []
        
        # Generate objectives based on concepts
        if concepts:
            objectives.append(f"Understand {len(concepts)} core concepts")
            objectives.append(f"Apply {concepts[0] if concepts else 'key principles'} in practice")
            objectives.append("Connect new knowledge to existing understanding")
        
        return objectives

    def _extract_practical_applications(self, captures: List[Dict]) -> List[str]:
        """Extract practical applications from capture content"""
        applications = []
        
        for capture in captures:
            content = capture.get('content', '').lower()
            
            # Look for application indicators
            if 'example' in content or 'application' in content:
                applications.append(f"Practical example from {capture.get('title', 'source')}")
            elif 'use case' in content:
                applications.append(f"Use case identified in {capture.get('title', 'source')}")
            elif 'implement' in content or 'practice' in content:
                applications.append(f"Implementation guidance from {capture.get('title', 'source')}")
        
        # Add generic applications if none found
        if not applications:
            applications = [
                "Apply concepts to real-world scenarios",
                "Practice through hands-on exercises",
                "Teach concepts to others"
            ]
        
        return applications[:5]  # Limit to 5

    def _gap_relates_to_topic(self, gap: Dict[str, Any], topic_name: str) -> bool:
        """Check if a knowledge gap relates to a specific topic"""
        gap_concept = gap.get('missing_concept', '').lower()
        topic_keywords = topic_name.lower().split()
        
        return any(keyword in gap_concept for keyword in topic_keywords)