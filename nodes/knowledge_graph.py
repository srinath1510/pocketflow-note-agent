"""
Knowledge Graph Node: Builds and maintains a per-user knowledge graph from extracted concepts
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import hashlib
from collections import defaultdict

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import os

from pocketflow import Node as BaseNode


class KnowledgeGraphNode(BaseNode):
    """
    Node 3: Knowledge Graph Construction
    
    Purpose: Build a persistent knowledge graph from extracted concepts and relationships
    
    Input: extracted_concepts from Content Analysis node
    Process: Create/update graph nodes and relationships in Neo4j
    Output: knowledge_graph metrics and insights
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Neo4j connection
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD', 'smartnotes123')
        
        self.driver = None
        self._init_neo4j()
    
    def _init_neo4j(self):
        """Initialize Neo4j connection and create constraints/indexes"""
        try:
            self.driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Verify connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            self.logger.info("Neo4j connection established")
            
            # Create constraints and indexes
            self._create_graph_schema()
            
        except ServiceUnavailable:
            self.logger.error("Neo4j is not available. Please ensure Neo4j is running.")
            self.logger.error("Run: docker-compose up -d neo4j")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Neo4j: {str(e)}")
            raise
    
    def _create_graph_schema(self):
        """Create constraints and indexes for optimal performance"""
        with self.driver.session() as session:
            # Constraints ensure uniqueness
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Resource) REQUIRE r.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    self.logger.debug(f"Constraint already exists or error: {e}")
            
            # Indexes for query performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.name)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.user_id)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.user_id)",
                "CREATE INDEX IF NOT EXISTS FOR (r:Resource) ON (r.url)",
                "CREATE INDEX IF NOT EXISTS FOR (r:Resource) ON (r.user_id)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    self.logger.debug(f"Index already exists or error: {e}")
    
    def prep(self, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare for knowledge graph construction
        """
        self.logger.info("Starting Knowledge Graph prep phase")
        
        # Get user context (for now, use session_id as user_id)
        user_id = shared_state.get('session_id', 'default_user')
        
        # Get extracted concepts from previous node
        extracted_concepts = shared_state.get('extracted_concepts', {})
        raw_captures = shared_state.get('raw_captures', [])
        
        if not extracted_concepts:
            self.logger.warning("No extracted concepts found")
            return {'error': 'No concepts to process', 'user_id': user_id}
        
        # Ensure user exists in graph
        self._ensure_user_exists(user_id)
        
        # Prepare data for processing
        prep_data = {
            'user_id': user_id,
            'concepts': extracted_concepts.get('learning_concepts', []),
            'entities': extracted_concepts.get('entities', {}),
            'key_terms': extracted_concepts.get('key_terms', {}),
            'topics': extracted_concepts.get('topics', []),
            'concept_connections': extracted_concepts.get('concept_connections', {}),
            'session_theme': extracted_concepts.get('session_theme', 'general'),
            'knowledge_progression': extracted_concepts.get('knowledge_progression', []),
            'captures': raw_captures,
            'session_id': shared_state.get('session_id'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.logger.info(f"Prepared {len(prep_data['concepts'])} concepts for user {user_id}")
        return prep_data
    
    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution: Build/update the knowledge graph
        """
        if 'error' in prep_result:
            return prep_result
        
        self.logger.info("Starting Knowledge Graph construction")
        
        user_id = prep_result['user_id']
        session_id = prep_result['session_id']
        
        # Create session node
        session_node_id = self._create_session_node(
            user_id, 
            session_id, 
            prep_result['session_theme'],
            prep_result['timestamp']
        )
        
        # Process different node types
        concept_nodes = self._process_concepts(user_id, prep_result['concepts'], session_node_id)
        entity_nodes = self._process_entities(user_id, prep_result['entities'], session_node_id)
        topic_nodes = self._process_topics(user_id, prep_result['topics'], session_node_id)
        resource_nodes = self._process_resources(user_id, prep_result['captures'], session_node_id)
        
        # Create relationships
        relationships_created = self._create_relationships(
            user_id,
            concept_nodes,
            entity_nodes,
            topic_nodes,
            resource_nodes,
            prep_result
        )
        
        # Calculate graph metrics
        metrics = self._calculate_graph_metrics(user_id)
        
        # Generate insights
        insights = self._generate_insights(user_id, session_id)
        
        return {
            'user_id': user_id,
            'session_id': session_id,
            'nodes_created': {
                'concepts': len(concept_nodes),
                'entities': len(entity_nodes),
                'topics': len(topic_nodes),
                'resources': len(resource_nodes)
            },
            'relationships_created': relationships_created,
            'graph_metrics': metrics,
            'insights': insights
        }
    
    def post(self, shared_state: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """
        Post-processing: Add graph results to shared state
        """
        self.logger.info("Knowledge Graph post-execution phase")
        
        if 'error' in exec_result:
            shared_state['knowledge_graph_error'] = exec_result['error']
            return "error"
        
        # Add knowledge graph results to shared state
        shared_state['knowledge_graph'] = {
            'user_id': exec_result['user_id'],
            'session_id': exec_result['session_id'],
            'nodes_created': exec_result['nodes_created'],
            'relationships_created': exec_result['relationships_created'],
            'metrics': exec_result['graph_metrics'],
            'insights': exec_result['insights'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Update pipeline metadata
        shared_state['pipeline_metadata']['knowledge_graph_complete'] = True
        shared_state['pipeline_metadata']['knowledge_graph_summary'] = {
            'total_nodes_created': sum(exec_result['nodes_created'].values()),
            'total_relationships': exec_result['relationships_created'],
            'graph_density': exec_result['graph_metrics'].get('density', 0)
        }
        
        self.logger.info("Knowledge graph construction complete")
        return "default"
    
    def _ensure_user_exists(self, user_id: str):
        """Ensure user node exists in graph"""
        with self.driver.session() as session:
            session.run("""
                MERGE (u:User {id: $user_id})
                ON CREATE SET 
                    u.created_at = datetime(),
                    u.last_active = datetime()
                ON MATCH SET
                    u.last_active = datetime()
            """, user_id=user_id)
    
    def _create_session_node(self, user_id: str, session_id: str, theme: str, timestamp: str) -> str:
        """Create a session node for this learning session"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (s:Session {
                    id: $session_id,
                    theme: $theme,
                    created_at: datetime($timestamp),
                    user_id: $user_id
                })
                CREATE (u)-[:HAS_SESSION]->(s)
                RETURN s.id as session_id
            """, user_id=user_id, session_id=session_id, theme=theme, timestamp=timestamp)
            
            return result.single()['session_id']
    
    def _generate_node_id(self, name: str, node_type: str, user_id: str) -> str:
        """Generate unique node ID"""
        content = f"{user_id}:{node_type}:{name.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _process_concepts(self, user_id: str, concepts: List[str], session_id: str) -> List[str]:
        """Process and create/update concept nodes"""
        concept_ids = []
        
        with self.driver.session() as session:
            for concept in concepts:
                if not concept:
                    continue
                    
                concept_id = self._generate_node_id(concept, 'concept', user_id)
                concept_ids.append(concept_id)
                
                # Create or update concept
                session.run("""
                    MERGE (c:Concept {id: $concept_id})
                    ON CREATE SET
                        c.name = $name,
                        c.user_id = $user_id,
                        c.created_at = datetime(),
                        c.occurrence_count = 1
                    ON MATCH SET
                        c.occurrence_count = c.occurrence_count + 1,
                        c.last_seen = datetime()
                    WITH c
                    MATCH (s:Session {id: $session_id})
                    CREATE (s)-[:CONTAINS_CONCEPT]->(c)
                """, concept_id=concept_id, name=concept, user_id=user_id, session_id=session_id)
        
        self.logger.info(f"Processed {len(concept_ids)} concepts")
        return concept_ids
    
    def _process_entities(self, user_id: str, entities: Dict[str, str], session_id: str) -> List[str]:
        """Process and create/update entity nodes"""
        entity_ids = []
        
        with self.driver.session() as session:
            for entity_name, entity_type in entities.items():
                if not entity_name:
                    continue
                    
                entity_id = self._generate_node_id(entity_name, 'entity', user_id)
                entity_ids.append(entity_id)
                
                session.run("""
                    MERGE (e:Entity {id: $entity_id})
                    ON CREATE SET
                        e.name = $name,
                        e.type = $entity_type,
                        e.user_id = $user_id,
                        e.created_at = datetime(),
                        e.occurrence_count = 1
                    ON MATCH SET
                        e.occurrence_count = e.occurrence_count + 1,
                        e.last_seen = datetime()
                    WITH e
                    MATCH (s:Session {id: $session_id})
                    CREATE (s)-[:MENTIONS_ENTITY]->(e)
                """, entity_id=entity_id, name=entity_name, entity_type=entity_type, 
                    user_id=user_id, session_id=session_id)
        
        return entity_ids
    
    def _process_topics(self, user_id: str, topics: List[str], session_id: str) -> List[str]:
        """Process and create/update topic nodes"""
        topic_ids = []
        
        with self.driver.session() as session:
            for topic in topics:
                if not topic:
                    continue
                    
                topic_id = self._generate_node_id(topic, 'topic', user_id)
                topic_ids.append(topic_id)
                
                session.run("""
                    MERGE (t:Topic {id: $topic_id})
                    ON CREATE SET
                        t.name = $name,
                        t.user_id = $user_id,
                        t.created_at = datetime(),
                        t.session_count = 1
                    ON MATCH SET
                        t.session_count = t.session_count + 1,
                        t.last_seen = datetime()
                    WITH t
                    MATCH (s:Session {id: $session_id})
                    CREATE (s)-[:COVERS_TOPIC]->(t)
                """, topic_id=topic_id, name=topic, user_id=user_id, session_id=session_id)
        
        return topic_ids
    
    def _process_resources(self, user_id: str, captures: List[Dict], session_id: str) -> List[str]:
        """Process and create resource nodes from captures"""
        resource_ids = []
        
        with self.driver.session() as session:
            for capture in captures:
                url = capture.get('url', '')
                if not url:
                    continue
                
                resource_id = self._generate_node_id(url, 'resource', user_id)
                resource_ids.append(resource_id)
                
                metadata = capture.get('metadata', {})
                
                session.run("""
                    MERGE (r:Resource {id: $resource_id})
                    ON CREATE SET
                        r.url = $url,
                        r.title = $title,
                        r.domain = $domain,
                        r.user_id = $user_id,
                        r.created_at = datetime(),
                        r.visit_count = 1
                    ON MATCH SET
                        r.visit_count = r.visit_count + 1,
                        r.last_visited = datetime()
                    WITH r
                    MATCH (s:Session {id: $session_id})
                    CREATE (s)-[:CAPTURED_FROM]->(r)
                """, resource_id=resource_id, url=url, 
                    title=metadata.get('page_title', 'Untitled'),
                    domain=metadata.get('domain', 'unknown'),
                    user_id=user_id, session_id=session_id)
        
        return resource_ids
    
    def _create_relationships(self, user_id: str, concept_ids: List[str], 
                            entity_ids: List[str], topic_ids: List[str], 
                            resource_ids: List[str], prep_data: Dict) -> int:
        """Create relationships between nodes"""
        relationships_created = 0
        
        # Concept connections from LLM analysis
        concept_connections = prep_data.get('concept_connections', {})
        
        with self.driver.session() as session:
            # Create RELATES_TO relationships from concept_connections
            for concept1, related in concept_connections.items():
                concept1_id = self._generate_node_id(concept1, 'concept', user_id)
                
                if isinstance(related, list):
                    for concept2 in related:
                        concept2_id = self._generate_node_id(concept2, 'concept', user_id)
                        result = session.run("""
                            MATCH (c1:Concept {id: $c1_id}), (c2:Concept {id: $c2_id})
                            WHERE c1.user_id = $user_id AND c2.user_id = $user_id
                            MERGE (c1)-[r:RELATES_TO]-(c2)
                            ON CREATE SET r.created_at = datetime()
                            RETURN r
                        """, c1_id=concept1_id, c2_id=concept2_id, user_id=user_id)
                        
                        if result.single():
                            relationships_created += 1
            
            # Create PREREQUISITE_OF from knowledge_progression
            progression = prep_data.get('knowledge_progression', [])
            for i in range(len(progression) - 1):
                current_id = self._generate_node_id(progression[i], 'concept', user_id)
                next_id = self._generate_node_id(progression[i + 1], 'concept', user_id)
                
                result = session.run("""
                    MATCH (c1:Concept {id: $current_id}), (c2:Concept {id: $next_id})
                    WHERE c1.user_id = $user_id AND c2.user_id = $user_id
                    MERGE (c1)-[r:PREREQUISITE_OF]->(c2)
                    ON CREATE SET r.created_at = datetime()
                    RETURN r
                """, current_id=current_id, next_id=next_id, user_id=user_id)
                
                if result.single():
                    relationships_created += 1
        
        self.logger.info(f"Created {relationships_created} relationships")
        return relationships_created
    
    def _calculate_graph_metrics(self, user_id: str) -> Dict[str, Any]:
        """Calculate metrics for the user's knowledge graph"""
        with self.driver.session() as session:
            # Basic counts
            result = session.run("""
                MATCH (u:User {id: $user_id})
                OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session)
                OPTIONAL MATCH (c:Concept {user_id: $user_id})
                OPTIONAL MATCH (e:Entity {user_id: $user_id})
                OPTIONAL MATCH (t:Topic {user_id: $user_id})
                OPTIONAL MATCH (r:Resource {user_id: $user_id})
                RETURN 
                    count(DISTINCT s) as session_count,
                    count(DISTINCT c) as concept_count,
                    count(DISTINCT e) as entity_count,
                    count(DISTINCT t) as topic_count,
                    count(DISTINCT r) as resource_count
            """, user_id=user_id)
            
            counts = result.single()
            
            # Graph density and connectivity
            density_result = session.run("""
                MATCH (n {user_id: $user_id})
                WHERE n:Concept OR n:Entity
                OPTIONAL MATCH (n)-[r]-(m {user_id: $user_id})
                WHERE m:Concept OR m:Entity
                WITH count(DISTINCT n) as node_count, count(DISTINCT r) as edge_count
                RETURN 
                    node_count,
                    edge_count,
                    CASE 
                        WHEN node_count > 1 
                        THEN toFloat(edge_count) / (node_count * (node_count - 1) / 2)
                        ELSE 0
                    END as density
            """, user_id=user_id)
            
            density_data = density_result.single()
            
            # Most connected concepts
            central_concepts = session.run("""
                MATCH (c:Concept {user_id: $user_id})
                OPTIONAL MATCH (c)-[r]-(other)
                WITH c, count(r) as degree
                ORDER BY degree DESC
                LIMIT 5
                RETURN c.name as concept, degree
            """, user_id=user_id)
            
            central_concepts_list = [
                {"concept": record["concept"], "connections": record["degree"]}
                for record in central_concepts
            ]
            
            return {
                "total_sessions": counts["session_count"],
                "total_concepts": counts["concept_count"],
                "total_entities": counts["entity_count"],
                "total_topics": counts["topic_count"],
                "total_resources": counts["resource_count"],
                "total_nodes": density_data["node_count"],
                "total_edges": density_data["edge_count"],
                "graph_density": round(density_data["density"], 4),
                "most_connected_concepts": central_concepts_list
            }
    
    def _generate_insights(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Generate insights about the knowledge graph"""
        insights = {}
        
        with self.driver.session() as session:
            # Find isolated concepts (potential knowledge gaps)
            isolated = session.run("""
                MATCH (c:Concept {user_id: $user_id})
                WHERE NOT (c)-[:RELATES_TO]-()
                RETURN c.name as concept
                LIMIT 10
            """, user_id=user_id)
            
            insights["isolated_concepts"] = [r["concept"] for r in isolated]
            
            # Find concept clusters
            clusters = session.run("""
                MATCH (c1:Concept {user_id: $user_id})-[:RELATES_TO]-(c2:Concept)
                WITH c1, count(DISTINCT c2) as connections
                WHERE connections >= 3
                MATCH (c1)-[:RELATES_TO]-(related:Concept)
                RETURN c1.name as hub_concept, collect(DISTINCT related.name) as cluster
                ORDER BY size(cluster) DESC
                LIMIT 5
            """, user_id=user_id)
            
            insights["concept_clusters"] = [
                {"hub": r["hub_concept"], "related": r["cluster"][:5]}
                for r in clusters
            ]
            
            # Learning trajectory
            trajectory = session.run("""
                MATCH path = (c1:Concept {user_id: $user_id})-[:PREREQUISITE_OF*..5]->(c2:Concept)
                RETURN c1.name as start, c2.name as end, length(path) as steps
                ORDER BY steps DESC
                LIMIT 5
            """, user_id=user_id)
            
            insights["learning_paths"] = [
                {"from": r["start"], "to": r["end"], "steps": r["steps"]}
                for r in trajectory
            ]
            
            # Recent learning focus
            recent_focus = session.run("""
                MATCH (s:Session {id: $session_id})-[:CONTAINS_CONCEPT]->(c:Concept)
                RETURN c.name as concept
                LIMIT 10
            """, session_id=session_id)
            
            insights["session_focus"] = [r["concept"] for r in recent_focus]
            
        return insights
    
    def __del__(self):
        """Clean up Neo4j driver connection"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()


# Helper function for local testing
def test_neo4j_connection():
    """Test if Neo4j is accessible"""
    try:
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'smartnotes123')
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 'Connected!' as message")
            print(result.single()['message'])
        driver.close()
        return True
    except Exception as e:
        print(f"Neo4j connection failed: {e}")
        print("Make sure Neo4j is running: docker-compose up -d neo4j")
        return False


if __name__ == "__main__":
    # Test connection when run directly
    test_neo4j_connection()