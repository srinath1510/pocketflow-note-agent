"""
NotionPageBuilder - Build structured Notion pages
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
from .client import NotionClient

class NotionPageBuilder:
    """Build structured Notion pages with rich formatting"""
    
    def __init__(self, notion_client: NotionClient):
        """Initialize with Notion client and formatting templates"""
        self.logger = logging.getLogger(__name__)
        self.notion_client = notion_client
        self.formatting_templates = self._init_formatting_templates()
    
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
    
    def create_enhanced_topic_page(self, topic_name: str, enhanced_topic_data: Dict[str, Any], 
                                   rich_content: Dict[str, Any], topics_db_id: str, 
                                   pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced topic page with rich content"""
        try:
            self.logger.info(f"Creating topic page for: {topic_name}")

            learning_objectives = enhanced_topic_data.get('learning_objectives', [])
            self.logger.info(f"Learning objectives: {learning_objectives}, type: {type(learning_objectives)}")
            
            # Determine topic emoji and color theme
            topic_emoji, color_theme = self._get_topic_visual_theme(topic_name)
            self.logger.info(f"Topic emoji: {topic_emoji}, type: {type(topic_emoji)}")

            # Ensure all values are properly converted to strings and handle Unicode properly
            complexity = str(enhanced_topic_data.get('complexity', 'Intermediate')).title()
            learning_sequence = enhanced_topic_data.get('learning_sequence', ['Continue learning'])
            next_step = str(learning_sequence[0]) if learning_sequence else 'Continue learning'
            
            # Clean the emoji to avoid Unicode issues
            clean_emoji = str(topic_emoji).encode('utf-8').decode('utf-8') if topic_emoji else '📚'
            
            # Format the title properly - ensure clean string concatenation
            page_title = f"{clean_emoji} {str(topic_name)}"
            domain_name = str(self._classify_domain(topic_name))
            
            # Create database entry for topic with proper string formatting
            page_data = {
                "parent": {"database_id": str(topics_db_id)},
                "properties": {
                    "Topic Name": {
                        "title": [
                            {
                                "text": {
                                    "content": page_title
                                }
                            }
                        ]
                    },
                    "Domain": {
                        "select": {
                            "name": domain_name
                        }
                    },
                    "Complexity Level": {
                        "select": {
                            "name": complexity
                        }
                    },
                    "Learning Status": {
                        "select": {
                            "name": "Learning"
                        }
                    },
                    "First Encountered": {
                        "date": {
                            "start": datetime.now(timezone.utc).isoformat()
                        }
                    },
                    "Last Reviewed": {
                        "date": {
                            "start": datetime.now(timezone.utc).isoformat()
                        }
                    },
                    "Session Count": {
                        "number": 1
                    },
                    "Concepts Count": {
                        "number": len(enhanced_topic_data.get('concepts', []))
                    },
                    "Practical Applications": {
                        "number": len(enhanced_topic_data.get('practical_applications', []))
                    },
                    "Knowledge Gaps": {
                        "number": len([gap for gap in pipeline_data.get('knowledge_gaps', []) 
                                     if self._gap_relates_to_topic(gap, topic_name)])
                    },
                    "Next Steps": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": next_step
                                }
                            }
                        ]
                    }
                }
            }
            
            topic_page = self.notion_client.create_page(page_data)
            
            if topic_page:
                # Add rich content will be handled by BlockBuilder
                self.logger.info(f"Successfully created topic page for: {topic_name}")
            
            return topic_page
            
        except Exception as e:
            self.logger.error(f"Error creating topic page for '{topic_name}': {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    def create_enhanced_concept_library_entries(self, extracted_concepts: Dict[str, Any], 
                                               concepts_db_id: str, topic_organization: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create enhanced concept library entries"""
        entries = []
        learning_concepts = extracted_concepts.get('learning_concepts', [])
        key_terms = extracted_concepts.get('key_terms', {})
        
        for concept in learning_concepts:
            try:
                # Find which topic this concept belongs to
                topic_name = 'General'
                for t_name, t_data in topic_organization.items():
                    if concept in t_data.get('concepts', []):
                        topic_name = t_name
                        break
                
                # Get definition quality based on key_terms
                definition_quality = "Clear" if concept in key_terms else "Partial"
                
                # Ensure all values are properly formatted as strings
                entry_data = {
                    "parent": {"database_id": str(concepts_db_id)},
                    "properties": {
                        "Concept Name": {
                            "title": [
                                {
                                    "text": {
                                        "content": str(concept)
                                    }
                                }
                            ]
                        },
                        "Topic": {
                            "select": {
                                "name": str(topic_name)
                            }
                        },
                        "Definition Quality": {
                            "select": {
                                "name": str(definition_quality)
                            }
                        },
                        "Understanding Level": {
                            "select": {
                                "name": "Functional"
                            }
                        },
                        "Confidence Score": {
                            "number": 75 if definition_quality == "Clear" else 60
                        },
                        "First Learned": {
                            "date": {
                                "start": datetime.now(timezone.utc).isoformat()
                            }
                        },
                        "Times Encountered": {
                            "number": 1
                        }
                    }
                }
                
                entry = self.notion_client.create_page(entry_data)
                
                if entry:
                    # Add concept content if available
                    if concept in key_terms:
                        self.add_concept_content(entry['id'], concept, key_terms[concept])
                    entries.append(entry)
                    
            except Exception as e:
                self.logger.error(f"Error creating concept entry for {concept}: {str(e)}")
                continue
        
        return entries
    
    def create_enhanced_master_session_page(self, session_metadata: Dict[str, Any], 
                                           pipeline_data: Dict[str, Any], topic_pages: Dict[str, Any], 
                                           synthesis_insights: Dict[str, Any], sessions_db_id: str) -> Dict[str, Any]:
        """Create enhanced master session page"""
        
        try:
            # Generate session story for memory reconstruction
            session_story = self._generate_session_story(pipeline_data, session_metadata)
            session_theme = pipeline_data['extracted_concepts'].get('session_theme', 'Knowledge Exploration')
            
            session_title = session_story.get('title', session_theme.replace('_', ' ').title())
            primary_theme = session_theme.replace('_', ' ').title()
            knowledge_level = str(session_metadata['knowledge_level'])
            
            # Safely create multi_select values - limit to 10 and ensure strings
            topics_covered = []
            for topic in list(topic_pages.keys())[:10]:  # Limit to 10 topics
                # Clean topic name for Notion
                clean_topic = str(topic).strip()
                if clean_topic:  # Only add non-empty topics
                    topics_covered.append({"name": clean_topic})
            
            page_data = {
                "parent": {"database_id": str(sessions_db_id)},
                "properties": {
                    "Session Title": {
                        "title": [
                            {
                                "text": {
                                    "content": f"🧠 {str(session_title)}"
                                }
                            }
                        ]
                    },
                    "Date": {
                        "date": {
                            "start": session_metadata['timestamp']
                        }
                    },
                    "Topics Covered": {
                        "multi_select": topics_covered
                    },
                    "Primary Theme": {
                        "select": {
                            "name": str(primary_theme)
                        }
                    },
                    "Knowledge Level": {
                        "select": {
                            "name": knowledge_level
                        }
                    },
                    "Topics Count": {
                        "number": len(topic_pages)
                    },
                    "Concepts Count": {
                        "number": session_metadata['total_concepts']
                    },
                    "Cross-References": {
                        "number": pipeline_data.get('historical_connections', {}).get('total_connections_found', 0)
                    },
                    "Completion Status": {
                        "select": {
                            "name": "Completed"
                        }
                    }
                }
            }
            
            master_page = self.notion_client.create_page(page_data)
            
            if master_page:
                self.logger.info("Successfully created master session page")
            
            return master_page
                
        except Exception as e:
            self.logger.error(f"Error creating master session page: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    def update_enhanced_database_relationships(self, databases: Dict[str, str], 
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
                            properties = {
                                "From Topics": {
                                    "relation": [{"id": topic_page.get('id')}]
                                }
                            }
                            self.notion_client.update_page_properties(concept_id, properties)
            
            self.logger.info("Enhanced database relationships updated")
        except Exception as e:
            self.logger.warning(f"Failed to update enhanced database relationships: {str(e)}")
    
    def add_concept_content(self, page_id: str, concept_name: str, definition: str):
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
        
        self.notion_client.add_blocks_to_page(page_id, blocks)
    
    def get_page_url(self, page: Dict[str, Any]) -> str:
        """Get Notion page URL"""
        if not page or 'id' not in page:
            return ""
        
        page_id = page['id'].replace('-', '')
        return f"https://notion.so/{page_id}"
    
    # Helper methods
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
    
    def _gap_relates_to_topic(self, gap: Dict[str, Any], topic_name: str) -> bool:
        """Check if a knowledge gap relates to a specific topic"""
        gap_concept = gap.get('missing_concept', '').lower()
        topic_keywords = topic_name.lower().split()
        
        return any(keyword in gap_concept for keyword in topic_keywords)
    
    def _generate_session_story(self, pipeline_data: Dict, session_metadata: Dict) -> Dict[str, Any]:
        """Generate basic session story"""
        concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        theme = pipeline_data['extracted_concepts'].get('session_theme', 'exploration')
        
        return {
            'title': f"Deep Dive: {theme.replace('_', ' ').title()}",
            'story': f"You explored {theme.replace('_', ' ')} by diving into {len(concepts)} key concepts. This session built your understanding through practical examples and real-world applications.",
            'spark': f"Curiosity about {theme.replace('_', ' ')}",
            'breakthrough': f"Understanding how {concepts[0] if concepts else 'core concepts'} work in practice"
        }

    def create_content_pages(self, raw_captures: List[Dict], content_db_id: str, 
                        topic_organization: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create content pages in the captured content database"""
        content_pages = []
        
        for capture in raw_captures:
            try:
                # Determine content type
                content_type = self._classify_content_type(capture)
                
                # Get related topics
                related_topics = []
                for topic_name, topic_data in topic_organization.items():
                    if capture in topic_data.get('captures', []):
                        related_topics.append({"name": str(topic_name)})
                
                # Create content page
                page_data = {
                    "parent": {"database_id": str(content_db_id)},
                    "properties": {
                        "Content Title": {
                            "title": [{"text": {"content": str(capture.get('title', 'Untitled'))}}]
                        },
                        "Source URL": {
                            "url": capture.get('url') if capture.get('url') != 'unknown' else None
                        },
                        "Capture Date": {
                            "date": {"start": capture.get('metadata', {}).get('timestamp', 
                                    datetime.now(timezone.utc).isoformat())}
                        },
                        "Content Type": {
                            "select": {"name": content_type}
                        },
                        "Word Count": {
                            "number": len(capture.get('content', '').split())
                        },
                        "Related Topics": {
                            "multi_select": related_topics[:10]  # Limit to 10
                        },
                        "Content Preview": {
                            "rich_text": [{"text": {"content": capture.get('content', '')[:2000]}}]
                        },
                        "Processing Status": {
                            "select": {"name": "Captured"}
                        }
                    }
                }
                
                content_page = self.notion_client.create_page(page_data)
                
                if content_page:
                    # Add full content as blocks
                    self._add_full_content_blocks(content_page['id'], capture)
                    content_pages.append(content_page)
                    
            except Exception as e:
                self.logger.error(f"Error creating content page for {capture.get('title', 'Unknown')}: {str(e)}")
                continue
        
        return content_pages

    def _classify_content_type(self, capture: Dict) -> str:
        """Classify content type based on URL patterns, content analysis, and metadata"""
        url = capture.get('url', '').lower()
        content = capture.get('content', '').lower()
        title = capture.get('title', '').lower()
        metadata = capture.get('metadata', {})
        
        # Get domain for analysis
        domain = metadata.get('domain', '')
        
        # Scoring system for flexible classification
        scores = {
            'Tutorial': 0,
            'Documentation': 0, 
            'Research Paper': 0,
            'Blog Post': 0,
            'Article': 0
        }
        
        # Tutorial indicators
        tutorial_signals = [
            ('tutorial', 3), ('how to', 3), ('step by step', 3), ('guide', 2),
            ('walkthrough', 2), ('getting started', 2), ('learn', 1), ('build', 1),
            ('create', 1), ('example', 1), ('demo', 1)
        ]
        
        # Documentation indicators
        docs_signals = [
            ('docs.', 4), ('documentation', 3), ('api reference', 4), ('spec', 2),
            ('manual', 2), ('reference', 2), ('installation', 2), ('usage', 1),
            ('configuration', 1), ('parameters', 1)
        ]
        
        # Research paper indicators
        research_signals = [
            ('arxiv', 4), ('doi:', 4), ('abstract', 3), ('methodology', 3),
            ('literature review', 3), ('research', 2), ('study', 2), ('analysis', 1),
            ('experiment', 2), ('findings', 2), ('conclusion', 1), ('references', 1)
        ]
        
        # Blog post indicators  
        blog_signals = [
            ('blog', 3), ('medium.com', 3), ('dev.to', 3), ('hashnode', 3),
            ('substack', 3), ('posted by', 2), ('author:', 2), ('published', 1),
            ('opinion', 2), ('thoughts on', 2), ('my experience', 2)
        ]
        
        # Article indicators (more general content)
        article_signals = [
            ('news', 2), ('report', 2), ('interview', 2), ('analysis', 1),
            ('overview', 1), ('introduction', 1), ('explained', 1)
        ]
        
        # Score each type based on signals found
        all_signals = [
            ('Tutorial', tutorial_signals),
            ('Documentation', docs_signals), 
            ('Research Paper', research_signals),
            ('Blog Post', blog_signals),
            ('Article', article_signals)
        ]
        
        # Check URL, title, and content for signals
        text_sources = [url, title, content[:1000]]  # Limit content check for performance
        
        for content_type, signals in all_signals:
            for signal, weight in signals:
                for text_source in text_sources:
                    if signal in text_source:
                        scores[content_type] += weight
        
        # Domain-specific boosters
        domain_boosts = {
            'github.io': {'Documentation': 2, 'Tutorial': 1},
            'readthedocs.io': {'Documentation': 3},
            'stackoverflow.com': {'Tutorial': 2, 'Article': 1},
            'wikipedia.org': {'Article': 2},
            'youtube.com': {'Tutorial': 2},
            'coursera.org': {'Tutorial': 3},
            'udemy.com': {'Tutorial': 3},
            'khan academy': {'Tutorial': 3}
        }
        
        for domain_pattern, boosts in domain_boosts.items():
            if domain_pattern in domain or domain_pattern in url:
                for content_type, boost in boosts.items():
                    scores[content_type] += boost
        
        # Content structure analysis
        content_words = content.split()
        word_count = len(content_words)
        
        # Research papers tend to be longer and more structured
        if word_count > 3000:
            scores['Research Paper'] += 1
        elif word_count > 1500:
            scores['Article'] += 1
        
        # Look for code blocks (indicates tutorial/documentation)
        if '```' in content or '<code>' in content or 'def ' in content:
            scores['Tutorial'] += 2
            scores['Documentation'] += 1
        
        # Look for academic formatting
        if any(term in content for term in ['et al.', 'fig.', 'table ', '[1]', '[2]']):
            scores['Research Paper'] += 2
        
        # Personal language indicates blog post
        if any(term in content for term in ['i think', 'in my opinion', 'i believe', 'my experience']):
            scores['Blog Post'] += 2
        
        # Find the highest scoring type
        best_type = max(scores.items(), key=lambda x: x[1])
        
        # If no clear winner (all scores are low), default based on context
        if best_type[1] < 3:
            # Use simple fallbacks
            if 'blog' in url or 'medium' in url:
                return 'Blog Post'
            elif 'docs' in url:
                return 'Documentation' 
            elif word_count > 2000:
                return 'Article'
            else:
                return 'General'
        
        return best_type[0]


    def _add_full_content_blocks(self, page_id: str, capture: Dict):
        """Add full content to content page"""
        content = capture.get('content', '')
        
        blocks = [
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": "📄 Full Content"}}]
                }
            }
        ]
        
        # Split content into chunks (Notion 2000 char limit per block)
        chunk_size = 1800
        content_chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        
        for chunk in content_chunks:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            })
        
        self.notion_client.add_blocks_to_page(page_id, blocks)