#!/usr/bin/env python3
"""
Enhanced Notion component tests with patterns extracted from legacy tests.
Tests database operations, page creation, and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from tests.fixtures.mock_responses import (
    create_advanced_notion_mock,
    create_error_scenario_mocks,
    create_fallback_behavior_mocks
)
from tests.fixtures.sample_data import create_sample_learning_session


class TestNotionDatabaseManager:
    """Test Notion database management with enhanced patterns."""

    @pytest.fixture
    def mock_environment(self):
        """Set up mock environment."""
        with patch.dict('os.environ', {'NOTION_TOKEN': 'test_token'}):
            yield

    @pytest.fixture
    def notion_mock(self):
        """Get advanced Notion API mock."""
        return create_advanced_notion_mock()

    def test_database_creation_with_advanced_mock(self, mock_environment, notion_mock):
        """Test database creation using advanced mock patterns."""
        from nodes.notion.database_manager import NotionDatabaseManager
        from nodes.notion.client import NotionClient
        
        with patch('requests.post', notion_mock['post']), \
             patch('requests.get', notion_mock['get']):
            
            client = NotionClient()
            manager = NotionDatabaseManager(client)
            
            databases = manager.ensure_enhanced_databases_exist()
            
            assert 'learning_sessions' in databases
            assert 'research_topics' in databases
            assert 'concept_library' in databases
            assert 'captured_content' in databases

    def test_database_search_and_fallback(self, mock_environment, notion_mock):
        """Test database search with fallback creation."""
        from nodes.notion.database_manager import NotionDatabaseManager
        from nodes.notion.client import NotionClient
        
        with patch('requests.post', notion_mock['post']), \
             patch('requests.get', notion_mock['get']):
            
            client = NotionClient()
            manager = NotionDatabaseManager(client)
            
            # Test database creation via ensure_enhanced_databases_exist
            databases = manager.ensure_enhanced_databases_exist()
            assert 'learning_sessions' in databases

    def test_error_handling_in_database_operations(self, mock_environment):
        """Test error handling in database operations."""
        from nodes.notion.database_manager import NotionDatabaseManager
        from nodes.notion.client import NotionClient
        
        error_scenarios = create_error_scenario_mocks()
        
        with patch('requests.post') as mock_post:
            # Simulate Notion API error
            mock_post.side_effect = Exception("API Error")
            
            client = NotionClient()
            manager = NotionDatabaseManager(client)
            
            with pytest.raises(Exception):
                manager.ensure_enhanced_databases_exist()


class TestNotionPageBuilder:
    """Test Notion page building with enhanced patterns."""

    @pytest.fixture
    def mock_environment(self):
        """Set up mock environment."""
        with patch.dict('os.environ', {'NOTION_TOKEN': 'test_token'}):
            yield

    @pytest.fixture
    def notion_mock(self):
        """Get advanced Notion API mock."""
        return create_advanced_notion_mock()

    def test_content_page_creation_patterns(self, mock_environment, notion_mock):
        """Test content page creation using extracted patterns."""
        from nodes.notion.page_builder import NotionPageBuilder
        from nodes.notion.client import NotionClient
        
        with patch('requests.post', notion_mock['post']), \
             patch('requests.patch', notion_mock['patch']):
            
            client = NotionClient()
            builder = NotionPageBuilder(client)
            
            # Mock the client's create_page method directly
            with patch.object(client, 'create_page') as mock_create_page:
                mock_create_page.return_value = {'id': 'test_page_123'}
                
                captures = create_sample_learning_session()
                topic_org = {
                    'Machine Learning': {
                        'captures': captures[:2]
                    }
                }
                
                content_pages = builder.create_content_pages(
                    captures, 'content_db_123', topic_org
                )
                
                assert len(content_pages) == len(captures)
                assert all('id' in page for page in content_pages)

    def test_content_type_classification_patterns(self, mock_environment):
        """Test content type classification with diverse patterns."""
        from nodes.notion.page_builder import NotionPageBuilder
        from nodes.notion.client import NotionClient
        
        builder = NotionPageBuilder(NotionClient())
        
        test_cases = [
            {
                'url': 'https://docs.python.org/3/tutorial/',
                'content': 'official documentation tutorial guide getting started installation usage',
                'title': 'Python Documentation Tutorial',
                'metadata': {'domain': 'docs.python.org'}
            },
            {
                'url': 'https://arxiv.org/abs/2010.11929',
                'content': 'abstract introduction methodology results conclusion research study experiment',
                'title': 'Research Paper on Machine Learning',
                'metadata': {'domain': 'arxiv.org'}
            },
            {
                'url': 'https://medium.com/towards-data-science/ml-guide',
                'content': 'my experience with machine learning journey blog thoughts opinion',
                'title': 'My ML Journey',
                'metadata': {'domain': 'medium.com'}
            },
            {
                'url': 'https://example.com/how-to-python',
                'content': 'step by step tutorial learn python programming how to build create',
                'title': 'How to Python',
                'metadata': {'domain': 'example.com'}
            }
        ]
        
        # Test that classification returns valid content types
        valid_types = ['Tutorial', 'Documentation', 'Research Paper', 'Blog Post', 'Article']
        
        for case in test_cases:
            result = builder._classify_content_type(case)
            assert result in valid_types

    def test_enhanced_topic_page_creation(self, mock_environment, notion_mock):
        """Test enhanced topic page creation patterns."""
        from nodes.notion.page_builder import NotionPageBuilder  
        from nodes.notion.client import NotionClient
        
        with patch('requests.post', notion_mock['post']), \
             patch('requests.patch', notion_mock['patch']):
            
            client = NotionClient()
            builder = NotionPageBuilder(client)
            
            enhanced_data = {
                'complexity': 'Intermediate',
                'concepts': ['machine learning', 'neural networks'],
                'practical_applications': ['image recognition'],
                'learning_sequence': ['basics', 'implementation']
            }
            
            rich_content = {
                'executive_summary': {'overview': 'Test overview'},
                'concepts_deep_dive': {'concepts': []},
                'practical_applications': {'applications': []}
            }
            
            pipeline_data = {
                'knowledge_gaps': [],
                'extracted_concepts': {
                    'key_terms': {
                        'machine learning': 'AI subset focused on learning from data'
                    }
                }
            }
            
            result = builder.create_enhanced_topic_page(
                'Machine Learning', enhanced_data, rich_content, 
                'topics_db_123', pipeline_data
            )
            
            assert 'id' in result
            assert result['id'] == 'test_page_456'


class TestNotionClientFallbacks:
    """Test Notion client fallback behaviors."""

    @pytest.fixture
    def fallback_mocks(self):
        """Get fallback behavior mocks."""
        return create_fallback_behavior_mocks()

    def test_connection_failure_handling(self, fallback_mocks):
        """Test Notion API connection failure scenarios."""
        notion_api = fallback_mocks['notion_api']
        
        # Test offline scenario
        notion_api.set_connection_status('offline')
        with pytest.raises(ConnectionError):
            notion_api.post('test_endpoint')
        
        # Test timeout scenario
        notion_api.set_connection_status('timeout')
        with pytest.raises(TimeoutError):
            notion_api.post('test_endpoint')
        
        # Test rate limiting
        notion_api.set_connection_status('rate_limited')
        response = notion_api.post('test_endpoint')
        assert response.status_code == 429

    def test_graceful_recovery_patterns(self, fallback_mocks):
        """Test graceful recovery from API failures."""
        notion_api = fallback_mocks['notion_api']
        
        # Start with failure
        notion_api.set_connection_status('offline')
        with pytest.raises(ConnectionError):
            notion_api.post('test_endpoint')
        
        # Recover to healthy state
        notion_api.set_connection_status('healthy')
        response = notion_api.post('test_endpoint')
        assert response.status_code == 200
        assert response.json()['id'] == 'test_success'


class TestNotionIntegrationPatterns:
    """Test advanced integration patterns extracted from legacy tests."""

    def test_database_schema_completeness(self):
        """Test that all required databases are included in schemas."""
        from nodes.notion.database_manager import NotionDatabaseManager
        from nodes.notion.client import NotionClient
        
        with patch.dict('os.environ', {'NOTION_TOKEN': 'test_token'}):
            manager = NotionDatabaseManager(NotionClient())
            schemas = manager.database_schemas
            
            expected_databases = [
                'learning_sessions', 'research_topics', 
                'concept_library', 'captured_content'
            ]
            
            for db_name in expected_databases:
                assert db_name in schemas
                assert 'properties' in schemas[db_name]
                
            # Test content database specific properties
            content_schema = schemas['captured_content']
            required_props = ['Content Title', 'Source URL', 'Content Type', 'Related Topics']
            for prop in required_props:
                assert prop in content_schema['properties']

    def test_page_url_generation_patterns(self):
        """Test page URL generation with various input patterns."""
        from nodes.notion.page_builder import NotionPageBuilder
        from nodes.notion.client import NotionClient
        
        with patch.dict('os.environ', {'NOTION_TOKEN': 'test_token'}):
            builder = NotionPageBuilder(NotionClient())
            
            test_cases = [
                ({'id': 'test-page-123-456-789'}, 'https://notion.so/testpage123456789'),
                ({'id': 'simple-id'}, 'https://notion.so/simpleid'),
                ({}, ''),
                (None, '')
            ]
            
            for page_data, expected_url in test_cases:
                result = builder.get_page_url(page_data)
                assert result == expected_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])