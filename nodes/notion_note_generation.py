"""
NotionNoteGenerationNode - Main orchestrator
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Any
from dotenv import load_dotenv
from pocketflow import Node as BaseNode

from .notion.client import NotionClient
from .notion.database_manager import NotionDatabaseManager
from .notion.topic_organizer import TopicOrganizer
from .notion.content_enhancer import ContentEnhancer
from .notion.page_builder import NotionPageBuilder
from .notion.block_builder import NotionBlockBuilder
from .llm_client import get_llm_client

load_dotenv()

class NotionNoteGenerationNode(BaseNode):
    """Main orchestrator for enhanced Notion note generation with topic-based organization"""

    def __init__(self):
        """Initialize all components"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        try:
            self.notion_client = NotionClient()
            self.database_manager = NotionDatabaseManager(self.notion_client)
            self.topic_organizer = TopicOrganizer()
            self.content_enhancer = ContentEnhancer()
            self.page_builder = NotionPageBuilder(self.notion_client)
            self.block_builder = NotionBlockBuilder(self.notion_client)
            
            self.logger.info("All Notion components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Notion components: {str(e)}")
            raise
        
        # Emojis for different content types
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

    def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare for Notion note generation"""
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

        # Test Notion connection
        try:
            if not self.notion_client.test_connection():
                return {'error': 'Notion API connection failed'}
            self.logger.info("Notion API connection successful")
        except Exception as e:
            self.logger.error(f"Notion API connection failed: {str(e)}")
            return {'error': f'Notion API connection failed: {str(e)}'}

        # Organize content into topics
        topic_organization = self.topic_organizer.intelligent_topic_clustering(
            pipeline_data['raw_captures'],
            pipeline_data['extracted_concepts'].get('learning_concepts', [])
        )

        # Assess user context
        user_context = {
            'knowledge_level': self._assess_session_knowledge_level(pipeline_data),
            'learning_style': 'progressive',
            'session_theme': pipeline_data['extracted_concepts'].get('session_theme', 'general')
        }

        # Enhance topics with rich content
        enhanced_topics = {}
        for topic_name, topic_data in topic_organization.items():
            rich_content = self.content_enhancer.generate_rich_topic_content(topic_data, user_context)
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
                'enhancement_level': 'modular_architecture'
            }
        }

        return prep_data

    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """Core execution: Create topic organized Notion pages"""
        if 'error' in prep_result:
            return prep_result
            
        self.logger.info("Starting Notion Note Generation core execution")

        pipeline_data = prep_result['pipeline_data']
        topic_organization = prep_result['topic_organization']
        session_metadata = prep_result['session_metadata']
        
        try:
            # Step 1: Ensure enhanced databases exist
            databases = self.database_manager.ensure_enhanced_databases_exist()
            
            # Step 2: Create topic pages (one per topic)
            topic_pages = {}
            for topic_name, enhanced_topic_data in topic_organization.items():
                rich_content = enhanced_topic_data.get('rich_content', {})
                
                topic_page = self.page_builder.create_enhanced_topic_page(
                    topic_name, 
                    enhanced_topic_data, 
                    rich_content,
                    databases['research_topics'], 
                    pipeline_data
                )
                
                if topic_page:
                    # Add rich content using block builder
                    topic_emoji, color_theme = self._get_topic_visual_theme(topic_name)
                    self.block_builder.add_rich_topic_content(
                        topic_page['id'], 
                        topic_name, 
                        enhanced_topic_data, 
                        pipeline_data, 
                        color_theme
                    )
                    topic_pages[topic_name] = topic_page
            
            # Step 3: Create enhanced concept library entries
            concept_entries = self.page_builder.create_enhanced_concept_library_entries(
                pipeline_data['extracted_concepts'], 
                databases['concept_library'], 
                topic_organization
            )
            
            # Step 4: Enhanced synthesis
            synthesis_insights = self.content_enhancer._create_master_session_synthesis(
                topic_organization, 
                {},
                pipeline_data
            )
            
            # Step 5: Enhanced master page
            master_session_page = self.page_builder.create_enhanced_master_session_page(
                session_metadata, 
                pipeline_data, 
                topic_pages, 
                synthesis_insights,
                databases['learning_sessions']
            )
            
            if master_session_page:
                # Add memory-focused content using block builder
                session_story = self.content_enhancer._generate_session_story(pipeline_data, session_metadata)
                self.block_builder.add_memory_focused_master_content(
                    master_session_page['id'], 
                    session_story, 
                    pipeline_data, 
                    topic_pages
                )
            
            # Step 6: Update database relationships
            self.page_builder.update_enhanced_database_relationships(
                databases, topic_pages, concept_entries, master_session_page
            )
            
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
                        'modular_architecture',
                        'intelligent_topic_clustering',
                        'rich_content_generation', 
                        'cross_topic_synthesis',
                        'interactive_progress_tracking',
                        'memory_aids_integration'
                    ]
                },
                'session_page_url': self.page_builder.get_page_url(master_session_page),
                'notion_urls': {
                    'master_session': self.page_builder.get_page_url(master_session_page),
                    'topic_pages': {name: self.page_builder.get_page_url(page) for name, page in topic_pages.items()},
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
        """Post-processing: Store enhanced Notion results"""
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
            'enhancement_level': 'modular_architecture'
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

    # Helper methods that don't fit in other classes
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
            'technology': ('⚡', 'yellow'),
            'react': ('⚛️', 'blue'),
            'javascript': ('🟨', 'yellow'),
            'programming': ('💻', 'blue'),
            'web development': ('🌐', 'green'),
            'frontend': ('🎨', 'purple'),
            'hooks': ('⚛️', 'blue'),
            'state management': ('🔄', 'orange'),
            'performance': ('⚡', 'yellow'),
            'optimization': ('🚀', 'red')
        }
        
        for key, (emoji, color) in theme_map.items():
            if key in topic_lower:
                # Ensure emoji is properly encoded
                clean_emoji = str(emoji).encode('utf-8').decode('utf-8')
                return clean_emoji, color
        
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

    def _gap_relates_to_topic(self, gap: Dict[str, Any], topic_name: str) -> bool:
        """Check if a knowledge gap relates to a specific topic"""
        gap_concept = gap.get('missing_concept', '').lower()
        topic_keywords = topic_name.lower().split()
        
        return any(keyword in gap_concept for keyword in topic_keywords)