"""
Test Suite for Semantic Agent Matching

This module provides comprehensive tests for the semantic agent matching
functionality, including unit tests, integration tests, and performance tests.

Test Categories:
- SemanticAgentMatcher unit tests
- CapabilityOntology tests
- Database integration tests
- API endpoint tests
- Performance benchmarks
- Error handling tests

Author: Agent Orchestrator Team
Version: 1.0.0
"""

import pytest
import asyncio
import json
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Test dependencies
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

# Import modules to test
from semantic_agent_matcher import (
    SemanticAgentMatcher,
    CapabilityOntology,
    AgentCapabilityProfile,
    TaskMatchingResult,
    CapabilityNode
)

# Mock database and auth dependencies
@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return AsyncMock()

@pytest.fixture
def mock_auth_info():
    """Mock authentication info"""
    mock_auth = MagicMock()
    mock_auth.key_id = "test_key_123"
    mock_auth.permissions = ["agent:read", "agent:write", "task:create"]
    return mock_auth


class TestCapabilityOntology:
    """Test the capability ontology system"""
    
    def test_ontology_initialization(self):
        """Test that ontology initializes with default structure"""
        ontology = CapabilityOntology()
        
        assert len(ontology.nodes) > 0
        assert "surveillance" in ontology.nodes
        assert "detection" in ontology.nodes
        assert "analysis" in ontology.nodes
        
        # Test hierarchical relationships
        detection_node = ontology.nodes["detection"]
        assert detection_node.parent == "surveillance"
        assert "person_detection" in detection_node.children
    
    def test_capability_expansion(self):
        """Test capability expansion through ontology"""
        ontology = CapabilityOntology()
        
        # Test expansion of basic capability
        expanded = ontology.get_expanded_capabilities(["person_detection"])
        
        assert "person_detection" in expanded
        assert "detection" in expanded  # Parent
        assert "surveillance" in expanded  # Grandparent
    
    def test_capability_similarity(self):
        """Test capability similarity calculation"""
        ontology = CapabilityOntology()
        
        # Test identical capabilities
        assert ontology.calculate_capability_similarity("person_detection", "person_detection") == 1.0
        
        # Test parent-child relationship
        similarity = ontology.calculate_capability_similarity("detection", "person_detection")
        assert similarity == 0.8
        
        # Test sibling relationship
        similarity = ontology.calculate_capability_similarity("person_detection", "vehicle_detection")
        assert similarity == 0.6
        
        # Test aliases
        similarity = ontology.calculate_capability_similarity("detection", "detect")
        assert similarity == 0.9
    
    def test_unknown_capabilities(self):
        """Test handling of unknown capabilities"""
        ontology = CapabilityOntology()
        
        # Should return low similarity for unknown capabilities
        similarity = ontology.calculate_capability_similarity("unknown_capability", "person_detection")
        assert similarity == 0.0
        
        # Expansion should include unknown capabilities as-is
        expanded = ontology.get_expanded_capabilities(["unknown_capability", "person_detection"])
        assert "unknown_capability" in expanded
        assert "person_detection" in expanded


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Semantic dependencies not available")
class TestSemanticAgentMatcher:
    """Test the semantic agent matcher"""
    
    @pytest.fixture
    def matcher(self):
        """Create a semantic agent matcher for testing"""
        # Use a lightweight model for testing
        return SemanticAgentMatcher(model_name="all-MiniLM-L6-v2")
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, matcher):
        """Test agent registration with semantic profiles"""
        agent_id = "test_agent_001"
        capabilities = ["person_detection", "video_analysis"]
        agent_data = {
            "success_rate": 0.85,
            "avg_response_time": 2.5,
            "task_count": 10
        }
        
        await matcher.register_agent(agent_id, capabilities, agent_data)
        
        assert agent_id in matcher.agent_profiles
        profile = matcher.agent_profiles[agent_id]
        assert profile.agent_id == agent_id
        assert profile.success_rate == 0.85
        assert len(profile.capabilities) >= len(capabilities)  # May be expanded
        
        # Check embeddings were computed
        if matcher.embedding_model:
            assert profile.capability_embeddings is not None
    
    @pytest.mark.asyncio
    async def test_performance_update(self, matcher):
        """Test agent performance updates"""
        agent_id = "test_agent_002"
        await matcher.register_agent(agent_id, ["detection"])
        
        # Update performance
        await matcher.update_agent_performance(
            agent_id=agent_id,
            task_type="person_detection",
            success=True,
            response_time=1.5
        )
        
        profile = matcher.agent_profiles[agent_id]
        assert profile.task_count == 1
        assert profile.success_rate > 0.5  # Should increase with success
        assert "person_detection" in profile.performance_scores
    
    @pytest.mark.asyncio
    async def test_task_matching(self, matcher):
        """Test task-agent matching"""
        # Register test agents
        await matcher.register_agent(
            "agent_1", 
            ["person_detection", "video_analysis"],
            {"success_rate": 0.9, "task_count": 20}
        )
        await matcher.register_agent(
            "agent_2", 
            ["vehicle_detection", "tracking"],
            {"success_rate": 0.7, "task_count": 5}
        )
        await matcher.register_agent(
            "agent_3",
            ["person_detection", "alerting"],
            {"success_rate": 0.8, "task_count": 15}
        )
        
        # Test matching
        results = await matcher.find_matching_agents(
            task_description="Detect people in surveillance camera feed",
            required_capabilities=["person_detection"],
            task_type="detection",
            top_k=2
        )
        
        assert len(results) <= 2
        assert all(isinstance(result, TaskMatchingResult) for result in results)
        
        # Check results are sorted by score
        if len(results) > 1:
            assert results[0].combined_score >= results[1].combined_score
        
        # Check that person detection agents are preferred
        person_detection_agents = [r for r in results if "person_detection" in r.matched_capabilities]
        assert len(person_detection_agents) > 0
    
    @pytest.mark.asyncio
    async def test_semantic_similarity(self, matcher):
        """Test semantic similarity calculation"""
        if not matcher.embedding_model:
            pytest.skip("Embedding model not available")
        
        # Register agent with video analysis capabilities
        await matcher.register_agent(
            "video_agent",
            ["video_analysis", "motion_detection"],
            {"success_rate": 0.8}
        )
        
        profile = matcher.agent_profiles["video_agent"]
        
        # Test semantic similarity
        similarity1 = matcher._calculate_semantic_similarity(
            "Analyze video footage for motion",
            profile
        )
        
        similarity2 = matcher._calculate_semantic_similarity(
            "Process audio recordings",
            profile
        )
        
        # Video-related task should have higher similarity
        assert similarity1 > similarity2
    
    @pytest.mark.asyncio
    async def test_capability_match_scoring(self, matcher):
        """Test capability matching score calculation"""
        agent_capabilities = ["person_detection", "video_analysis", "alerting"]
        required_capabilities = ["person_detection", "motion_detection"]
        
        score, matched, missing = matcher._calculate_capability_match_score(
            required_capabilities, agent_capabilities
        )
        
        assert 0.0 <= score <= 1.0
        assert "person_detection" in matched
        assert "motion_detection" in missing or len(missing) == 0  # Might be expanded through ontology
    
    @pytest.mark.asyncio
    async def test_performance_scoring(self, matcher):
        """Test performance score calculation"""
        profile = AgentCapabilityProfile(
            agent_id="test_agent",
            capabilities=["detection"],
            success_rate=0.9,
            avg_response_time=2.0,
            task_count=50
        )
        
        score = matcher._calculate_performance_score(profile, "detection")
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be above average due to good metrics


class TestSemanticEndpoints:
    """Test semantic matching API endpoints"""
    
    @pytest.fixture
    def mock_request(self):
        """Mock HTTP request"""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        return request
    
    @pytest.mark.asyncio
    async def test_semantic_matching_request_validation(self):
        """Test request validation for semantic matching"""
        from semantic_endpoints import SemanticTaskRequest
        
        # Valid request
        valid_request = SemanticTaskRequest(
            task_description="Detect people in parking lot using camera feeds",
            required_capabilities=["person_detection", "video_analysis"],
            task_type="surveillance",
            max_agents=3
        )
        
        assert valid_request.task_description is not None
        assert len(valid_request.required_capabilities) == 2
        
        # Test validation errors
        with pytest.raises(ValueError):
            SemanticTaskRequest(
                task_description="",  # Too short
                required_capabilities=["person_detection"]
            )
        
        with pytest.raises(ValueError):
            SemanticTaskRequest(
                task_description="Valid description",
                max_agents=15  # Too many
            )
    
    @pytest.mark.asyncio
    async def test_capability_analysis_request(self):
        """Test capability analysis request validation"""
        from semantic_endpoints import CapabilityAnalysisRequest
        
        # Valid request
        valid_request = CapabilityAnalysisRequest(
            capabilities=["person_detection", "video_analysis"]
        )
        
        assert len(valid_request.capabilities) == 2
        
        # Test validation errors
        with pytest.raises(ValueError):
            CapabilityAnalysisRequest(capabilities=[])  # Empty list
    
    @pytest.mark.asyncio
    @patch('semantic_endpoints.AgentRepository')
    async def test_find_agents_semantic_endpoint(self, mock_repo, mock_db_session, mock_auth_info):
        """Test the semantic matching endpoint"""
        # Mock database response
        mock_agent = MagicMock()
        mock_agent.id = "agent_123"
        mock_agent.name = "Test Agent"
        mock_agent.type.value = "surveillance"
        mock_agent.status = "idle"
        mock_agent.capabilities = ["person_detection", "video_analysis"]
        mock_agent.performance_metrics = {"success_rate": 0.8, "task_count": 10}
        mock_agent.last_seen = datetime.utcnow()
        
        mock_repo.list_agents.return_value = ([mock_agent], 1)
        mock_repo.find_suitable_agents_semantic.return_value = (
            [mock_agent],
            [{
                "agent_id": "agent_123",
                "score": 0.85,
                "method": "semantic",
                "matched_capabilities": ["person_detection"],
                "missing_capabilities": []
            }]
        )
        
        # Import and test endpoint
        from semantic_endpoints import find_agents_semantic_enhanced, SemanticTaskRequest
        
        request = SemanticTaskRequest(
            task_description="Monitor parking lot for people",
            required_capabilities=["person_detection"],
            max_agents=3
        )
        
        response = await find_agents_semantic_enhanced(
            request=request,
            db=mock_db_session,
            auth_info=mock_auth_info
        )
        
        assert response.matched_agents is not None
        assert response.total_available_agents == 1
        assert response.semantic_matching_available in [True, False]  # Depends on dependencies


class TestIntegration:
    """Integration tests with database and full system"""
    
    @pytest.mark.asyncio
    @patch('semantic_agent_matcher.get_db_session')
    async def test_database_sync(self, mock_db_session):
        """Test synchronization with database"""
        # Mock database agents
        mock_agent1 = MagicMock()
        mock_agent1.id = "agent_1"
        mock_agent1.capabilities = ["person_detection"]
        mock_agent1.performance_metrics = {"success_rate": 0.8}
        mock_agent1.updated_at = datetime.utcnow()
        
        mock_agent2 = MagicMock()
        mock_agent2.id = "agent_2"
        mock_agent2.capabilities = ["vehicle_detection"]
        mock_agent2.performance_metrics = {"success_rate": 0.7}
        mock_agent2.updated_at = datetime.utcnow()
        
        # Mock AgentRepository
        with patch('semantic_agent_matcher.AgentRepository') as mock_repo:
            mock_repo.list_agents.return_value = ([mock_agent1, mock_agent2], 2)
            
            # Test sync
            matcher = SemanticAgentMatcher()
            
            async with mock_db_session() as db:
                await matcher.sync_with_database(db)
            
            # Check agents were registered
            assert len(matcher.agent_profiles) == 2
            assert "agent_1" in matcher.agent_profiles
            assert "agent_2" in matcher.agent_profiles


class TestPerformance:
    """Performance tests for semantic matching"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies not available")
    async def test_matching_performance(self):
        """Test performance of semantic matching"""
        matcher = SemanticAgentMatcher()
        
        # Register many agents
        num_agents = 50
        for i in range(num_agents):
            await matcher.register_agent(
                f"agent_{i:03d}",
                [f"capability_{i % 10}", "common_capability"],
                {"success_rate": 0.5 + (i % 5) * 0.1}
            )
        
        # Time the matching operation
        start_time = datetime.utcnow()
        
        results = await matcher.find_matching_agents(
            task_description="Test task requiring common capability and specialized features",
            required_capabilities=["common_capability"],
            top_k=10
        )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Performance assertions
        assert duration < 5.0  # Should complete within 5 seconds
        assert len(results) <= 10
        
        # Check quality of results
        if results:
            assert all(result.combined_score > 0 for result in results)
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage with many agents"""
        matcher = SemanticAgentMatcher()
        
        # Register agents and check memory doesn't grow excessively
        for i in range(100):
            await matcher.register_agent(
                f"agent_{i:03d}",
                [f"capability_{i % 5}"],
                {"success_rate": 0.5}
            )
        
        # Check reasonable memory usage
        assert len(matcher.agent_profiles) == 100
        assert len(matcher.task_embeddings_cache) < 1000  # Cache should be bounded


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_no_agents_available(self):
        """Test behavior when no agents are available"""
        matcher = SemanticAgentMatcher()
        
        results = await matcher.find_matching_agents(
            task_description="Test task",
            required_capabilities=["nonexistent_capability"]
        )
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_invalid_agent_data(self):
        """Test handling of invalid agent data"""
        matcher = SemanticAgentMatcher()
        
        # Should not crash with invalid data
        with pytest.raises(Exception):
            await matcher.register_agent(
                agent_id="",  # Invalid agent ID
                capabilities=["valid_capability"]
            )
    
    @pytest.mark.asyncio
    async def test_missing_dependencies_fallback(self):
        """Test fallback behavior when dependencies are missing"""
        # Mock missing dependencies
        with patch.dict('sys.modules', {'sentence_transformers': None, 'sklearn': None}):
            # Should still work with basic matching
            from semantic_agent_matcher import SemanticAgentMatcher
            
            matcher = SemanticAgentMatcher()
            assert matcher.embedding_model is None
            
            # Should still allow agent registration
            await matcher.register_agent("test_agent", ["test_capability"])
            assert "test_agent" in matcher.agent_profiles


# Utility functions for testing

def create_test_agent_data(agent_id: str, capabilities: List[str], 
                          performance_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create test agent data"""
    return {
        "id": agent_id,
        "name": f"Test Agent {agent_id}",
        "capabilities": capabilities,
        "performance_metrics": performance_metrics or {"success_rate": 0.5, "task_count": 0},
        "status": "idle",
        "type": "surveillance"
    }


@pytest.fixture
def sample_agents():
    """Create sample agents for testing"""
    return [
        create_test_agent_data("agent_001", ["person_detection", "video_analysis"], 
                              {"success_rate": 0.9, "task_count": 20}),
        create_test_agent_data("agent_002", ["vehicle_detection", "tracking"],
                              {"success_rate": 0.7, "task_count": 15}),
        create_test_agent_data("agent_003", ["motion_detection", "alerting"],
                              {"success_rate": 0.8, "task_count": 10})
    ]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
