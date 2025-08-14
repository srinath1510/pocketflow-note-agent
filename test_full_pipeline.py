#!/usr/bin/env python3
"""
Complete AI Learning Pipeline Integration Test Suite
Tests the entire flow from raw captures to Notion pages
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime, timezone
from typing import Dict, Any, List
from pathlib import Path

# Import pipeline components
from main import NoteGenerationPipeline, create_sample_minimal_input
from pipeline_orchestrator import PipelineOrchestrator
from api_server import app as flask_app

# Import individual nodes for targeted testing
from nodes.capture_ingestion import CaptureIngestionNode
from nodes.content_analysis import ContentAnalysisNode
from nodes.knowledge_graph import KnowledgeGraphNode
from nodes.historical_knowledge_retrieval import HistoricalKnowledgeRetrievalNode
from nodes.notion_note_generation import NotionNoteGenerationNode


class TestCompletePipeline:
    """Integration tests for the complete AI learning pipeline"""

    @pytest.fixture
    def mock_environment(self):
        """Set up a complete mock environment for testing"""
        env_vars = {
            'ANTHROPIC_API_KEY': 'test_anthropic_key_123',
            'NOTION_TOKEN': 'test_notion_token_456',
            'NEO4J_URI': 'bolt://localhost:7687',
            'NEO4J_USER': 'neo4j',
            'NEO4J_PASSWORD': 'smartnotes123',
            'LLM_PROVIDER': 'anthropic'
        }
        
        with patch.dict(os.environ, env_vars):
            yield env_vars

    @pytest.fixture
    def sample_learning_session(self):
        """Create a realistic learning session for testing"""
        return [
            {
                "content": "Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention.",
                "user_id": "test_learner_123",
                "source_url": "https://example.com/ml-fundamentals",
                "title": "Introduction to Machine Learning",
                "intent": "learn",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_note": "Need to understand this for my data science course"
            },
            {
                "content": "Neural networks are a series of algorithms that mimic the operations of a human brain to recognize relationships between vast amounts of data. They are used in a variety of applications in financial services, from forecasting and marketing research to fraud detection and risk assessment.",
                "user_id": "test_learner_123", 
                "source_url": "https://example.com/neural-networks-intro",
                "title": "Neural Networks Explained",
                "intent": "research",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "content": "Deep learning is a subset of machine learning in artificial intelligence that has networks capable of learning unsupervised from data that is unstructured or unlabeled. Also known as deep neural learning or deep neural network.",
                "user_id": "test_learner_123",
                "source_url": "https://example.com/deep-learning",
                "title": "Deep Learning Fundamentals", 
                "intent": "learn",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_note": "Advanced topic - need solid foundation first"
            },
            {
                "content": "Supervised learning is a type of machine learning where the model is trained on labeled data. The algorithm learns from the training data and can make predictions on new, unseen data.",
                "user_id": "test_learner_123",
                "source_url": "https://example.com/supervised-learning",
                "title": "Supervised Learning Guide",
                "intent": "learn"
            }
        ]

    @pytest.fixture  
    def mock_llm_responses(self):
        """Mock LLM responses for consistent testing"""
        return {
            'content_analysis_batch': {
                "analyses": [
                    {
                        "learning_concepts": ["machine learning", "data analysis", "artificial intelligence"],
                        "key_terms": {"machine learning": "Automated analytical model building"},
                        "entities": {"algorithms": "technology"},
                        "methodologies": ["supervised learning"],
                        "skills": ["pattern recognition"],
                        "complexity": "intermediate",
                        "prerequisites": ["statistics", "programming"],
                        "learning_type": "explanation",
                        "actionable_items": ["practice with datasets"],
                        "main_topic": "machine learning"
                    },
                    {
                        "learning_concepts": ["neural networks", "algorithms", "pattern recognition"],
                        "key_terms": {"neural networks": "Brain-inspired computing systems"},
                        "entities": {"brain": "biological_system"},
                        "methodologies": ["deep learning"],
                        "skills": ["data modeling"],
                        "complexity": "advanced", 
                        "prerequisites": ["linear algebra", "calculus"],
                        "learning_type": "explanation",
                        "actionable_items": ["build simple neural network"],
                        "main_topic": "neural networks"
                    },
                    {
                        "learning_concepts": ["deep learning", "neural networks", "unsupervised learning"],
                        "key_terms": {"deep learning": "Multi-layer neural networks"},
                        "entities": {"TensorFlow": "technology"},
                        "methodologies": ["backpropagation"],
                        "skills": ["model architecture"],
                        "complexity": "advanced",
                        "prerequisites": ["neural networks", "calculus"],
                        "learning_type": "explanation", 
                        "actionable_items": ["experiment with deep networks"],
                        "main_topic": "deep learning"
                    },
                    {
                        "learning_concepts": ["supervised learning", "labeled data", "predictions"],
                        "key_terms": {"supervised learning": "Learning from labeled examples"},
                        "entities": {"training data": "concept"},
                        "methodologies": ["classification", "regression"],
                        "skills": ["model evaluation"],
                        "complexity": "beginner",
                        "prerequisites": ["basic statistics"],
                        "learning_type": "explanation",
                        "actionable_items": ["try classification problems"],
                        "main_topic": "supervised learning"
                    }
                ]
            },
            'content_synthesis': {
                "session_learning_theme": "Machine Learning Fundamentals",
                "knowledge_progression": ["supervised learning", "machine learning", "neural networks", "deep learning"],
                "learning_path": ["basic concepts", "algorithms", "neural networks", "advanced techniques"],
                "session_complexity": "intermediate",
                "learning_goals": ["understand ML fundamentals", "grasp neural network basics"],
                "next_steps": ["practice with real datasets", "build simple models"],
                "concept_connections": {"machine learning": ["neural networks", "deep learning"]},
                "synthesis_method": "llm_complex"
            },
            'historical_semantic_analysis': [
                {
                    "existing_concept": "statistics",
                    "relationship_type": "prerequisite", 
                    "strength": 0.9,
                    "explanation": "Statistics provides the mathematical foundation for machine learning"
                }
            ],
            'knowledge_gap_analysis': [
                {
                    "missing_concept": "linear algebra",
                    "importance": "high",
                    "gap_type": "foundational", 
                    "explanation": "Essential mathematical foundation for neural networks",
                    "learning_priority": 9
                }
            ],
            'notion_topic_clustering': {
                "topics": [
                    {
                        "topic_name": "Machine Learning Fundamentals",
                        "scope": "Core concepts and algorithms in machine learning",
                        "complexity_level": "intermediate",
                        "learning_objectives": ["Understand ML principles", "Apply basic algorithms"],
                        "prerequisite_topics": ["statistics", "programming"],
                        "related_concepts": ["machine learning", "supervised learning"],
                        "confidence": 0.9
                    }
                ]
            },
            'notion_content_generation': {
                "learning_story": "You explored machine learning fundamentals through systematic study",
                "concept_cards": [
                    {
                        "concept": "machine learning",
                        "essence": "Automated learning from data",
                        "memory_trigger": "Think algorithms learning patterns"
                    }
                ],
                "curiosity_questions": ["How does machine learning work in practice?"],
                "personal_relevance": "Essential for data science career advancement"
            },
            'notion_session_synthesis': {
                "session_overview": {
                    "title": "Machine Learning Learning Journey",
                    "narrative": "Progressive exploration from basic ML to advanced neural networks"
                },
                "strategic_next_steps": {
                    "high_impact_priorities": [
                        "Practice with scikit-learn",
                        "Study linear algebra", 
                        "Build first neural network"
                    ]
                }
            }
        }

    @pytest.fixture
    def mock_neo4j(self):
        """Mock Neo4j database operations"""
        with patch('neo4j.GraphDatabase.driver') as mock_driver:
            mock_session = MagicMock()
            
            def mock_run(*args, **kwargs):
                mock_result = MagicMock()
                query = args[0] if args else ""
                
                # Default return with all possible keys
                default_result = {
                    'session_id': 'test_session_123',
                    'session_count': 1,
                    'concept_count': 5,
                    'entity_count': 3,
                    'topic_count': 2,
                    'relationship_count': 4,
                    'resource_count': 6,  
                    'node_count': 15,     
                    'edge_count': 8,      
                    'density': 0.25,      
                    'id': 'test_id_123',
                    'count': 1,
                    'nodes_created': 5,
                    'relationships_created': 4
                }
                
                mock_result.single.return_value = default_result
                mock_result.data.return_value = [default_result]
                mock_result.consume.return_value = None
                return mock_result
        
        mock_session.run.side_effect = mock_run
        mock_session.close.return_value = None
        
        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver_instance.session.return_value.__exit__.return_value = None
        mock_driver.return_value = mock_driver_instance
        
        yield mock_session

    @pytest.fixture
    def mock_notion_api(self):
        """Mock Notion API for complete testing"""
        with patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post, \
             patch('requests.patch') as mock_patch:
            
            # Mock Notion API health check
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'object': 'user', 'id': 'test_user'}
            
            # Mock database creation
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'id': 'test_database_123',
                'title': [{'plain_text': 'Smart Notes Database'}]
            }
            
            # Mock page creation
            mock_patch.return_value.status_code = 200
            mock_patch.return_value.json.return_value = {
                'id': 'test_page_123',
                'url': 'https://notion.so/test_page_123'
            }
            
            yield {
                'get': mock_get,
                'post': mock_post, 
                'patch': mock_patch
            }

    @pytest.fixture
    def mock_llm_client(self):
        """Create a reusable mock LLM client"""
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_provider_name.return_value = "test_provider"
        mock_client.set_provider_specific_defaults.return_value = {"temperature": 0.3}
        return mock_client

    def test_pipeline_initialization(self, mock_environment):
        """Test pipeline initializes with all nodes correctly"""
        pipeline = NoteGenerationPipeline()
        
        # Check all nodes are initialized
        assert pipeline.capture_ingestion_node is not None
        assert pipeline.content_analysis_node is not None
        assert pipeline.knowledge_graph_node is not None
        assert pipeline.historical_knowledge_node is not None
        assert pipeline.notion_generation_node is not None
        
        # Check flow is built
        assert pipeline.flow is not None

    def test_individual_node_execution_sequence(self, mock_environment, sample_learning_session, 
                                               mock_llm_responses, mock_neo4j, mock_notion_api, mock_llm_client):
        """Test each node executes correctly in sequence"""

        with patch('nodes.knowledge_graph.GraphDatabase.driver') as mock_driver:
            mock_driver.return_value = mock_neo4j
        
        try:
            pipeline = NoteGenerationPipeline()
            pipeline.knowledge_graph_node.driver = mock_neo4j
            print(f"Pipeline created: {pipeline}")
            print(f"Content analysis node: {pipeline.content_analysis_node}")
            print(f"Notion node: {pipeline.notion_generation_node}")
            
            # Mock LLM clients for all nodes that need them
            with patch('nodes.notion_note_generation.NotionClient') as MockNotionClient, \
                patch('nodes.notion_note_generation.NotionDatabaseManager') as MockDatabaseManager, \
                patch('nodes.notion_note_generation.TopicOrganizer') as MockTopicOrganizer, \
                patch('nodes.notion_note_generation.ContentEnhancer') as MockContentEnhancer, \
                patch('nodes.notion_note_generation.NotionPageBuilder') as MockPageBuilder, \
                patch('nodes.notion_note_generation.NotionBlockBuilder') as MockBlockBuilder:
            
                mock_notion_client = MockNotionClient.return_value
                mock_notion_client.test_connection.return_value = True

                mock_db_manager = MockDatabaseManager.return_value
                mock_db_manager.ensure_enhanced_databases_exist.return_value = {
                    'learning_sessions': 'db_sessions_123',
                    'research_topics': 'db_topics_123', 
                    'concept_library': 'db_concepts_123'
                }

                # Mock topic organizer
                mock_organizer = MockTopicOrganizer.return_value
                mock_organizer.intelligent_topic_clustering.return_value = {
                    'Machine Learning': {
                        'topic_name': 'Machine Learning',
                        'concepts': ['machine learning'],
                        'captures': sample_learning_session[:2]
                    }
                }

                mock_enhancer = MockContentEnhancer.return_value
                mock_enhancer.generate_rich_topic_content.return_value = {'learning_story': 'test story'}
                mock_enhancer._generate_session_story.return_value = {'title': 'Test Session'}
                mock_enhancer._create_master_session_synthesis.return_value = {'overview': 'test'}
            
                mock_page_builder = MockPageBuilder.return_value
                mock_page_builder.create_enhanced_topic_page.return_value = {'id': 'page_123'}
                mock_page_builder.create_enhanced_master_session_page.return_value = {'id': 'master_123'}
                mock_page_builder.create_enhanced_concept_library_entries.return_value = [{'id': 'concept_123'}]
                mock_page_builder.get_page_url.return_value = 'https://notion.so/test'
                

                # Set up LLM response sequence
                mock_llm_client.chat_completion.side_effect = [
                    json.dumps(mock_llm_responses['content_analysis_batch']),
                    json.dumps(mock_llm_responses['content_synthesis']),
                    json.dumps(mock_llm_responses['historical_semantic_analysis']),
                    json.dumps(mock_llm_responses['knowledge_gap_analysis'])
                ]
                
                # Mock Notion components
                mock_organizer.intelligent_topic_clustering.return_value = {
                    'Machine Learning': {
                        'topic_name': 'Machine Learning',
                        'concepts': ['machine learning', 'neural networks'],
                        'captures': sample_learning_session[:2],
                        'source_count': 2
                    }
                }
                
                mock_enhancer.generate_rich_topic_content.return_value = mock_llm_responses['notion_content_generation']
                mock_enhancer._generate_session_story.return_value = {
                    'title': 'ML Learning Session',
                    'story': 'You learned about machine learning',
                    'spark': 'curiosity'
                }
                mock_enhancer._create_master_session_synthesis.return_value = mock_llm_responses['notion_session_synthesis']
                
                # Initialize shared state
                shared_state = {
                    "session_id": "test_session_integration_123",
                    "user_id": "test_learner_123",
                    "raw_input": sample_learning_session,
                    "pipeline_metadata": {
                        "start_time": datetime.now(timezone.utc).isoformat(),
                        "input_format": "minimal_capture",
                        "pipeline_version": "1.1.0-test"
                    }
                }
                
                # Test Node 1: Capture Ingestion
                result1 = pipeline.capture_ingestion_node.prep(shared_state)
                assert 'captures_to_process' in result1
                assert len(result1['captures_to_process']) == 4
                
                exec_result1 = pipeline.capture_ingestion_node.exec(result1)
                assert 'processed_captures' in exec_result1
                assert len(exec_result1['processed_captures']) == 4
                
                post_result1 = pipeline.capture_ingestion_node.post(shared_state, result1, exec_result1)
                assert post_result1 == "default"
                assert 'raw_captures' in shared_state
                
                # Test Node 2: Content Analysis
                result2 = pipeline.content_analysis_node.prep(shared_state)
                assert 'capture_categories' in result2
                
                exec_result2 = pipeline.content_analysis_node.exec(result2)
                assert 'extracted_concepts' in exec_result2
                assert 'batch_metrics' in exec_result2
                
                post_result2 = pipeline.content_analysis_node.post(shared_state, result2, exec_result2)
                assert post_result2 == "default"
                assert 'extracted_concepts' in shared_state
                assert 'batch_metrics' in shared_state
                
                # Test Node 3: Knowledge Graph
                result3 = pipeline.knowledge_graph_node.prep(shared_state)
                assert 'concepts' in result3
                
                exec_result3 = pipeline.knowledge_graph_node.exec(result3)
                assert 'nodes_created' in exec_result3
                
                post_result3 = pipeline.knowledge_graph_node.post(shared_state, result3, exec_result3)
                assert post_result3 == "default"
                assert 'knowledge_graph' in shared_state
                
                # Test Node 4: Historical Knowledge Retrieval  
                result4 = pipeline.historical_knowledge_node.prep(shared_state)
                assert 'new_concepts' in result4
                
                exec_result4 = pipeline.historical_knowledge_node.exec(result4)
                assert 'direct_connections' in exec_result4
                
                post_result4 = pipeline.historical_knowledge_node.post(shared_state, result4, exec_result4)
                assert post_result4 == "default"
                assert 'historical_connections' in shared_state
                assert 'knowledge_gaps' in shared_state
                
                # Test Node 5: Notion Note Generation
                result5 = pipeline.notion_generation_node.prep(shared_state)
                assert 'topic_organization' in result5
                
                exec_result5 = pipeline.notion_generation_node.exec(result5)
                assert 'creation_summary' in exec_result5
                
                post_result5 = pipeline.notion_generation_node.post(shared_state, result5, exec_result5)
                assert post_result5 == "default"
                assert 'notion_generation' in shared_state

        except Exception as e:
            print(f"Error details: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise

    def test_complete_pipeline_execution(self, mock_environment, sample_learning_session, 
                                        mock_llm_responses, mock_neo4j, mock_notion_api, mock_llm_client):
        """Test complete pipeline execution end-to-end"""
        pipeline = NoteGenerationPipeline()
        
        # Mock all LLM clients and Notion components
        with patch('nodes.content_analysis.get_llm_client', return_value=mock_llm_client), \
             patch('nodes.historical_knowledge_retrieval.get_llm_client', return_value=mock_llm_client), \
             patch('nodes.notion_note_generation.get_llm_client', return_value=mock_llm_client), \
             patch.object(pipeline.notion_generation_node, 'content_enhancer') as mock_enhancer, \
             patch.object(pipeline.notion_generation_node, 'topic_organizer') as mock_organizer, \
             patch.object(pipeline.notion_generation_node, 'page_builder') as mock_page_builder, \
             patch.object(pipeline.notion_generation_node, 'block_builder') as mock_block_builder, \
             patch.object(pipeline.notion_generation_node, 'database_manager') as mock_db_manager, \
             patch.object(pipeline.notion_generation_node, 'notion_client') as mock_notion_client:
            
            # Set up LLM responses
            mock_llm_client.chat_completion.side_effect = [
                json.dumps(mock_llm_responses['content_analysis_batch']),
                json.dumps(mock_llm_responses['content_synthesis']),
                json.dumps(mock_llm_responses['historical_semantic_analysis']),
                json.dumps(mock_llm_responses['knowledge_gap_analysis'])
            ]
            
            # Mock Notion API operations
            mock_notion_client.test_connection.return_value = True
            mock_db_manager.ensure_enhanced_databases_exist.return_value = {
                'learning_sessions': 'db_session_123',
                'research_topics': 'db_topics_123',
                'concept_library': 'db_concepts_123'
            }
            
            mock_page_builder.create_enhanced_topic_page.return_value = {
                'id': 'page_123',
                'url': 'https://notion.so/page_123'
            }
            mock_page_builder.create_enhanced_master_session_page.return_value = {
                'id': 'master_page_123',
                'url': 'https://notion.so/master_page_123'
            }
            mock_page_builder.create_enhanced_concept_library_entries.return_value = [
                {'id': 'concept_123', 'name': 'machine learning'}
            ]
            mock_page_builder.get_page_url.return_value = 'https://notion.so/test_page'
            
            # Mock topic organization
            mock_organizer.intelligent_topic_clustering.return_value = {
                'Machine Learning': {
                    'topic_name': 'Machine Learning',
                    'concepts': ['machine learning', 'neural networks'],
                    'captures': sample_learning_session[:2],
                    'source_count': 2
                }
            }
            
            # Mock content enhancement
            mock_enhancer.generate_rich_topic_content.return_value = mock_llm_responses['notion_content_generation']
            mock_enhancer._generate_session_story.return_value = {
                'title': 'ML Learning Session',
                'story': 'You learned about machine learning',
                'spark': 'curiosity'
            }
            mock_enhancer._create_master_session_synthesis.return_value = mock_llm_responses['notion_session_synthesis']
            
            # Run complete pipeline
            result = pipeline.run(sample_learning_session)
            
            # Verify pipeline completion
            assert result is not None
            assert 'session_id' in result
            assert 'user_id' in result
            assert result['user_id'] == 'test_learner_123'
            
            # Verify all pipeline stages completed
            assert 'raw_captures' in result
            assert 'extracted_concepts' in result
            assert 'knowledge_graph' in result
            assert 'historical_connections' in result
            assert 'notion_generation' in result
            
            # Verify pipeline metadata
            metadata = result.get('pipeline_metadata', {})
            assert metadata['status'] == 'completed'
            assert 'start_time' in metadata
            assert 'end_time' in metadata
            
            # Verify batch optimization worked
            assert 'batch_metrics' in result
            batch_metrics = result['batch_metrics']
            assert 'total_captures_processed' in batch_metrics
            
            # Verify content analysis results
            concepts = result['extracted_concepts']
            assert 'learning_concepts' in concepts
            assert 'session_theme' in concepts
            assert len(concepts['learning_concepts']) > 0
            
            # Verify knowledge graph results
            kg = result['knowledge_graph']
            assert 'nodes_created' in kg
            assert 'relationships_created' in kg
            
            # Verify historical analysis results
            historical = result['historical_connections']
            assert 'total_connections_found' in historical
            
            # Verify Notion generation results
            notion = result['notion_generation']
            assert 'master_session_url' in notion
            assert 'creation_summary' in notion

    def test_pipeline_error_handling(self, mock_environment):
        """Test pipeline handles errors gracefully"""
        pipeline = NoteGenerationPipeline()
    
        # Test with invalid input
        with pytest.raises(ValueError, match="No input captures provided"):
            pipeline.run([])
    
        bad_input = [{"invalid": "data"}]
        result = pipeline.run(bad_input)
        assert result is not None

    def test_pipeline_orchestrator_integration(self, mock_environment, sample_learning_session, 
                                             mock_llm_responses, mock_neo4j, mock_notion_api, mock_llm_client):
        """Test pipeline orchestrator handles the full flow"""
        with patch('neo4j.GraphDatabase.driver') as mock_driver:
            mock_driver.return_value = mock_neo4j
        orchestrator = PipelineOrchestrator()
        
        # Mock the LLM responses and Notion operations
        with patch.object(orchestrator.pipeline.content_analysis_node, 'llm_client', mock_llm_client), \
             patch.object(orchestrator.pipeline.notion_generation_node, 'content_enhancer') as mock_enhancer, \
             patch.object(orchestrator.pipeline.notion_generation_node, 'topic_organizer') as mock_organizer, \
             patch.object(orchestrator.pipeline.notion_generation_node, 'notion_client') as mock_notion_client:

            orchestrator.pipeline.knowledge_graph_node.driver = mock_neo4j

            mock_llm_client.chat_completion.side_effect = [
                json.dumps(mock_llm_responses['content_analysis_batch']),
                json.dumps(mock_llm_responses['content_synthesis'])
            ]
            
            # Mock Notion operations
            mock_notion_client.test_connection.return_value = True
            mock_organizer.intelligent_topic_clustering.return_value = {}
            mock_enhancer.generate_rich_topic_content.return_value = {}
            
            # Test validation and processing
            result = orchestrator.run_pipeline(sample_learning_session)
            
            assert result['status'] == 'completed'
            assert 'session_id' in result
            assert 'learning_analysis' in result
            assert 'knowledge_insights' in result
            assert 'outputs' in result
            
            # Verify summary stats
            summary = result['summary']
            assert summary['captures_processed'] == 4
            assert 'concepts_extracted' in summary
            assert 'session_theme' in summary

    def test_api_server_integration(self, mock_environment, sample_learning_session):
        """Test API server handles complete pipeline flow"""
        with flask_app.test_client() as client:
            # Test health check
            response = client.get('/api/health')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            
            # Test batch processing
            batch_data = {
                'notes': [
                    {
                        'content': capture['content'],
                        'user_id': capture['user_id'],
                        'source_url': capture.get('source_url', ''),
                        'title': capture.get('title', '')
                    }
                    for capture in sample_learning_session
                ]
            }
            
            response = client.post('/api/notes/batch', 
                                 data=json.dumps(batch_data),
                                 content_type='application/json')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['notes_processed'] == 4

    def test_single_node_execution(self, mock_environment, sample_learning_session):
        """Test single node execution functionality"""
        pipeline = NoteGenerationPipeline()
        
        # Test capture ingestion only
        result = pipeline.run_single_node('capture_ingestion', sample_learning_session)
        
        assert 'raw_captures' in result
        assert len(result['raw_captures']) == 4
        assert result['pipeline_metadata']['test_mode'] is True

    def test_configuration_handling(self, mock_environment):
        """Test pipeline handles different configurations"""
        # Test with config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "logging": {
                    "log_level": "DEBUG"
                },
                "pipeline": {
                    "max_parallel_nodes": 1
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            pipeline = NoteGenerationPipeline(config_path)
            assert pipeline.config is not None
        finally:
            os.unlink(config_path)

    def test_edge_cases_and_robustness(self, mock_environment, mock_llm_client):
        """Test pipeline handles edge cases"""
        pipeline = NoteGenerationPipeline()
        
        # Test with minimal input
        minimal_input = [{
            "content": "Short content",
            "user_id": "test_user"
        }]
        
        with patch.object(pipeline.content_analysis_node, 'llm_client', mock_llm_client), \
             patch.object(pipeline.notion_generation_node, 'notion_client') as mock_notion_client:
            
            mock_llm_client.is_available.return_value = False  # Force fallback
            mock_notion_client.test_connection.return_value = True
            
            result = pipeline.run(minimal_input)
            assert result is not None
            assert 'raw_captures' in result


class TestPipelineComponents:
    """Test individual pipeline components in isolation"""
    
    def test_capture_ingestion_minimal_format(self):
        """Test capture ingestion handles minimal format correctly"""
        node = CaptureIngestionNode()
        
        minimal_input = [{
            "content": "Test content for learning",
            "user_id": "test_user_123"
        }]
        
        shared_state = {
            'session_id': 'test_session',
            'raw_input': minimal_input
        }
        
        prep_result = node.prep(shared_state)
        assert len(prep_result['captures_to_process']) == 1
        
        exec_result = node.exec(prep_result)
        assert len(exec_result['processed_captures']) == 1
        
        processed_capture = exec_result['processed_captures'][0]
        assert processed_capture['content'] == "Test content for learning"
        assert processed_capture['user_id'] == "test_user_123"
        assert 'metadata' in processed_capture

    def test_content_analysis_batch_optimization(self):
        """Test content analysis batch optimization works"""
        node = ContentAnalysisNode()
        
        # Create test captures
        captures = [
            {'id': f'capture_{i}', 'content': f'Test content {i}', 'metadata': {}}
            for i in range(10)
        ]
        
        shared_state = {'raw_captures': captures}
        
        with patch.object(node, 'llm_client') as mock_llm:
            mock_llm.is_available.return_value = True
            
            prep_result = node.prep(shared_state)
            assert 'batch_config' in prep_result
            
            # Should estimate fewer API calls due to batching
            estimated_calls = prep_result['batch_config']['estimated_api_calls']
            assert estimated_calls < len(captures)

    def test_knowledge_graph_persistence(self):
        """Test knowledge graph creates persistent nodes"""
        with patch('neo4j.GraphDatabase.driver') as mock_driver:
            mock_session = MagicMock()
            def mock_run(*args, **kwargs):
                mock_result = MagicMock()
                default_result = {
                    'session_id': 'test_session_123',
                    'session_count': 1,
                    'concept_count': 2,
                    'entity_count': 1,
                    'topic_count': 1,
                    'relationship_count': 4,
                    'resource_count': 0,
                    'node_count': 4,
                    'edge_count': 2,
                    'density': 0.25,
                    'id': 'test_id_123',
                    'count': 1,
                    'nodes_created': 5,
                    'relationships_created': 4
                }
                mock_result.single.return_value = default_result
                mock_result.data.return_value = [default_result]
                return mock_result
        
            mock_session.run.side_effect = mock_run
            
            mock_driver_instance = MagicMock()
            mock_driver_instance.session.return_value.__enter__.return_value = mock_session
            mock_driver_instance.session.return_value.__exit__.return_value = None
            mock_driver.return_value = mock_driver_instance
            
            node = KnowledgeGraphNode()
            
            concepts = {
                'learning_concepts': ['machine learning', 'neural networks'],
                'entities': {'Python': 'programming_language'},
                'topics': ['artificial intelligence']
            }
            
            shared_state = {
                'session_id': 'test_session',
                'extracted_concepts': concepts,
                'raw_captures': []
            }
            
            prep_result = node.prep(shared_state)
            exec_result = node.exec(prep_result)
            
            assert 'nodes_created' in exec_result
            assert exec_result['nodes_created']['concepts'] > 0

    def test_content_database_creation(self, mock_environment, mock_notion_api):
        """Test content database is created with correct schema"""
        from nodes.notion_note_generation import NotionDatabaseManager
        from nodes.notion.client import NotionClient
        
        with patch('nodes.notion.client.requests') as mock_requests:
            mock_requests.get.return_value.status_code = 200
            mock_requests.post.return_value.status_code = 200
            mock_requests.post.return_value.json.return_value = {'id': 'content_db_123'}
        
        client = NotionClient()
        manager = NotionDatabaseManager(client)
        
        databases = manager.ensure_enhanced_databases_exist()
        
        # Should now include content database
        assert 'captured_content' in databases
        assert len(databases) == 4  # sessions, topics, concepts, content

    
    def test_content_page_creation(self, mock_environment, sample_learning_session, mock_notion_api):
        """Test content pages are created for each capture"""
        from nodes.notion.page_builder import NotionPageBuilder
        from nodes.notion.client import NotionClient
        
        with patch('nodes.notion.client.requests') as mock_requests:
            mock_requests.post.return_value.status_code = 200
            mock_requests.post.return_value.json.return_value = {
                'id': 'content_page_123',
                'properties': {'Content Title': {'title': [{'plain_text': 'Test Title'}]}}
            }
            mock_requests.patch.return_value.status_code = 200
            
            client = NotionClient()
            builder = NotionPageBuilder(client)
            
            # Mock topic organization
            topic_org = {
                'Machine Learning': {
                    'captures': sample_learning_session[:2]
                }
            }
            
            content_pages = builder.create_content_pages(
                sample_learning_session, 
                'content_db_123', 
                topic_org
            )
            
            assert len(content_pages) == 4

    
    def test_topic_pages_include_full_content(self, mock_environment, sample_learning_session, mock_notion_api):
        """Test topic pages now include full content sections"""
        from nodes.notion.block_builder import NotionBlockBuilder
        from nodes.notion.client import NotionClient
        
        with patch('nodes.notion.client.requests') as mock_requests:
            mock_requests.patch.return_value.status_code = 200
            
            client = NotionClient()
            builder = NotionBlockBuilder(client)
            
            topic_data = {
                'captures': sample_learning_session[:2],
                'rich_content': {'learning_story': 'test story'}
            }
            
            content_pages = [{'id': 'content_123', 'properties': {'Content Title': {'title': [{'plain_text': 'ML Intro'}]}}}]
            
            # Should not raise errors
            builder.add_rich_topic_content_with_sources(
                'page_123',
                'Machine Learning', 
                topic_data,
                {'extracted_concepts': {}},
                content_pages,
                'blue'
            )
            
            # Verify content blocks were added
            mock_requests.patch.assert_called()
                



def test_main_pipeline_cli():
    """Test main.py CLI functionality"""
    # Test sample data creation
    sample_data = create_sample_minimal_input()
    assert len(sample_data) == 3
    assert all('content' in capture for capture in sample_data)
    assert all('user_id' in capture for capture in sample_data)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short", "-x"])