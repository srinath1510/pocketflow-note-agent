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
        required_data = {
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


        topic_organization = self._organize_content_by_topics(pipeline_data)
        
        if self.llm_client and self.llm_client.is_available():
            enhanced_topics = self._enhance_topics_with_llm(topic_organization, pipeline_data)
        else:
            enhanced_topics = self._enhance_topics_without_llm(topic_organization, pipeline_data)
        
        prep_data = {
            'pipeline_data': pipeline_data,
            'topic_organization': enhanced_topics,
            'session_metadata': {
                'session_id': pipeline_data['session_id'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'topics_identified': len(enhanced_topics),
                'total_concepts': len(pipeline_data['extracted_concepts'].get('learning_concepts', [])),
                'knowledge_level': self._assess_session_knowledge_level(pipeline_data)
            }
        }
        
        self.logger.info(f"Prepared enhanced Notion generation - {len(enhanced_topics)} topics identified")
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
            for topic_name, topic_data in topic_organization.items():
                topic_page = self._create_rich_topic_page(
                    topic_name, topic_data, databases['research_topics'], pipeline_data
                )
                topic_pages[topic_name] = topic_page
            
            # Step 3: Create/update concept library entries
            concept_entries = self._create_concept_library_entries(
                pipeline_data['extracted_concepts'], databases['concept_library'], topic_organization
            )
            
            # Step 4: Create master session page with topic overview
            master_session_page = self._create_master_session_page(
                session_metadata, pipeline_data, topic_pages, databases['learning_sessions']
            )
            
            # Step 5: Create cross-topic relationships and synthesis
            synthesis_insights = self._create_synthesis_insights(topic_organization, pipeline_data)
            
            # Step 6: Update database relationships
            self._update_database_relationships(databases, topic_pages, concept_entries, master_session_page)
            
            return {
                'master_session_page': master_session_page,
                'topic_pages': topic_pages,
                'concept_entries': concept_entries,
                'synthesis_insights': synthesis_insights,
                'databases': databases,
                'creation_summary': {
                    'session_page_created': bool(master_session_page),
                    'topic_pages_created': len(topic_pages),
                    'concepts_documented': len(concept_entries),
                    'total_pages': 1 + len(topic_pages) + len(concept_entries),
                    'topics_covered': list(topic_organization.keys())
                },
                'notion_urls': {
                    'master_session': master_session_page.get('url') if master_session_page else None,
                    'topic_pages': {name: page.get('url') for name, page in topic_pages.items()},
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
            'concepts_documented': exec_result['creation_summary']['concepts_documented'],
            'topics_covered': exec_result['creation_summary']['topics_covered']
        }
        
        self.logger.info(f"Enhanced Notion generation complete - {exec_result['creation_summary']['total_pages']} pages created")
        return "default"


    def _organize_content_by_topics(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Organize content by topics using existing pipeline data (no LLM calls)
        Leverages session_theme, learning_concepts, and content analysis
        """
        topics = {}
        
        # Get session theme as primary topic
        session_theme = pipeline_data['extracted_concepts'].get('session_theme', 'general_learning')
        learning_concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        raw_captures = pipeline_data['raw_captures']
        
        # Rule-based topic identification from content
        content_topics = self._identify_topics_from_content(raw_captures, learning_concepts)
        
        # If only one clear topic, create focused single-topic organization
        if len(content_topics) == 1:
            topic_name = list(content_topics.keys())[0]
            topics[topic_name] = {
                'primary_topic': True,
                'captures': raw_captures,
                'concepts': learning_concepts,
                'complexity': self._assess_topic_complexity(raw_captures, learning_concepts),
                'learning_objectives': self._extract_learning_objectives(raw_captures, learning_concepts),
                'practical_applications': self._extract_practical_applications(raw_captures),
                'source_count': len(raw_captures)
            }
        else:
            # Multi-topic organization
            for topic_name, topic_info in content_topics.items():
                topic_captures = topic_info['captures']
                topic_concepts = topic_info['concepts']
                
                topics[topic_name] = {
                    'primary_topic': topic_name == session_theme,
                    'captures': topic_captures,
                    'concepts': topic_concepts,
                    'complexity': self._assess_topic_complexity(topic_captures, topic_concepts),
                    'learning_objectives': self._extract_learning_objectives(topic_captures, topic_concepts),
                    'practical_applications': self._extract_practical_applications(topic_captures),
                    'source_count': len(topic_captures)
                }
        
        return topics


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
                    'captures': data['captures'],
                    'concepts': list(set(data['concepts'])),
                    'confidence': min(data['score'] / 10.0, 1.0)
                }
        
        # If no clear topics found, create a general topic
        if not filtered_topics:
            filtered_topics['General Learning'] = {
                'captures': raw_captures,
                'concepts': learning_concepts,
                'confidence': 0.5
            }
        
        return filtered_topics

    def _enhance_topics_with_llm(self, topic_organization: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance topics with a single strategic LLM call
        """
        if not topic_organization:
            return topic_organization

    def _create_rich_topic_page(self, topic_name: str, topic_data: Dict[str, Any], 
                               topics_db_id: str, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a beautifully rich Notion page for a specific topic
        """
        # Determine topic emoji and color theme
        topic_emoji, color_theme = self._get_topic_visual_theme(topic_name)
        
        # Create database entry for topic
        page_data = {
            "parent": {"database_id": topics_db_id},
            "properties": {
                "Topic Name": {"title": [{"text": {"content": f"{topic_emoji} {topic_name}"}}]},
                "Domain": {"select": {"name": self._classify_domain(topic_name)}},
                "Complexity Level": {"select": {"name": topic_data.get('complexity', 'Intermediate')}},
                "Learning Status": {"select": {"name": "Learning"}},
                "First Encountered": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
                "Last Reviewed": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
                "Session Count": {"number": 1},
                "Concepts Count": {"number": len(topic_data.get('concepts', []))},
                "Practical Applications": {"number": len(topic_data.get('practical_applications', []))},
                "Knowledge Gaps": {"number": len([gap for gap in pipeline_data.get('knowledge_gaps', []) if self._gap_relates_to_topic(gap, topic_name)])},
                "Next Steps": {"rich_text": [{"text": {"content": topic_data.get('learning_sequence', ['Continue learning'])[0]}}]}
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
            self._add_rich_topic_content(topic_page['id'], topic_name, topic_data, pipeline_data, color_theme)
            
            return topic_page
            
        except Exception as e:
            self.logger.error(f"Failed to create topic page for '{topic_name}': {str(e)}")
            return {}

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

    def _create_master_session_page(self, session_metadata: Dict[str, Any], pipeline_data: Dict[str, Any], 
                                   topic_pages: Dict[str, Any], sessions_db_id: str) -> Dict[str, Any]:
        """Create comprehensive master session page"""
        
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
            self._add_master_session_content(master_page['id'], session_metadata, pipeline_data, topic_pages)
            
            return master_page
            
        except Exception as e:
            self.logger.error(f"Failed to create master session page: {str(e)}")
            return {}

    def _add_master_session_content(self, page_id: str, session_metadata: Dict[str, Any], 
                                   pipeline_data: Dict[str, Any], topic_pages: Dict[str, Any]):
        """Add rich content to master session page"""
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
        
        # Session overview
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"Comprehensive learning session covering {len(topic_pages)} topics with {session_metadata['total_concepts']} concepts explored."}}],
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
                topic_url = topic_page.get('url', '')
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
        
        # Key insights from session
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
        
        # Knowledge connections found
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
                    "rich_text": [{"type": "text", "text": {"content": f"Found {connections_count} connections to your existing knowledge base, strengthening your understanding across domains."}}],
                    "icon": {"emoji": "🌟"},
                    "color": "yellow_background"
                }
            })
        
        # Batch optimization results
        batch_metrics = pipeline_data.get('batch_metrics', {})
        if batch_metrics and batch_metrics.get('api_calls_saved', 0) > 0:
            api_calls_saved = batch_metrics['api_calls_saved']
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": f"🚀 Efficient Processing: Saved {api_calls_saved} API calls through intelligent batch optimization!"}}],
                    "icon": {"emoji": "⚡"},
                    "color": "green_background"
                }
            })
        
        # Next steps
        recommendations = pipeline_data.get('learning_recommendations', [])
        if recommendations:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🎯 Strategic Next Steps"}}]
                }
            })
            
            high_priority_recs = [rec for rec in recommendations if rec.get('priority') == 'high']
            for rec in high_priority_recs[:5]:
                action = rec.get('action', rec.get('recommended_action', 'Continue learning'))
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": f"🔥 {action}"}}],
                        "checked": False
                    }
                })
        
        # Add all blocks to the page
        try:
            requests.patch(
                f"{self.notion_api_url}/blocks/{page_id}/children",
                headers=self.headers,
                json={"children": blocks}
            )
            self.logger.info("Successfully added content to master session page")
        except Exception as e:
            self.logger.warning(f"Failed to add content to master session page: {str(e)}")

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

    # ... continue with remaining helper methods for concept library, synthesis, etc.

    def _test_notion_connection(self):
        """Test Notion API connection"""
        response = requests.get(
            f"{self.notion_api_url}/users/me",
            headers=self.headers
        )
        response.raise_for_status()
        
        # Prepare context for LLM enhancement
        topics_summary = []
        for topic_name, topic_data in topic_organization.items():
            topics_summary.append({
                'name': topic_name,
                'concepts': topic_data['concepts'][:5],  # Top 5 concepts
                'source_count': topic_data['source_count'],
                'sample_content': topic_data['captures'][0].get('content', '')[:200] if topic_data['captures'] else ''
            })
        
        # Single LLM call to enhance all topics
        prompt = f"""Enhance these research topics with rich learning context. Add compelling descriptions, learning outcomes, and pedagogical structure.

TOPICS IDENTIFIED:
{json.dumps(topics_summary, indent=2)}

USER CONTEXT:
- Session Theme: {pipeline_data['extracted_concepts'].get('session_theme', 'general')}
- Knowledge Level: {self._assess_session_knowledge_level(pipeline_data)}
- Total Concepts: {len(pipeline_data['extracted_concepts'].get('learning_concepts', []))}

For each topic, provide:
1. Compelling description that motivates learning
2. Clear learning outcomes
3. Optimal learning sequence
4. Key insights and "aha moments"
5. Practical applications
6. Memory aids and mnemonics

Return JSON:
{{
    "topic_name": {{
        "enhanced_description": "compelling description",
        "learning_outcomes": ["outcome1", "outcome2"],
        "learning_sequence": ["step1", "step2"],
        "key_insights": ["insight1", "insight2"],
        "memory_aids": ["aid1", "aid2"],
        "practical_applications": ["app1", "app2"],
        "pedagogical_approach": "best_learning_method"
    }}
}}"""

        try:
            messages = [
                {"role": "system", "content": "You are an expert learning designer. Create rich, engaging educational content. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.4,
                max_tokens=1500
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            llm_enhancements = json.loads(response_text)
            
            # Merge LLM enhancements with existing topic data
            for topic_name, topic_data in topic_organization.items():
                if topic_name in llm_enhancements:
                    topic_data.update(llm_enhancements[topic_name])
            
            self.logger.info("Successfully enhanced topics with LLM")
            return topic_organization
            
        except Exception as e:
            self.logger.warning(f"LLM enhancement failed, using rule-based enhancement: {str(e)}")
            return self._enhance_topics_without_llm(topic_organization, pipeline_data)

    def _enhance_topics_without_llm(self, topic_organization: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance topics using rule-based methods when LLM is unavailable
        """
        for topic_name, topic_data in topic_organization.items():
            # Add rule-based enhancements
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