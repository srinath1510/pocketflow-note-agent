"""
NotionBlockBuilder - Create rich Notion content blocks
"""

import logging
from typing import Dict, List, Any
from .client import NotionClient
from ..llm_client import get_llm_client

class NotionBlockBuilder:
    """Create rich Notion content blocks and sections"""
    
    def __init__(self, notion_client: NotionClient):
        """Initialize with Notion client"""
        self.logger = logging.getLogger(__name__)
        self.notion_client = notion_client
        
        # Initialize LLM for enhanced content generation
        try:
            self.llm_client = get_llm_client()
            self.logger.info(f"LLM initialized for block content generation: {self.llm_client.get_provider_name()}")
        except Exception as e:
            self.logger.warning(f"LLM not available for enhanced block content: {str(e)}")
            self.llm_client = None
    
    def add_rich_topic_content(self, page_id: str, topic_name: str, topic_data: Dict[str, Any], 
                              pipeline_data: Dict[str, Any], color_theme: str):
        """Add memory-focused content to topic page"""
        rich_content = topic_data.get('rich_content', {})
        
        blocks = []
        
        # Hero section with learning story
        blocks.extend(self._create_topic_hero_with_story(topic_name, topic_data, rich_content, color_theme))
        
        # Visual concept cards for memory
        blocks.extend(self._create_visual_concept_cards_section(rich_content, topic_data))
        
        # Personal relevance section
        blocks.extend(self._create_personal_relevance_section(rich_content, topic_name))
        
        # Quick scan insights
        blocks.extend(self._create_topic_quick_scan(rich_content, topic_data))
        
        # Curiosity questions
        blocks.extend(self._create_topic_curiosity_questions(rich_content, topic_name))
        
        # Sources with context
        blocks.extend(self._create_contextual_sources_section(topic_data))
        
        # Spaced repetition schedule
        blocks.extend(self._create_spaced_review_section(rich_content))
        
        # Add all blocks to the page
        success = self.notion_client.add_blocks_to_page(page_id, blocks)
        
        if success:
            self.logger.info(f"Memory-focused topic content added: {topic_name}")
        else:
            self.logger.warning(f"Failed to add topic content '{topic_name}'")
    
    def add_memory_focused_master_content(self, page_id: str, session_story: Dict, 
                                         pipeline_data: Dict, topic_pages: Dict):
        """Add memory-focused content to master session page"""
        blocks = []
        
        # Hero section with session story
        blocks.extend(self._create_session_hero_section(session_story, pipeline_data))
        
        # Quick scan takeaways
        blocks.extend(self._create_quick_scan_section(pipeline_data, topic_pages))
        
        # Topic navigation with memory anchors
        blocks.extend(self._create_topic_navigation_section(topic_pages))
        
        # Questions that arose
        blocks.extend(self._create_curiosity_section(pipeline_data))
        
        # Knowledge connections found
        blocks.extend(self._create_connections_highlight(pipeline_data))
        
        # Strategic next steps
        blocks.extend(self._create_strategic_actions(pipeline_data))
        
        # Add all blocks to the page
        success = self.notion_client.add_blocks_to_page(page_id, blocks)
        
        if success:
            self.logger.info("Memory-focused master content added successfully")
        else:
            self.logger.warning("Failed to add master content")
    
    # Session-level block builders
    def _create_session_hero_section(self, session_story: Dict, pipeline_data: Dict) -> List[Dict]:
        """Create compelling hero section with session story"""
        blocks = []
        
        # Session title with story
        title = session_story.get('title', 'Learning Session')
        story = session_story.get('story', 'A journey of discovery and understanding.')
        
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": f"🧠 {title}"}}],
                "color": "blue"
            }
        })
        
        # Story callout
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": story}}],
                "icon": {"emoji": "✨"},
                "color": "blue_background"
            }
        })
        
        # What sparked this learning
        spark = session_story.get('spark', 'Intellectual curiosity')
        blocks.append({
            "object": "block",
            "type": "quote",
            "quote": {
                "rich_text": [{"type": "text", "text": {"content": f"🔥 What sparked this: {spark}"}}],
                "color": "orange"
            }
        })
        
        return blocks
    
    def _create_quick_scan_section(self, pipeline_data: Dict, topic_pages: Dict) -> List[Dict]:
        """Create scannable takeaways for quick recall"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "⚡ Quick Scan - Key Takeaways"}}]
            }
        })
        
        # Extract key insights
        concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        connections = pipeline_data.get('historical_connections', {}).get('total_connections_found', 0)
        
        takeaways = [
            f"🧠 Mastered {len(concepts)} new concepts across {len(topic_pages)} topics",
            f"🔗 Found {connections} connections to existing knowledge" if connections > 0 else None,
            f"💡 Key breakthrough: {concepts[0]}" if concepts else None,
            f"📚 Explored {len(topic_pages)} distinct knowledge areas"
        ]
        
        for takeaway in takeaways:
            if takeaway:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": takeaway}}]
                    }
                })
        
        return blocks
    
    def _create_topic_navigation_section(self, topic_pages: Dict) -> List[Dict]:
        """Create topic navigation with visual memory anchors"""
        blocks = []
        
        if not topic_pages:
            return blocks
            
        blocks.append({
            "object": "block",
            "type": "heading_2", 
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🗺️ Knowledge Areas Explored"}}]
            }
        })
        
        for topic_name, topic_page in topic_pages.items():
            topic_emoji, _ = self._get_topic_visual_theme(topic_name)
            topic_url = self._get_page_url(topic_page)
            
            if topic_url:
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"{topic_emoji} {topic_name}"}}  # FIX: Remove link
                        ],
                        "icon": {"emoji": topic_emoji},
                        "color": "gray_background"
                    }
                })
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": f"{topic_emoji} {topic_name}"}}]
                    }
                })
        
        return blocks
    
    def _create_curiosity_section(self, pipeline_data: Dict) -> List[Dict]:
        """Create section for questions that arose during learning"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🤔 Questions That Emerged"}}]
            }
        })
        
        # Generate curiosity questions based on concepts
        concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        
        if self.llm_client and self.llm_client.is_available():
            try:
                curiosity_prompt = f"""Generate 4 specific follow-up questions for: {', '.join(concepts[:8])}

Questions must:
- Be specific and actionable
- Point to practical applications
- Drive deeper learning
- Be answerable through research

Return only the questions, one per line."""

                messages = [
                    {"role": "system", "content": "Generate specific, actionable follow-up questions that drive practical learning."},
                    {"role": "user", "content": curiosity_prompt}
                ]
                    
                request_params = self.llm_client.set_provider_specific_defaults(temperature=0.3, max_tokens=300)
                response_text = self.llm_client.chat_completion(messages, **request_params)
                    
                # Parse questions from response
                questions = [q.strip('- ').strip() for q in response_text.split('\n') if q.strip() and '?' in q]
                
            except Exception as e:
                self.logger.warning(f"Curiosity question generation failed: {str(e)}")
                questions = self._generate_basic_curiosity_questions(concepts)
        else:
            questions = self._generate_basic_curiosity_questions(concepts)
        
        for question in questions[:4]:
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": question}}],
                    "icon": {"emoji": "🤔"},
                    "color": "purple_background"
                }
            })
        
        return blocks
    
    def _create_connections_highlight(self, pipeline_data):
        """Create knowledge connections highlight section"""
        blocks = []
        
        historical_connections = pipeline_data.get('historical_connections', {})
        connections_count = historical_connections.get('total_connections_found', 0)
        
        if connections_count > 0:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🔗 Knowledge Connections Found"}}]
                }
            })
            
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": f"Discovered {connections_count} connections to your existing knowledge, strengthening cross-domain understanding."}}],
                    "icon": {"emoji": "🌟"},
                    "color": "yellow_background"
                }
            })
        
        return blocks
    
    def _create_strategic_actions(self, pipeline_data: Dict) -> List[Dict]:
        """Create actionable next steps section"""
        blocks = []
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🎯 What to Do Next"}}]
            }
        })
        
        # Get recommendations from pipeline
        recommendations = pipeline_data.get('learning_recommendations', [])
        concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        
        # Create actionable steps
        actions = []
        
        # High priority actions from recommendations
        high_priority = [r for r in recommendations if r.get('priority') == 'high']
        for rec in high_priority[:2]:
            action = rec.get('action', rec.get('recommended_action', ''))
            if action:
                actions.append(f"🔥 {action}")
        
        # Practice/application actions
        if concepts:
            actions.append(f"🛠️ Practice applying {concepts[0]} in a real project")
            actions.append(f"👥 Teach {concepts[0]} to someone else to solidify understanding")
        
        # Review actions
        actions.append("📅 Schedule review of key concepts in 3 days")
        
        for action in actions[:5]:
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": action}}],
                    "checked": False
                }
            })
        
        return blocks
    
    # Topic-level block builders
    def _create_topic_hero_with_story(self, topic_name: str, topic_data: Dict, rich_content: Dict, color_theme: str) -> List[Dict]:
        """Create topic hero section with learning story"""
        blocks = []
        
        topic_emoji, _ = self._get_topic_visual_theme(topic_name)
        learning_story = rich_content.get('learning_story', f'Your exploration of {topic_name.lower()} concepts and applications.')
        
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": f"{topic_emoji} {topic_name}"}}],
                "color": "blue"
            }
        })
        
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": learning_story}}],
                "icon": {"emoji": "✨"},
                "color": f"{color_theme}_background"
            }
        })
        
        return blocks
    
    def _create_visual_concept_cards_section(self, rich_content: Dict, topic_data: Dict) -> List[Dict]:
        """Create visual concept cards for memory"""
        blocks = []
        
        concept_cards = rich_content.get('concept_cards', [])
        if not concept_cards:
            return blocks
        
        blocks.append({
            "object": "block", 
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🎴 Concept Memory Cards"}}]
            }
        })
        
        for card in concept_cards[:6]:
            # Safely extract concept information
            if isinstance(card, dict):
                concept = str(card.get('concept', 'Unknown')).strip()
                essence = str(card.get('essence', 'Key concept in this topic')).strip()
                memory_trigger = str(card.get('memory_trigger', f'Remember when thinking about {concept}')).strip()
            else:
                # Handle case where card is not a dict
                concept = str(card).strip()
                essence = 'Key concept in this topic'
                memory_trigger = f'Remember when thinking about {concept}'
            
            # Only create card if we have a valid concept name
            if concept and concept != 'Unknown':
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"💡 {concept}\n"}, "annotations": {"bold": True}},
                            {"type": "text", "text": {"content": f"{essence}\n\n"}},
                            {"type": "text", "text": {"content": f"🧠 Memory trigger: {memory_trigger}"}, "annotations": {"italic": True}}
                        ],
                        "icon": {"emoji": "💡"},
                        "color": "yellow_background"
                    }
                })
        
        return blocks
    
    def _create_personal_relevance_section(self, rich_content: Dict, topic_name: str) -> List[Dict]:
        """Create personal relevance section"""
        blocks = []
        
        personal_relevance = rich_content.get('personal_relevance', f'Understanding {topic_name.lower()} builds your expertise in this domain.')
        if isinstance(personal_relevance, dict):
            personal_relevance = str(personal_relevance.get('text', personal_relevance))
        personal_relevance = str(personal_relevance)
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🎯 Why This Matters to You"}}]
            }
        })
        
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": personal_relevance}}],
                "icon": {"emoji": "🎯"},
                "color": "green_background"
            }
        })
        
        return blocks
    
    def _create_topic_quick_scan(self, rich_content: Dict, topic_data: Dict) -> List[Dict]:
        """Create quick scan section for topic"""
        blocks = []
        
        quick_scan = rich_content.get('quick_scan_takeaways', [])
        if not quick_scan:
            # Generate from topic data
            concepts = topic_data.get('concepts', [])
            quick_scan = [
                f"💡 Learned {len(concepts)} key concepts",
                f"📚 From {len(topic_data.get('captures', []))} sources",
                f"🎯 Focus: {concepts[0] if concepts else 'Core principles'}"
            ]
        
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "⚡ Quick Scan"}}]
            }
        })
        
        for insight in quick_scan[:4]:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": insight}}]
                }
            })
        
        return blocks
    
    def _create_topic_curiosity_questions(self, rich_content: Dict, topic_name: str) -> List[Dict]:
        """Create curiosity questions section for topic"""
        blocks = []
        
        curiosity_questions = rich_content.get('curiosity_questions', [
            f"How does {topic_name.lower()} apply in different industries?",
            f"What are the cutting-edge developments in {topic_name.lower()}?",
            f"What challenges remain unsolved in {topic_name.lower()}?"
        ])
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🤔 Questions to Explore Further"}}]
            }
        })
        
        # Ensure questions are strings
        for question in curiosity_questions[:4]:
            question_text = str(question).strip() if question else f"What can I learn more about {topic_name.lower()}?"
            
            if question_text:  # Only add non-empty questions
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": question_text}}],
                        "icon": {"emoji": "🤔"},
                        "color": "purple_background"
                    }
                })
        
        return blocks
    
    def _create_contextual_sources_section(self, topic_data):
        """Create sources section with full content access"""
        blocks = []
        
        captures = topic_data.get('captures', [])
        if not captures:
            return blocks
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📖 Sources & Saved Content"}}]
            }
        })
        
        for capture in captures[:5]:  # Limit to 5 most important
            title = capture.get('title', 'Untitled Source')
            url = capture.get('url', '')
            content = capture.get('content', '')
            content_page_url = self._find_content_page_url(capture, content_pages)

            
            if url and url != 'unknown':
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"🔗 "}, "annotations": {"bold": True}},
                            {"type": "text", "text": {"content": title, "link": {"url": url}}, "annotations": {"bold": True}}
                        ]
                    }
                })
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"📄 {title}"}, "annotations": {"bold": True}}
                        ]
                    }
                })
            
            # Key excerpt (first 300 chars)
            excerpt = content[:300] + "..." if len(content) > 300 else content
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": excerpt}}],
                    "color": "gray"
                }
            })

            # Full content in toggle
            content_chunks = [content[i:i+1800] for i in range(0, len(content), 1800)]
            toggle_children = []
            
            for chunk in content_chunks:
                toggle_children.append({
                    "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            })
        
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": "📄 View Full Content"}}],
                    "children": toggle_children
                }
            })
            
            # Link to dedicated content page if available
            if content_page_url:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "📋 "}, "annotations": {"color": "blue"}},
                            {"type": "text", "text": {"content": "View in Content Database", "link": {"url": content_page_url}}, "annotations": {"color": "blue"}}
                        ]
                    }
                })
            
            # Add divider
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        
        return blocks

    
    def _find_content_page_url(self, capture: Dict, content_pages: List[Dict]) -> str:
        """Find URL for corresponding content page"""
        capture_title = capture.get('title', '')
        
        for page in content_pages:
            page_title = page.get('properties', {}).get('Content Title', {}).get('title', [{}])[0].get('plain_text', '')
            if capture_title == page_title:
                return self._get_page_url(page)
    
        return ""
    
    def _create_spaced_review_section(self, rich_content: Dict) -> List[Dict]:
        """Create spaced repetition review schedule"""
        blocks = []
        
        review_schedule = rich_content.get('spaced_review_schedule', {})
        if not review_schedule:
            return blocks
        
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📅 Spaced Review Schedule"}}]
            }
        })
        
        review_items = [
            ("1 day", review_schedule.get('review_in_1_day', [])),
            ("3 days", review_schedule.get('review_in_3_days', [])),
            ("1 week", review_schedule.get('review_in_1_week', []))
        ]
        
        for timing, concepts in review_items:
            if concepts:
                # Convert concepts to strings properly - handle both dict and string formats
                concept_list = []
                for c in concepts[:3]:  # Limit to 3 concepts
                    if isinstance(c, dict):
                        # If it's a dict, get the 'concept' key or convert to string
                        concept_name = c.get('concept', str(c))
                    elif isinstance(c, str):
                        concept_name = c
                    else:
                        concept_name = str(c)
                    
                    # Clean the concept name and ensure it's a string
                    clean_concept = str(concept_name).strip()
                    if clean_concept:  # Only add non-empty concepts
                        concept_list.append(clean_concept)
                
                # Only create the block if we have valid concepts
                if concept_list:
                    concept_text = ', '.join(concept_list)
                    blocks.append({
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": [{"type": "text", "text": {"content": f"📚 Review in {timing}: {concept_text}"}}],
                            "checked": False
                        }
                    })
        
        return blocks
    
    # Helper methods for curiosity questions
    def _generate_basic_curiosity_questions(self, concepts: List[str]) -> List[str]:
        """Generate basic curiosity questions when LLM unavailable"""
        if not concepts:
            return [
                "What should I explore next?", 
                "How can I apply this knowledge?",
                "What problems can this solve?",
                "Where is this used in practice?"
            ]
        
        questions = []
        for concept in concepts[:2]:  # Use first 2 concepts
            questions.extend([
                f"How is {concept} applied in industry?",
                f"What are the limitations of {concept}?"
            ])
        
        # Add general questions if we need more
        if len(questions) < 4:
            questions.extend([
                "What problems can I solve with this knowledge?",
                "How do these concepts connect to my goals?"
            ])
        
        return questions[:4]
    
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
    
    def _get_page_url(self, page: Dict[str, Any]) -> str:
        """Get Notion page URL"""
        if not page or 'id' not in page:
            return ""
        
        page_id = page['id'].replace('-', '')
        return f"https://notion.so/{page_id}"