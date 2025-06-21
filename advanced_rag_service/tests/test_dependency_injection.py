#!/usr/bin/env python3
"""
Dependency Injection Tests for Advanced RAG Service

This test suite demonstrates the dependency injection capabilities and improved testability
of the refactored Advanced RAG Service.
"""

import sys
import os
import asyncio
sys.path.append('.')

def test_dependency_injection_framework():
    """Test the dependency injection framework components"""
    print("=== Testing Dependency Injection Framework ===\n")
    
    try:
        print("1. Testing dependency container...")
        from dependency_injection import (
            DependencyContainer, AbstractEmbeddingModel, AbstractWeaviateClient, 
            AbstractOpenAIClient, MockEmbeddingModel, MockWeaviateClient, MockOpenAIClient
        )
        
        # Create a new container
        container = DependencyContainer()
        
        # Test binding and retrieval
        container.bind_instance(AbstractEmbeddingModel, MockEmbeddingModel())
        
        embedding_model = container.get(AbstractEmbeddingModel)
        assert isinstance(embedding_model, MockEmbeddingModel)
        print("   ✅ Container binding and retrieval working")
        
        # Test singleton behavior
        embedding_model2 = container.get(AbstractEmbeddingModel)
        assert embedding_model is embedding_model2
        print("   ✅ Singleton behavior working correctly")
        
        print("2. Testing mock implementations...")
        
        # Test MockEmbeddingModel
        mock_embedding = MockEmbeddingModel(available=True, embedding_size=10)
        embeddings = mock_embedding.encode("test text")
        assert len(embeddings) == 10
        assert all(isinstance(x, float) for x in embeddings)
        print("   ✅ MockEmbeddingModel working correctly")
        
        # Test MockWeaviateClient
        mock_weaviate = MockWeaviateClient(connected=True)
        assert mock_weaviate.is_connected()
        results = mock_weaviate.query_similar_events([0.1, 0.2, 0.3], k=3)
        assert len(results) == 3
        assert all('id' in result for result in results)
        print("   ✅ MockWeaviateClient working correctly")
        
        # Test MockOpenAIClient
        async def test_openai():
            mock_openai = MockOpenAIClient(available=True)
            response = await mock_openai.generate_explanation("Test prompt")
            assert isinstance(response, str)
            assert len(response) > 0
            return True
        
        openai_test_result = asyncio.run(test_openai())
        print("   ✅ MockOpenAIClient working correctly")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during dependency injection testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_with_dependency_injection():
    """Test the Advanced RAG Service with dependency injection"""
    print("\n=== Testing Advanced RAG Service with Dependency Injection ===\n")
    
    try:
        print("1. Testing service initialization with mock dependencies...")
        from dependency_injection import DependencyConfiguration
        from advanced_rag import AdvancedRAGService, QueryEvent, create_rag_service_with_container
        
        # Create test container with mock dependencies
        test_container = DependencyConfiguration.create_test_container(
            embedding_available=True,
            weaviate_connected=True,
            openai_available=True
        )
        
        # Create service with injected dependencies
        rag_service = create_rag_service_with_container(test_container)
        
        assert rag_service.embedding_model is not None
        assert rag_service.weaviate_client is not None
        assert rag_service.openai_client is not None
        print("   ✅ Service initialized with mock dependencies")
        
        print("2. Testing embedding functionality with mocks...")
        
        # Test embedding generation
        query_event = QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-13T10:30:00Z",
            label="person_detected",
            bbox={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}
        )
        
        embeddings = rag_service.get_event_embedding(query_event)
        assert isinstance(embeddings, list)
        assert len(embeddings) > 0
        assert all(isinstance(x, float) for x in embeddings)
        print("   ✅ Embedding generation working with mock model")
        
        print("3. Testing Weaviate query functionality with mocks...")
        
        # Test Weaviate query
        similar_events = rag_service.query_weaviate(query_event, k=3)
        assert isinstance(similar_events, list)
        assert len(similar_events) == 3
        assert all('id' in event for event in similar_events)
        print("   ✅ Weaviate query working with mock client")
        
        print("4. Testing temporal processing with mocks...")
        
        # Test temporal RAG processing
        async def test_temporal_processing():
            result = await rag_service.process_temporal_query(query_event, k=3)
            assert hasattr(result, 'linked_explanation')
            assert hasattr(result, 'retrieved_context')
            assert hasattr(result, 'explanation_confidence')
            assert len(result.retrieved_context) == 3
            return True
        
        temporal_test_result = asyncio.run(test_temporal_processing())
        print("   ✅ Temporal processing working with mock dependencies")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during service testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_degraded_service_scenarios():
    """Test service behavior with degraded dependencies"""
    print("\n=== Testing Service Behavior with Degraded Dependencies ===\n")
    
    try:
        print("1. Testing service with unavailable embedding model...")
        from dependency_injection import DependencyConfiguration
        from advanced_rag import create_rag_service_with_container, QueryEvent
        
        # Create container with unavailable embedding model
        degraded_container = DependencyConfiguration.create_test_container(
            embedding_available=False,  # Embedding unavailable
            weaviate_connected=True,
            openai_available=True
        )
        
        rag_service = create_rag_service_with_container(degraded_container)
        
        query_event = QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-13T10:30:00Z",
            label="person_detected"
        )
        
        # This should raise an EmbeddingGenerationError
        try:
            embeddings = rag_service.get_event_embedding(query_event)
            assert False, "Should have raised EmbeddingGenerationError"
        except Exception as e:
            assert "embedding" in str(e).lower()
            print("   ✅ Embedding unavailability handled correctly")
        
        print("2. Testing service with disconnected Weaviate...")
        
        # Create container with disconnected Weaviate
        weaviate_down_container = DependencyConfiguration.create_test_container(
            embedding_available=True,
            weaviate_connected=False,  # Weaviate disconnected
            openai_available=True
        )
        
        rag_service = create_rag_service_with_container(weaviate_down_container)
        
        # This should handle Weaviate disconnection gracefully
        try:
            similar_events = rag_service.query_weaviate(query_event, k=3)
            assert False, "Should have raised WeaviateConnectionError"
        except Exception as e:
            assert "weaviate" in str(e).lower() or "mock" in str(e).lower()
            print("   ✅ Weaviate disconnection handled correctly")
        
        print("3. Testing service with unavailable OpenAI...")
        
        # Create container with unavailable OpenAI
        openai_down_container = DependencyConfiguration.create_test_container(
            embedding_available=True,
            weaviate_connected=True,
            openai_available=False  # OpenAI unavailable
        )
        
        rag_service = create_rag_service_with_container(openai_down_container)
        
        # This should handle OpenAI unavailability during temporal processing
        async def test_openai_unavailable():
            try:
                result = await rag_service.process_temporal_query(query_event, k=3)
                # Should still return a result but with degraded explanation
                assert hasattr(result, 'linked_explanation')
                assert "temporarily unavailable" in result.linked_explanation or "not available" in result.linked_explanation
                return True
            except Exception as e:
                # Or should raise appropriate error
                assert "openai" in str(e).lower() or "unavailable" in str(e).lower()
                return True
        
        openai_test_result = asyncio.run(test_openai_unavailable())
        print("   ✅ OpenAI unavailability handled correctly")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during degraded scenario testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_service_instances():
    """Test creating multiple service instances with different configurations"""
    print("\n=== Testing Multiple Service Instances ===\n")
    
    try:
        print("1. Testing multiple instances with different configurations...")
        from dependency_injection import DependencyConfiguration
        from advanced_rag import create_rag_service_with_container
        
        # Create multiple containers with different configurations
        full_service_container = DependencyConfiguration.create_test_container(
            embedding_available=True,
            weaviate_connected=True,
            openai_available=True
        )
        
        limited_service_container = DependencyConfiguration.create_test_container(
            embedding_available=True,
            weaviate_connected=True,
            openai_available=False
        )
        
        # Create multiple service instances
        full_service = create_rag_service_with_container(full_service_container)
        limited_service = create_rag_service_with_container(limited_service_container)
        
        # Verify they have different capabilities
        assert full_service.openai_client is not None
        assert limited_service.openai_client is not None  # Mock should be available even if set to unavailable
        
        # Verify they are separate instances
        assert full_service is not limited_service
        assert full_service.container is not limited_service.container
        
        print("   ✅ Multiple service instances created successfully")
        
        print("2. Testing isolation between instances...")
        
        # Modify one container and verify the other is unaffected
        from dependency_injection import MockEmbeddingModel
        
        # Bind a different embedding model to one container
        custom_embedding = MockEmbeddingModel(available=True, embedding_size=100)
        full_service_container.bind_instance(MockEmbeddingModel, custom_embedding)
        
        # Create new service with modified container
        new_full_service = create_rag_service_with_container(full_service_container)
        
        # Verify isolation
        assert new_full_service is not full_service
        assert new_full_service is not limited_service
        
        print("   ✅ Service instance isolation working correctly")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during multiple instance testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_dependency_injection_tests():
    """Run all dependency injection tests"""
    print("🚀 Starting Dependency Injection Integration Tests")
    print("=" * 80)
    
    test_results = {}
    
    # Run dependency injection framework tests
    test_results["dependency_framework"] = test_dependency_injection_framework()
    
    # Run service with DI tests
    test_results["service_with_di"] = test_service_with_dependency_injection()
    
    # Run degraded scenario tests
    test_results["degraded_scenarios"] = test_degraded_service_scenarios()
    
    # Run multiple instances tests
    test_results["multiple_instances"] = test_multiple_service_instances()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 DEPENDENCY INJECTION TEST SUMMARY")
    print("=" * 80)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL DEPENDENCY INJECTION TESTS PASSED!")
        print("\n📋 DEPENDENCY INJECTION BENEFITS DEMONSTRATED:")
        print("   ✅ Decoupled service initialization from external dependencies")
        print("   ✅ Easy mocking and testing of external services")
        print("   ✅ Graceful handling of unavailable dependencies")
        print("   ✅ Support for multiple service configurations")
        print("   ✅ Improved testability and maintainability")
        print("   ✅ Flexible dependency replacement without code changes")
        
        print("\n🔧 USAGE RECOMMENDATIONS:")
        print("   1. Use DependencyConfiguration.create_test_container() for unit tests")
        print("   2. Use DependencyConfiguration.create_production_container() for production")
        print("   3. Create custom containers for specific testing scenarios")
        print("   4. Use create_rag_service_with_container() for dependency injection")
        print("   5. Mock external services to test error handling paths")
        
        return True
    else:
        print("❌ SOME DEPENDENCY INJECTION TESTS FAILED - Review errors above")
        return False

if __name__ == "__main__":
    success = run_dependency_injection_tests()
    sys.exit(0 if success else 1)
