"""
ContentEnhancer - Generate enhanced content with LLM
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
from ..llm_client import get_llm_client

class ContentEnhancer:
    """Generate rich, memory-focused content using LLM"""
    
    def __init__(self):
        """Initialize with LLM client for content enhancement"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM for minimal enhancement calls
        try:
            self.llm_client = get_llm_client()
            self.logger.info(f"LLM initialized for enhanced content generation: {self.llm_client.get_provider_name()}")
        except Exception as e:
            self.logger.warning(f"LLM not available for enhanced features: {str(e)}")
            self.llm_client = None
    
    def generate_rich_topic_content(self, topic_data: Dict, user_context: Dict) -> Dict[str, Any]:
        """Generate memory-focused content that helps users recollect their learning journey"""
        if not self.llm_client or not self.llm_client.is_available():
            return self._generate_memory_focused_content_basic(topic_data, user_context)
    
        try:
            topic_name = topic_data['topic_name']
            concepts = topic_data['concepts'][:8]
            captures = topic_data.get('captures', [])
        
            # Single strategic LLM call for memory-focused content
            memory_prompt = f"""Generate practical learning content for: {topic_name}

CONTEXT:
- Concepts: {', '.join(concepts)}
- Level: {user_context.get('knowledge_level', 'intermediate')}
- Sources: {len(captures)}

Create:
1. LEARNING_STORY: One clear sentence explaining what you learned about {topic_name}
2. CONCEPT_CARDS: For each concept, provide: concept name, one-line definition, practical use
3. CURIOSITY_QUESTIONS: 3 specific questions to explore next
4. PERSONAL_RELEVANCE: One sentence on why this matters practically

Return JSON: {{"learning_story": "...", "concept_cards": [...], "curiosity_questions": [...], "personal_relevance": "..."}}"""

            messages = [
                {"role": "system", "content": "Generate practical, actionable learning content. Be concise and specific. Focus on what users can apply immediately."},
                {"role": "user", "content": memory_prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(temperature=0.4, max_tokens=1800)
            response_text = self.llm_client.chat_completion(messages, **request_params)
            memory_content = json.loads(response_text)
        
            # Enhance with visual elements
            return self._add_memory_aids(memory_content, topic_data)
        
        except Exception as e:
            self.logger.warning(f"Memory-focused content generation failed: {str(e)}")
            return self._generate_memory_focused_content_basic(topic_data, user_context)
    
    def _generate_session_story(self, pipeline_data: Dict, session_metadata: Dict) -> Dict[str, Any]:
        """Generate compelling session narrative for memory reconstruction"""
        if not self.llm_client or not self.llm_client.is_available():
            return self._create_basic_session_story(pipeline_data, session_metadata)
        
        try:
            concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
            session_theme = pipeline_data['extracted_concepts'].get('session_theme', 'exploration')
            
            story_prompt = f"""Create a concise learning session summary:

SESSION: {session_theme}
CONCEPTS: {', '.join(concepts[:8])}
LEVEL: {session_metadata['knowledge_level']}

Generate:
- TITLE: Clear session name (5 words max)
- STORY: One sentence describing what was learned
- SPARK: What triggered this learning
- BREAKTHROUGH: Key insight gained

Return JSON: {{"title": "...", "story": "...", "spark": "...", "breakthrough": "..."}}"""

            messages = [
                {"role": "system", "content": "Create clear, memorable learning summaries. Be direct and specific about what was learned."},
                {"role": "user", "content": story_prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(temperature=0.4, max_tokens=400)
            response_text = self.llm_client.chat_completion(messages, **request_params)
            return json.loads(response_text)
            
        except Exception as e:
            self.logger.warning(f"Session story generation failed: {str(e)}")
            return self._create_basic_session_story(pipeline_data, session_metadata)
    
    def _create_master_session_synthesis(self, all_topics: Dict, synthesis_insights: Dict, pipeline_data: Dict) -> Dict[str, Any]:
        """Create comprehensive master session page with novel insights"""
        if not self.llm_client or not self.llm_client.is_available():
            return self._create_basic_master_synthesis(all_topics, pipeline_data)
        
        try:
            # Prepare synthesis data
            topic_summary = {name: {
                'concepts': data['concepts'][:5],
                'complexity': data.get('complexity', 'intermediate'),
                'connections': data.get('cross_topic_connections', [])
            } for name, data in all_topics.items()}
            
            synthesis_prompt = f"""Synthesize this multi-topic learning session:

TOPICS: {json.dumps(topic_summary, indent=2)}
CONNECTIONS: {pipeline_data.get('historical_connections', {}).get('total_connections_found', 0)}
GAPS: {len(pipeline_data.get('knowledge_gaps', []))}

Generate:
1. SESSION_OVERVIEW: Main theme and key insights (2 sentences)
2. TOPIC_RELATIONSHIPS: How topics connect (3 key connections)
3. STRATEGIC_NEXT_STEPS: 3 specific actions to take
4. KNOWLEDGE_INTEGRATION: How to apply learnings together

Return JSON with session_overview, topic_relationship_map, strategic_next_steps, knowledge_integration."""

            messages = [
                {"role": "system", "content": "Create actionable learning synthesis. Focus on practical connections and next steps."},
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
    
    def _enhance_topics_with_llm(self, topic_organization: Dict[str, Any], pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance topics with a single strategic LLM call"""
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

        prompt = f"""Enhance these learning topics with practical details:

TOPICS: {json.dumps(topics_summary, indent=2)}
SESSION_THEME: {pipeline_data['extracted_concepts'].get('session_theme', 'general')}
LEVEL: {self._assess_session_knowledge_level(pipeline_data)}

For each topic, provide:
- enhanced_description: One clear sentence explaining the topic
- learning_outcomes: 3 specific skills/knowledge gained
- practical_applications: 3 ways to apply this knowledge
- key_insights: 2 main takeaways

Return JSON: {{"topic_name": {{"enhanced_description": "...", "learning_outcomes": [...], "practical_applications": [...], "key_insights": [...]}}}}"""

        try:
            messages = [
                {"role": "system", "content": "Enhance learning topics with practical, actionable details. Be specific about outcomes and applications."},
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
    
    def _generate_memory_focused_content_basic(self, topic_data: Dict, user_context: Dict) -> Dict[str, Any]:
        """Basic memory-focused content when LLM unavailable"""
        topic_name = str(topic_data.get('topic_name', 'Topic'))
        concepts = topic_data.get('concepts', [])
        
        # Ensure concepts are strings
        clean_concepts = []
        for concept in concepts:
            if isinstance(concept, str):
                clean_concepts.append(concept.strip())
            else:
                clean_concepts.append(str(concept).strip())
        
        # Remove empty concepts
        clean_concepts = [c for c in clean_concepts if c]
        
        concept_cards = []
        for concept in clean_concepts[:5]:
            concept_cards.append({
                'concept': concept,
                'essence': f"{concept} is a fundamental building block in {topic_name.lower()}",
                'memory_trigger': f"Think of {concept} when you see {topic_name.lower()} applications",
                'personal_relevance': f"Useful for understanding {topic_name.lower()} systems"
            })
        
        curiosity_questions = []
        for concept in clean_concepts[:3]:
            curiosity_questions.append(f"How does {concept} work in practice?")
        
        if not curiosity_questions:
            curiosity_questions = [f"What problems does {topic_name.lower()} solve?"]
        
        return {
            'learning_story': f"You dove into {topic_name.lower()} to understand {clean_concepts[0] if clean_concepts else 'key concepts'}. This builds on your {user_context.get('session_theme', 'general')} learning journey.",
            'concept_cards': concept_cards,
            'curiosity_questions': curiosity_questions,
            'personal_relevance': f"Understanding {topic_name.lower()} helps you build expertise in this domain"
        }
    
    def _add_memory_aids(self, memory_content: Dict, topic_data: Dict) -> Dict[str, Any]:
        """Add visual and structural memory aids"""
        # Get topic visual theme
        topic_emoji, color_theme = self._get_topic_visual_theme(topic_data['topic_name'])
        
        # Safely get concept cards
        concept_cards = memory_content.get('concept_cards', [])
        
        # Ensure concept cards are properly formatted
        formatted_concept_cards = []
        for card in concept_cards:
            if isinstance(card, dict):
                formatted_concept_cards.append({
                    'concept': str(card.get('concept', 'Unknown')),
                    'essence': str(card.get('essence', 'Key concept')),
                    'memory_trigger': str(card.get('memory_trigger', 'Important concept'))
                })
            elif isinstance(card, str):
                formatted_concept_cards.append({
                    'concept': str(card),
                    'essence': 'Key concept in this topic',
                    'memory_trigger': f'Remember when studying {topic_data["topic_name"]}'
                })
        
        memory_content.update({
            'visual_theme': {
                'emoji': str(topic_emoji),
                'color': str(color_theme),
                'memory_anchor': f"{topic_emoji} {topic_data['topic_name']}"
            },
            'quick_scan_takeaways': self._extract_scannable_insights(topic_data),
            'spaced_review_schedule': {
                'review_in_1_day': formatted_concept_cards[:2],
                'review_in_3_days': formatted_concept_cards[2:4],
                'review_in_1_week': formatted_concept_cards[4:6]
            },
            'concept_cards': formatted_concept_cards  # Update with properly formatted cards
        })
        
        return memory_content
    
    def _extract_scannable_insights(self, topic_data: Dict) -> List[str]:
        """Extract 3-5 bullet points for 10-second scanning"""
        concepts = topic_data.get('concepts', [])
        captures = topic_data.get('captures', [])
    
        insights = []
        if concepts:
            insights.append(f"🧠 Mastered {len(concepts)} core concepts in {topic_data['topic_name']}")
        if captures:
            insights.append(f"📚 Explored {len(captures)} quality sources")
    
        # Add concept-specific insights
        for concept in concepts[:3]:
            insights.append(f"💡 Understood how {concept} works")
    
        return insights[:5]
    
    def _create_basic_session_story(self, pipeline_data: Dict, session_metadata: Dict) -> Dict[str, Any]:
        """Create basic session story when LLM unavailable"""
        concepts = pipeline_data['extracted_concepts'].get('learning_concepts', [])
        theme = pipeline_data['extracted_concepts'].get('session_theme', 'exploration')
        
        return {
            'title': f"Deep Dive: {theme.replace('_', ' ').title()}",
            'story': f"You explored {theme.replace('_', ' ')} by diving into {len(concepts)} key concepts. This session built your understanding through practical examples and real-world applications.",
            'spark': f"Curiosity about {theme.replace('_', ' ')}",
            'breakthrough': f"Understanding how {concepts[0] if concepts else 'core concepts'} work in practice"
        }
    
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