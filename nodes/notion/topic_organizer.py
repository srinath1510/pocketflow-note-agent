"""
TopicOrganizer - Organize content into topics
"""

import json
import logging
from typing import Dict, List, Any
from collections import defaultdict
from ..llm_client import get_llm_client

class TopicOrganizer:
    """Organize content into coherent topics using LLM and rule-based methods"""
    
    def __init__(self):
        """Initialize with LLM client and topic indicators"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM for topic clustering
        try:
            self.llm_client = get_llm_client()
            self.logger.info(f"LLM initialized for topic clustering: {self.llm_client.get_provider_name()}")
        except Exception as e:
            self.logger.warning(f"LLM not available for topic clustering: {str(e)}")
            self.llm_client = None
        
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
    
    def intelligent_topic_clustering(self, captures: List[Dict], learning_concepts: List[str]) -> Dict[str, Any]:
        """Enhanced semantic clustering using LLM analysis"""
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
    
    def _identify_topics_from_content(self, raw_captures: List[Dict], learning_concepts: List[str]) -> Dict[str, Any]:
        """Identify topics using rule-based analysis of content and concepts"""
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