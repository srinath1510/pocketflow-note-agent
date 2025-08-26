"""
Test data fixtures and sample data for unit and integration tests.
"""

SAMPLE_MINIMAL_CAPTURES = [
    {
        "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data without being explicitly programmed.",
        "user_id": "test_user_001",
        "source_url": "https://ml-basics.com/introduction",
        "title": "Introduction to Machine Learning",
        "intent": "learn",
        "user_note": "Foundational concepts for AI course"
    },
    {
        "content": "Deep learning uses neural networks with multiple layers to model and understand complex patterns in data.",
        "user_id": "test_user_001", 
        "source_url": "https://deeplearning.ai/basics",
        "title": "Deep Learning Fundamentals",
        "intent": "research",
        "user_note": "Advanced topic for later study"
    },
    {
        "content": "Natural language processing enables computers to understand, interpret, and generate human language.",
        "user_id": "test_user_001",
        "source_url": "https://nlp-guide.org/intro", 
        "title": "NLP Overview",
        "intent": "reference"
    }
]

SAMPLE_PROCESSED_CAPTURES = [
    {
        "user_id": "test_user_001",
        "session_id": "test_session_001",
        "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data without being explicitly programmed.",
        "title": "Introduction to Machine Learning", 
        "source_url": "https://ml-basics.com/introduction",
        "timestamp": "2024-01-01T10:00:00Z",
        "intent": "learn",
        "user_note": "Foundational concepts for AI course",
        "metadata": {
            "word_count": 23,
            "domain": "ml-basics.com",
            "content_category": "educational",
            "knowledge_level": "beginner",
            "reading_time_minutes": 1,
            "language": "en",
            "content_type": "article"
        }
    }
]

SAMPLE_EXTRACTED_CONCEPTS = {
    "learning_concepts": [
        "machine learning",
        "artificial intelligence", 
        "algorithms",
        "data learning",
        "neural networks",
        "deep learning"
    ],
    "key_terms": {
        "machine learning": "Subset of AI focused on algorithms that learn from data",
        "neural networks": "Computing systems inspired by biological neural networks",
        "deep learning": "ML technique using multiple layer neural networks",
        "natural language processing": "AI field focused on human language understanding"
    },
    "entities": {
        "technologies": ["Python", "TensorFlow", "PyTorch", "scikit-learn"],
        "concepts": ["supervised learning", "unsupervised learning", "reinforcement learning"],
        "domains": ["computer science", "data science", "artificial intelligence"]
    },
    "topics": [
        "artificial intelligence",
        "machine learning", 
        "data science",
        "computer science",
        "neural networks"
    ],
    "session_theme": "artificial intelligence and machine learning fundamentals",
    "complexity_assessment": {
        "overall_level": "intermediate",
        "technical_depth": "moderate", 
        "prerequisite_knowledge": ["programming basics", "mathematics", "statistics"],
        "difficulty_score": 6.5
    },
    "knowledge_progression": [
        "programming basics",
        "data structures", 
        "algorithms",
        "statistics",
        "machine learning",
        "neural networks",
        "deep learning"
    ]
}

SAMPLE_KNOWLEDGE_GRAPH = {
    "nodes_created": {
        "concepts": 6,
        "entities": 8,
        "topics": 5,
        "resources": 3,
        "sessions": 1
    },
    "relationships_created": 15,
    "graph_summary": {
        "total_nodes": 23,
        "total_relationships": 15,
        "density": 0.057
    },
    "metrics": {
        "centrality_scores": {
            "machine learning": 0.85,
            "artificial intelligence": 0.92,
            "neural networks": 0.71
        },
        "clustering_coefficient": 0.34,
        "graph_density": 0.057
    }
}

SAMPLE_HISTORICAL_CONNECTIONS = {
    "direct_connections": [
        {
            "new_concept": "deep learning",
            "existing_concept": "machine learning",
            "similarity_score": 0.89,
            "connection_type": "direct_match",
            "relationship_type": "specialization_of"
        }
    ],
    "semantic_connections": [
        {
            "new_concept": "neural networks",
            "existing_concept": "algorithms", 
            "relationship_type": "builds_upon",
            "strength": 0.76,
            "explanation": "Neural networks are a specific type of learning algorithm"
        }
    ],
    "total_connections_found": 8
}

SAMPLE_NOTION_RESPONSE = {
    "creation_summary": {
        "total_pages": 3,
        "concepts_created": 6,
        "topics_covered": ["machine learning", "AI", "neural networks"],
        "databases_used": ["concepts", "sessions", "topics"]
    },
    "master_session_url": "https://notion.so/test_session_page",
    "created_pages": [
        {
            "type": "session_summary",
            "url": "https://notion.so/session_summary_page",
            "title": "ML Fundamentals - Session Summary"
        },
        {
            "type": "concept_page", 
            "url": "https://notion.so/ml_concept_page",
            "title": "Machine Learning Concepts"
        }
    ]
}

SAMPLE_API_RESPONSES = {
    "anthropic_response": {
        "content": [
            {"text": "Based on the content, I've identified key concepts: machine learning, neural networks, and data analysis."}
        ]
    },
    "notion_create_database": {
        "id": "test_database_123",
        "title": [{"plain_text": "Test Database"}],
        "properties": {}
    },
    "notion_create_page": {
        "id": "test_page_456", 
        "url": "https://notion.so/test_page_456",
        "properties": {}
    },
    "neo4j_query_result": [
        {"concept": "machine learning", "count": 5},
        {"concept": "neural networks", "count": 3}
    ]
}

ERROR_SCENARIOS = {
    "api_key_missing": {
        "anthropic": "ANTHROPIC_API_KEY not found",
        "notion": "NOTION_TOKEN not found"
    },
    "service_unavailable": {
        "neo4j": "ServiceUnavailable: Could not connect to Neo4j",
        "anthropic": "APIConnectionError: Connection timeout",
        "notion": "HTTPError: 503 Service Unavailable"
    },
    "invalid_input": {
        "empty_content": {"content": "", "user_id": "test"},
        "missing_user_id": {"content": "test content"},
        "invalid_url": {"content": "test", "source_url": "not-a-url", "user_id": "test"}
    }
}


def create_sample_learning_session():
    """Create a sample learning session for testing."""
    return SAMPLE_MINIMAL_CAPTURES.copy()