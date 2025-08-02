"""
Historical Knowledge Retrieval Node: Connects new learning to existing knowledge base
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
import statistics

from neo4j.exceptions import ServiceUnavailable
from pocketflow import Node as BaseNode
from .llm_client import get_llm_client


class HistoricalKnowledgeRetrievalNode(BaseNode):
    """
    Node 4: Historical Knowledge Retrieval
    
    Purpose: Connect new concepts to existing knowledge and identify learning patterns
    
    Input: extracted_concepts + knowledge_graph from previous nodes
    Process: Query knowledge graph for connections, gaps, and reinforcement opportunities
    Output: historical_connections, knowledge_gaps, learning_insights
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM for semantic analysis
        self.llm_client = None
        self._initialize_llm()
        
        # Knowledge retrieval parameters
        self.connection_threshold = 0.3  # Minimum similarity for connections
        self.recency_weight = 0.7       # Weight for recent vs old knowledge
        self.max_connections = 10       # Max connections to return per concept
        
    def _initialize_llm(self):
        """Initialize LLM client for semantic analysis"""
        try:
            self.llm_client = get_llm_client()
            self.logger.info(f"LLM initialized for historical analysis: {self.llm_client.get_provider_name()}")
        except Exception as e:
            self.logger.warning(f"LLM not available for semantic analysis: {str(e)}")
            
    def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare for historical knowledge retrieval
        """
        self.logger.info("Starting Historical Knowledge Retrieval prep phase")
        
        # Get current session data
        user_id = shared_state.get('session_id', 'default_user')
        current_concepts = shared_state.get('extracted_concepts', {})
        knowledge_graph = shared_state.get('knowledge_graph', {})
        
        if not current_concepts:
            self.logger.warning("No extracted concepts found for historical analysis")
            return {'error': 'No concepts to analyze historically', 'user_id': user_id}
        
        # Get Neo4j driver from knowledge graph node
        neo4j_config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j', 
            'password': 'smartnotes123'
        }
        
        prep_data = {
            'user_id': user_id,
            'current_session_id': shared_state.get('session_id'),
            'new_concepts': current_concepts.get('learning_concepts', []),
            'new_entities': current_concepts.get('entities', {}),
            'new_topics': current_concepts.get('topics', []),
            'session_theme': current_concepts.get('session_theme', 'general'),
            'knowledge_progression': current_concepts.get('knowledge_progression', []),
            'neo4j_config': neo4j_config,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.logger.info(f"Prepared historical analysis for {len(prep_data['new_concepts'])} new concepts")
        return prep_data
    
    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution: Analyze historical connections and patterns
        """
        if 'error' in prep_result:
            return prep_result
            
        self.logger.info("Starting Historical Knowledge Retrieval core execution")
        
        user_id = prep_result['user_id']
        new_concepts = prep_result['new_concepts']
        
        try:
            # Import here to avoid circular dependencies
            from neo4j import GraphDatabase
            
            driver = GraphDatabase.driver(
                prep_result['neo4j_config']['uri'],
                auth=(prep_result['neo4j_config']['user'], prep_result['neo4j_config']['password'])
            )
            
            with driver.session() as session:
                # 1. Find direct concept connections
                direct_connections = self._find_direct_connections(session, user_id, new_concepts)
                
                # 2. Find semantic similarities 
                semantic_connections = self._find_semantic_connections(session, user_id, new_concepts)
                
                # 3. Identify knowledge gaps
                knowledge_gaps = self._identify_knowledge_gaps(session, user_id, new_concepts, prep_result)
                
                # 4. Find reinforcement opportunities
                reinforcement_opportunities = self._find_reinforcement_opportunities(session, user_id, new_concepts)
                
                # 5. Analyze learning patterns
                learning_patterns = self._analyze_learning_patterns(session, user_id, prep_result)
                
                # 6. Calculate knowledge confidence scores
                confidence_scores = self._calculate_confidence_scores(session, user_id, new_concepts)
                
                # 7. Generate learning recommendations
                recommendations = self._generate_learning_recommendations(
                    direct_connections, semantic_connections, knowledge_gaps, 
                    reinforcement_opportunities, learning_patterns
                )
            
            driver.close()
            
            return {
                'user_id': user_id,
                'session_id': prep_result['current_session_id'],
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'direct_connections': direct_connections,
                'semantic_connections': semantic_connections,
                'knowledge_gaps': knowledge_gaps,
                'reinforcement_opportunities': reinforcement_opportunities,
                'learning_patterns': learning_patterns,
                'confidence_scores': confidence_scores,
                'recommendations': recommendations,
                'historical_analysis_complete': True
            }
            
        except ServiceUnavailable:
            self.logger.error("Neo4j not available for historical analysis")
            return {'error': 'Neo4j database not available'}
        except Exception as e:
            self.logger.error(f"Historical analysis failed: {str(e)}")
            return {'error': f"Historical analysis failed: {str(e)}"}
    
    def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """
        Post-processing: Store historical analysis results
        """
        self.logger.info("Historical Knowledge Retrieval post-execution phase")
        
        if 'error' in exec_result:
            shared_state['historical_analysis_error'] = exec_result['error']
            return "error"
        
        # Store results in shared_state
        shared_state['historical_connections'] = {
            'direct_connections': exec_result['direct_connections'],
            'semantic_connections': exec_result['semantic_connections'],
            'total_connections_found': len(exec_result['direct_connections']) + len(exec_result['semantic_connections'])
        }
        
        shared_state['knowledge_gaps'] = exec_result['knowledge_gaps']
        shared_state['reinforcement_opportunities'] = exec_result['reinforcement_opportunities']
        shared_state['learning_patterns'] = exec_result['learning_patterns']
        shared_state['knowledge_confidence'] = exec_result['confidence_scores']
        shared_state['learning_recommendations'] = exec_result['recommendations']
        
        # Update pipeline metadata
        shared_state['pipeline_metadata']['historical_analysis_complete'] = True
        shared_state['pipeline_metadata']['historical_analysis_summary'] = {
            'connections_found': len(exec_result['direct_connections']) + len(exec_result['semantic_connections']),
            'knowledge_gaps_identified': len(exec_result['knowledge_gaps']),
            'reinforcement_opportunities': len(exec_result['reinforcement_opportunities']),
            'learning_patterns_detected': len(exec_result['learning_patterns'])
        }
        
        self.logger.info("Historical knowledge analysis complete")
        return "default"
    
    def _find_direct_connections(self, session, user_id: str, new_concepts: List[str]) -> List[Dict[str, Any]]:
        """Find direct relationships to existing concepts in the knowledge graph"""
        connections = []
        
        for concept in new_concepts:
            # Find existing concepts with similar names or direct relationships
            result = session.run("""
                MATCH (c:Concept {user_id: $user_id})
                WHERE c.name CONTAINS $concept_part OR $concept_part CONTAINS c.name
                OR c.name =~ '(?i).*' + $concept_part + '.*'
                WITH c, 
                     CASE 
                         WHEN c.name = $concept THEN 1.0
                         WHEN c.name CONTAINS $concept OR $concept CONTAINS c.name THEN 0.8
                         ELSE 0.6
                     END as similarity
                WHERE similarity > 0.5
                
                OPTIONAL MATCH (c)-[r]-(related:Concept {user_id: $user_id})
                OPTIONAL MATCH (c)<-[:CONTAINS_CONCEPT]-(s:Session {user_id: $user_id})
                
                RETURN c.name as existing_concept,
                       c.occurrence_count as frequency,
                       c.created_at as first_seen,
                       c.last_seen as last_seen,
                       similarity,
                       collect(DISTINCT related.name)[..5] as related_concepts,
                       count(DISTINCT s) as session_count
                ORDER BY similarity DESC, frequency DESC
                LIMIT 5
            """, user_id=user_id, concept=concept, concept_part=concept.lower())
            
            for record in result:
                connection = {
                    'new_concept': concept,
                    'existing_concept': record['existing_concept'],
                    'similarity_score': record['similarity'],
                    'frequency': record['frequency'],
                    'first_encountered': record['first_seen'],
                    'last_encountered': record['last_seen'],
                    'related_concepts': record['related_concepts'],
                    'session_count': record['session_count'],
                    'connection_type': 'direct_match'
                }
                connections.append(connection)
        
        self.logger.info(f"Found {len(connections)} direct connections")
        return connections
    
    def _find_semantic_connections(self, session, user_id: str, new_concepts: List[str]) -> List[Dict[str, Any]]:
        """Find semantic connections using LLM analysis"""
        if not self.llm_client or not self.llm_client.is_available():
            self.logger.warning("LLM not available for semantic analysis")
            return []
        
        semantic_connections = []
        
        # Get existing concepts for semantic comparison
        existing_concepts_result = session.run("""
            MATCH (c:Concept {user_id: $user_id})
            WHERE c.occurrence_count > 1  // Focus on well-established concepts
            RETURN c.name as concept, c.occurrence_count as frequency
            ORDER BY frequency DESC
            LIMIT 50
        """, user_id=user_id)

        if not existing_concepts_result:
            return []
        
        existing_concepts = [record['concept'] for record in existing_concepts_result if record and 'concept' in record]
        
        if not existing_concepts:
            return []
        
        # Use LLM to find semantic relationships
        for new_concept in new_concepts:
            prompt = f"""Analyze the semantic relationship between the new concept "{new_concept}" and these existing concepts:

Existing concepts: {', '.join(existing_concepts[:20])}

For each existing concept that has a meaningful relationship to "{new_concept}", return JSON with:
- "existing_concept": the existing concept name
- "relationship_type": one of [prerequisite, builds_upon, related_field, complementary, example_of, generalization_of, tool_for, applied_in]  
- "strength": float 0.0-1.0 indicating relationship strength
- "explanation": brief explanation of the relationship

Only include relationships with strength >= 0.4. Return as a JSON array. Maximum 5 relationships."""

            try:
                messages = [
                    {"role": "system", "content": "You are an expert at identifying semantic relationships between learning concepts. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ]
                
                request_params = self.llm_client.set_provider_specific_defaults(
                    temperature=0.2,
                    max_tokens=600
                )
                
                response_text = self.llm_client.chat_completion(messages, **request_params)
                semantic_relations = json.loads(response_text)
                
                for relation in semantic_relations:
                    if relation.get('strength', 0) >= 0.4:
                        connection = {
                            'new_concept': new_concept,
                            'existing_concept': relation['existing_concept'],
                            'relationship_type': relation['relationship_type'],
                            'strength': relation['strength'],
                            'explanation': relation['explanation'],
                            'connection_type': 'semantic',
                            'analysis_timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        semantic_connections.append(connection)
                        
            except Exception as e:
                self.logger.warning(f"Semantic analysis failed for concept '{new_concept}': {str(e)}")
                continue
        
        self.logger.info(f"Found {len(semantic_connections)} semantic connections")
        return semantic_connections
    
    def _identify_knowledge_gaps(self, session, user_id: str, new_concepts: List[str], prep_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify potential knowledge gaps based on learning progression"""
        gaps = []
        
        # Check for missing prerequisites in knowledge progression
        knowledge_progression = prep_data.get('knowledge_progression', [])
        
        for i, concept in enumerate(knowledge_progression):
            if i > 0:  # Skip first concept
                prerequisite = knowledge_progression[i-1]
                self.logger.info(f"Checking prerequisite: {prerequisite} for concept: {concept}")

                try:
                    # Check if prerequisite exists in user's knowledge base
                    result = session.run("""
                        MATCH (c:Concept {user_id: $user_id})
                        WHERE c.name =~ '(?i).*' + $prerequisite + '.*'
                        RETURN c.name as concept, c.occurrence_count as frequency
                        ORDER BY frequency DESC
                        LIMIT 1
                    """, user_id=user_id, prerequisite=prerequisite)

                    existing = result.single()
                if not existing or existing.get('frequency', 0) < 2:
                        gap = {
                            'missing_concept': prerequisite,
                            'needed_for': concept,
                            'gap_type': 'prerequisite',
                            'priority': 'high' if i == 1 else 'medium',
                            'recommended_action': f"Learn '{prerequisite}' before diving deeper into '{concept}'"
                        }
                        gaps.append(gap)
                        self.logger.info(f"Added gap for missing prerequisite: {prerequisite}")
                except Exception as e:
                    self.logger.error(f"Error checking prerequisite {prerequisite}: {str(e)}")
                    continue
        self.logger.info(f"Finished checking prerequisites, found {len(gaps)} gaps so far")

        try:

            # Identify domain knowledge gaps using LLM
            if self.llm_client and self.llm_client.is_available():
                self.logger.info("Starting LLM domain gap analysis...")
                domain_gaps = self._identify_domain_gaps_with_llm(session, user_id, new_concepts)
                gaps.extend(domain_gaps)
                self.logger.info(f"LLM domain gap analysis complete, added {len(domain_gaps)} gaps")
        except Exception as e:
            self.logger.error(f"Error in LLM domain gap analysis: {str(e)}")
            
        self.logger.info(f"Identified {len(gaps)} knowledge gaps")
        return gaps
    
    def _identify_domain_gaps_with_llm(self, session, user_id: str, new_concepts: List[str]) -> List[Dict[str, Any]]:
        """Use LLM to identify domain-specific knowledge gaps"""
        gaps = []
        
        try:
            # Get user's existing knowledge domains
            domains_result = session.run("""
                MATCH (c:Concept {user_id: $user_id})
                WITH c.name as concept
                RETURN collect(concept) as all_concepts
            """, user_id=user_id)

            result_record = domains_result.single()
            if result_record:
                existing_concepts = result_record['all_concepts']  # Use bracket notation, not .get()
            else:
                existing_concepts = []
        except Exception as e:
            self.logger.warning(f"Error querying existing concepts: {str(e)}")
            existing_concepts = []
        
        if not existing_concepts:
            self.logger.info("No existing concepts found, skipping LLM domain gap analysis")
            return gaps
        
        prompt = f"""Analyze these new concepts a learner is studying: {', '.join(new_concepts)}

Their existing knowledge includes: {', '.join(existing_concepts[:30])}

Identify important foundational concepts that are missing from their existing knowledge but would be valuable for understanding the new concepts.

Return JSON array with:
- "missing_concept": the gap concept name
- "importance": high/medium/low  
- "gap_type": one of [foundational, contextual, practical, theoretical]
- "explanation": why this concept is important
- "learning_priority": 1-10 (10 = learn immediately)

Focus on genuine gaps that would improve understanding. Maximum 5 gaps."""

        try:
            messages = [
                {"role": "system", "content": "You are an expert learning advisor who identifies knowledge gaps to optimize learning paths."},
                {"role": "user", "content": prompt}
            ]
            
            request_params = self.llm_client.set_provider_specific_defaults(
                temperature=0.3,
                max_tokens=700
            )
            
            response_text = self.llm_client.chat_completion(messages, **request_params)
            domain_gaps = json.loads(response_text)
            
            for gap in domain_gaps:
                if gap.get('learning_priority', 0) >= 6:  # Only include important gaps
                    processed_gap = {
                        'missing_concept': gap['missing_concept'],
                        'gap_type': gap['gap_type'],
                        'importance': gap['importance'],
                        'priority': gap['learning_priority'],
                        'explanation': gap['explanation'],
                        'recommended_action': f"Study '{gap['missing_concept']}' to strengthen understanding of {', '.join(new_concepts[:2])}"
                    }
                    gaps.append(processed_gap)
                    
        except Exception as e:
            self.logger.warning(f"Domain gap analysis failed: {str(e)}")
        
        return gaps
    
    def _find_reinforcement_opportunities(self, session, user_id: str, new_concepts: List[str]) -> List[Dict[str, Any]]:
        """Find concepts that need reinforcement based on forgetting patterns"""
        opportunities = []
        
        # Find concepts related to new learning that haven't been seen recently
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        
        result = session.run("""
            MATCH (new_session:Session {user_id: $user_id})
            WHERE new_session.created_at > datetime($cutoff_date)
            MATCH (new_session)-[:CONTAINS_CONCEPT]->(new_concept:Concept)
            WHERE new_concept.name IN $new_concepts
            
            // Find related concepts that need reinforcement
            MATCH (new_concept)-[:RELATES_TO]-(related:Concept {user_id: $user_id})
            WHERE related.last_seen < datetime($cutoff_date)
            AND related.occurrence_count >= 2
            
            OPTIONAL MATCH (related)<-[:CONTAINS_CONCEPT]-(old_session:Session)
            WITH related, 
                 count(DISTINCT old_session) as session_frequency,
                 duration.between(datetime(related.last_seen), datetime()).days as days_since_seen
            WHERE days_since_seen > 3
            
            RETURN related.name as concept,
                   related.occurrence_count as total_encounters,
                   session_frequency,
                   days_since_seen,
                   related.last_seen as last_encountered
            ORDER BY days_since_seen DESC, total_encounters DESC
            LIMIT 10
        """, user_id=user_id, new_concepts=new_concepts, cutoff_date=cutoff_date)
        
        for record in result:
            days_since = record['days_since_seen']
            total_encounters = record['total_encounters']
            
            # Calculate urgency based on forgetting curve
            urgency = min(days_since / 30.0, 1.0)  # Normalize to 0-1 over 30 days
            priority = "high" if urgency > 0.7 else "medium" if urgency > 0.4 else "low"
            
            opportunity = {
                'concept': record['concept'],
                'days_since_encounter': days_since,
                'total_encounters': total_encounters,
                'session_frequency': record['session_frequency'],
                'last_encountered': record['last_encountered'],
                'urgency_score': urgency,
                'priority': priority,
                'recommended_action': f"Review '{record['concept']}' to reinforce connection with new learning"
            }
            opportunities.append(opportunity)
        
        self.logger.info(f"Found {len(opportunities)} reinforcement opportunities")
        return opportunities
    
    def _analyze_learning_patterns(self, session, user_id: str, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user's learning patterns and preferences"""
        
        # Get learning session patterns
        patterns_result = session.run("""
            MATCH (s:Session {user_id: $user_id})
            WHERE s.created_at > datetime() - duration({days: 30})
            OPTIONAL MATCH (s)-[:CONTAINS_CONCEPT]->(c:Concept)
            OPTIONAL MATCH (s)-[:COVERS_TOPIC]->(t:Topic)
            
            WITH s, count(DISTINCT c) as concepts_per_session, collect(DISTINCT t.name) as topics
            RETURN 
                avg(concepts_per_session) as avg_concepts_per_session,
                count(s) as recent_sessions,
                collect(topics) as all_session_topics,
                collect(s.theme) as session_themes
        """, user_id=user_id)
        
        patterns_data = patterns_result.single()
        
        if not patterns_data:
            return {'error': 'No recent learning patterns found'}
        
        # Analyze topic preferences
        all_topics = [topic for session_topics in patterns_data['all_session_topics'] for topic in session_topics]
        topic_frequency = Counter(all_topics)
        
        # Analyze learning intensity
        avg_concepts = patterns_data['avg_concepts_per_session'] or 0
        intensity = "high" if avg_concepts > 8 else "medium" if avg_concepts > 4 else "low"
        
        # Analyze learning consistency
        recent_sessions = patterns_data['recent_sessions'] or 0
        consistency = "high" if recent_sessions > 15 else "medium" if recent_sessions > 7 else "low"
        
        patterns = {
            'learning_intensity': {
                'level': intensity,
                'avg_concepts_per_session': round(avg_concepts, 1),
                'description': f"Typically learns {round(avg_concepts, 1)} concepts per session"
            },
            'learning_consistency': {
                'level': consistency,
                'sessions_last_30_days': recent_sessions,
                'description': f"{recent_sessions} learning sessions in the last 30 days"
            },
            'topic_preferences': {
                'most_frequent_topics': [topic for topic, count in topic_frequency.most_common(5)],
                'topic_diversity': len(topic_frequency),
                'description': f"Shows interest in {len(topic_frequency)} different topics"
            },
            'session_themes': {
                'recent_themes': list(set(patterns_data['session_themes'])),
                'current_focus': prep_data.get('session_theme', 'general')
            }
        }
        
        return patterns
    
    def _calculate_confidence_scores(self, session, user_id: str, new_concepts: List[str]) -> Dict[str, Any]:
        """Calculate confidence scores for concepts based on exposure and connections"""
        
        confidence_scores = {}
        
        for concept in new_concepts:
            # Check if concept exists in knowledge base
            result = session.run("""
                MATCH (c:Concept {user_id: $user_id})
                WHERE c.name =~ '(?i).*' + $concept + '.*'
                OPTIONAL MATCH (c)-[r]-(related:Concept {user_id: $user_id})
                OPTIONAL MATCH (c)<-[:CONTAINS_CONCEPT]-(s:Session)
                
                RETURN c.name as concept_name,
                       c.occurrence_count as occurrences,
                       count(DISTINCT related) as connection_count,
                       count(DISTINCT s) as session_count,
                       c.created_at as first_seen
                ORDER BY occurrences DESC
                LIMIT 1
            """, user_id=user_id, concept=concept)
            
            record = result.single()
            
            if record:
                # Calculate confidence based on multiple factors
                occurrences = record['occurrences'] or 0
                connections = record['connection_count'] or 0
                sessions = record['session_count'] or 0
                
                # Confidence formula (0-1 scale)
                occurrence_score = min(occurrences / 5.0, 1.0)  # Max at 5 occurrences
                connection_score = min(connections / 10.0, 1.0)  # Max at 10 connections  
                session_score = min(sessions / 3.0, 1.0)        # Max at 3 sessions
                
                overall_confidence = (occurrence_score * 0.4 + connection_score * 0.4 + session_score * 0.2)
                
                confidence_level = "high" if overall_confidence > 0.7 else "medium" if overall_confidence > 0.4 else "low"
                
                confidence_scores[concept] = {
                    'overall_confidence': round(overall_confidence, 2),
                    'confidence_level': confidence_level,
                    'contributing_factors': {
                        'occurrences': occurrences,
                        'connections': connections,
                        'sessions_seen': sessions
                    },
                    'first_encountered': record['first_seen'],
                    'status': 'reinforced' if overall_confidence > 0.3 else 'new'
                }
            else:
                # Completely new concept
                confidence_scores[concept] = {
                    'overall_confidence': 0.1,
                    'confidence_level': 'new',
                    'contributing_factors': {
                        'occurrences': 0,
                        'connections': 0,
                        'sessions_seen': 0
                    },
                    'status': 'new'
                }
        
        return confidence_scores
    
    def _generate_learning_recommendations(self, direct_connections: List, semantic_connections: List, 
                                         knowledge_gaps: List, reinforcement_opportunities: List,
                                         learning_patterns: Dict) -> List[Dict[str, Any]]:
        """Generate actionable learning recommendations"""
        recommendations = []
        
        # Priority 1: Address critical knowledge gaps
        high_priority_gaps = [gap for gap in knowledge_gaps if gap.get('priority') == 'high']
        for gap in high_priority_gaps[:2]:  # Top 2 gaps
            recommendations.append({
                'type': 'knowledge_gap',
                'priority': 'high',
                'action': gap['recommended_action'],
                'concept': gap['missing_concept'],
                'reason': f"Missing prerequisite: {gap.get('explanation', 'No explanation provided')}"
            })
        
        # Priority 2: Reinforce forgetting concepts
        urgent_reinforcement = [opp for opp in reinforcement_opportunities if opp.get('priority') == 'high']
        for opp in urgent_reinforcement[:2]:  # Top 2 opportunities
            recommendations.append({
                'type': 'reinforcement',
                'priority': 'medium',
                'action': opp['recommended_action'],
                'concept': opp['concept'],
                'reason': f"Not reviewed for {opp['days_since_encounter']} days"
            })
        
        # Priority 3: Explore strong connections
        strong_connections = [conn for conn in semantic_connections if conn.get('strength', 0) > 0.7]
        for conn in strong_connections[:2]:  # Top 2 connections
            recommendations.append({
                'type': 'connection',
                'priority': 'low',
                'action': f"Explore the relationship between '{conn['new_concept']}' and '{conn['existing_concept']}'",
                'concept': conn['existing_concept'],
                'reason': f"Strong {conn['relationship_type']} relationship: {conn.get('explanation', 'Related concepts')}" 
            })
        
        # Learning pattern recommendations
        intensity = learning_patterns.get('learning_intensity', {}).get('level', 'medium')
        if intensity == 'low':
            recommendations.append({
                'type': 'learning_strategy',
                'priority': 'medium',
                'action': 'Consider increasing learning session intensity',
                'reason': 'Current learning pace may be too slow for optimal retention'
            })
        
        return recommendations

    
    def _generate_node_id(self, name: str, node_type: str, user_id: str) -> str:
        """Generate unique node ID (same pattern as KnowledgeGraphNode)"""
        import hashlib
        content = f"{user_id}:{node_type}:{name.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()


    def _calculate_confidence_scores_structure(self) -> bool:
        """Test method to validate confidence score calculation structure"""
        # This method is just for testing the structure - returns True if valid
        try:
            # Test the confidence calculation formula
            test_occurrences = 5
            test_connections = 8
            test_sessions = 3
            
            occurrence_score = min(test_occurrences / 5.0, 1.0)
            connection_score = min(test_connections / 10.0, 1.0)
            session_score = min(test_sessions / 3.0, 1.0)
            
            overall_confidence = (occurrence_score * 0.4 + connection_score * 0.4 + session_score * 0.2)
            
            # Validate the calculation produces expected ranges
            valid_range = 0.0 <= overall_confidence <= 1.0
            valid_components = all(0.0 <= score <= 1.0 for score in [occurrence_score, connection_score, session_score])
            
            return valid_range and valid_components
            
        except Exception:
            return False
