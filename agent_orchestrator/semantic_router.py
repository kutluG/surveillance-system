"""
Semantic Agent Matching Router

This module provides FastAPI router integration for semantic agent matching
endpoints. It integrates the enhanced semantic matching capabilities with
the existing agent orchestrator API structure.

Features:
- Semantic agent matching endpoints
- Capability analysis and ontology exploration
- Performance tracking and learning
- Comprehensive API documentation
- Authentication and authorization
- Error handling and validation

Author: Agent Orchestrator Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging

from semantic_endpoints import (
    SemanticTaskRequest,
    SemanticMatchingResponse,
    CapabilityAnalysisRequest,
    CapabilityAnalysisResponse,
    AgentPerformanceUpdate,
    find_agents_semantic_enhanced,
    analyze_capabilities_enhanced,
    update_agent_performance_enhanced,
    get_semantic_matching_status
)
from auth import APIKeyInfo, require_permission

logger = logging.getLogger(__name__)

# Create semantic matching router
semantic_router = APIRouter(
    prefix="/api/v2/semantic",
    tags=["Semantic Agent Matching"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)


@semantic_router.post(
    "/agents/match",
    response_model=SemanticMatchingResponse,
    summary="Find Agents Using Semantic Matching",
    description="""
    **Find the best matching agents for a task using advanced semantic analysis.**
    
    This endpoint uses vector embeddings and capability ontology to find agents that
    best match a natural language task description. It provides detailed scoring,
    confidence metrics, and matching explanations.
    
    ## Features
    - **Vector Embeddings**: Uses sentence transformers for semantic similarity
    - **Capability Ontology**: Hierarchical capability matching with inheritance
    - **Performance Weighting**: Considers agent historical performance
    - **Dynamic Learning**: Adapts based on agent performance feedback
    - **Comprehensive Scoring**: Multiple scoring dimensions with explanations
    
    ## Scoring Methodology
    - **Capability Match**: How well agent capabilities match requirements
    - **Semantic Similarity**: Vector similarity between task and agent profile
    - **Performance Score**: Based on success rate, response time, and experience
    - **Combined Score**: Weighted combination of all factors
    
    ## Example Usage
    ```json
    {
        "task_description": "Monitor parking lot for unauthorized vehicles using camera feeds",
        "required_capabilities": ["vehicle_detection", "video_analysis", "real_time_monitoring"],
        "task_type": "surveillance_monitoring",
        "max_agents": 3,
        "min_score": 0.4
    }
    ```
    """,
    responses={
        200: {
            "description": "Successfully found matching agents",
            "content": {
                "application/json": {
                    "example": {
                        "request_id": "semantic_match_1703097600",
                        "task_description": "Monitor parking lot for unauthorized vehicles",
                        "matched_agents": [
                            {
                                "agent_id": "agent-123",
                                "agent_name": "Surveillance Agent Alpha",
                                "combined_score": 0.85,
                                "matched_capabilities": ["vehicle_detection", "video_analysis"],
                                "reasoning": "High capability match with excellent performance history"
                            }
                        ],
                        "total_available_agents": 12,
                        "semantic_matching_available": True,
                        "recommendations": ["All requirements matched successfully"]
                    }
                }
            }
        },
        400: {"description": "Invalid request parameters"},
        422: {"description": "Validation error in request data"}
    }
)
async def find_agents_semantic(
    request: SemanticTaskRequest,
    request_obj: Request,
    result: SemanticMatchingResponse = Depends(find_agents_semantic_enhanced)
) -> SemanticMatchingResponse:
    """Find agents using semantic matching with detailed analytics."""
    logger.info(f"Semantic agent matching request from {request_obj.client.host if request_obj.client else 'unknown'}")
    return result


@semantic_router.post(
    "/capabilities/analyze",
    response_model=CapabilityAnalysisResponse,
    summary="Analyze Capabilities Using Ontology",
    description="""
    **Analyze capability relationships and semantic structure.**
    
    This endpoint provides detailed analysis of capabilities using the built-in
    capability ontology. It expands capabilities through hierarchical relationships
    and provides semantic insights.
    
    ## Features
    - **Ontology Expansion**: Automatically includes related capabilities
    - **Semantic Relationships**: Shows similarity scores between capabilities
    - **Hierarchy Visualization**: Parent-child capability relationships
    - **Alias Recognition**: Handles capability aliases and synonyms
    - **Embedding Analysis**: Vector space analysis when available
    
    ## Use Cases
    - **Capability Planning**: Understand capability requirements
    - **Agent Training**: Identify capability gaps
    - **Ontology Exploration**: Browse capability relationships
    - **Semantic Analysis**: Understand capability similarities
    
    ## Example Usage
    ```json
    {
        "capabilities": ["person_detection", "video_analysis", "alerting"]
    }
    ```
    """,
    responses={
        200: {
            "description": "Successfully analyzed capabilities",
            "content": {
                "application/json": {
                    "example": {
                        "analyzed_capabilities": ["person_detection", "video_analysis"],
                        "expanded_capabilities": ["detection", "person_detection", "analysis", "video_analysis", "surveillance"],
                        "semantic_embeddings_available": True,
                        "suggestions": ["Capability ontology expanded 2 capabilities to 5"]
                    }
                }
            }
        }
    }
)
async def analyze_capabilities(
    request: CapabilityAnalysisRequest,
    result: CapabilityAnalysisResponse = Depends(analyze_capabilities_enhanced)
) -> CapabilityAnalysisResponse:
    """Analyze capabilities using the ontology system."""
    return result


@semantic_router.post(
    "/agents/{agent_id}/performance",
    summary="Update Agent Performance for Learning",
    description="""
    **Update agent performance metrics for dynamic learning.**
    
    This endpoint updates agent performance data that feeds into the semantic
    matching system's learning algorithms. It affects future agent rankings
    and matching decisions.
    
    ## Learning Algorithm
    - **Exponential Moving Average**: Recent performance weighted more heavily
    - **Task-Specific Learning**: Performance tracked per task type
    - **Capability Specialization**: Tracks performance per capability
    - **Response Time Optimization**: Considers speed vs accuracy tradeoffs
    
    ## Performance Factors
    - **Success Rate**: Whether tasks complete successfully
    - **Response Time**: How quickly agent responds
    - **Task Count**: Agent experience level
    - **Task Type Performance**: Specialization in specific task types
    
    ## Example Usage
    ```json
    {
        "task_type": "person_detection",
        "success": true,
        "response_time": 2.5,
        "additional_metrics": {
            "accuracy": 0.94,
            "confidence": 0.88
        }
    }
    ```
    """,
    responses={
        200: {
            "description": "Performance updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "agent_id": "agent-123",
                        "performance_updated": True,
                        "semantic_matcher_updated": True,
                        "updated_metrics": {
                            "success_rate": 0.87,
                            "avg_response_time": 2.3,
                            "task_count": 45
                        }
                    }
                }
            }
        },
        404: {"description": "Agent not found"}
    }
)
async def update_agent_performance(
    agent_id: str,
    performance_update: AgentPerformanceUpdate,
    result: Dict[str, Any] = Depends(update_agent_performance_enhanced)
) -> Dict[str, Any]:
    """Update agent performance for dynamic learning."""
    return result


@semantic_router.get(
    "/status",
    summary="Get Semantic Matching System Status",
    description="""
    **Get comprehensive status of the semantic matching system.**
    
    This endpoint provides detailed information about the current state of
    semantic matching capabilities, including model status, agent profiles,
    and system health.
    
    ## Status Information
    - **Dependencies**: Whether required libraries are installed
    - **Model Status**: Embedding model loading and configuration
    - **Agent Profiles**: Number of registered agent profiles
    - **Ontology**: Capability ontology statistics
    - **Performance**: Cache sizes and sync status
    
    ## Use Cases
    - **System Monitoring**: Check semantic matching health
    - **Troubleshooting**: Diagnose matching issues
    - **Configuration**: Verify system setup
    - **Analytics**: View system usage statistics
    """,
    responses={
        200: {
            "description": "System status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "semantic_matching_available": True,
                        "embedding_model_loaded": True,
                        "agent_profiles_count": 15,
                        "capability_ontology_nodes": 32,
                        "model_name": "all-MiniLM-L6-v2",
                        "dependencies_installed": True
                    }
                }
            }
        }
    }
)
async def get_status(
    result: Dict[str, Any] = Depends(get_semantic_matching_status)
) -> Dict[str, Any]:
    """Get semantic matching system status."""
    return result


@semantic_router.get(
    "/ontology",
    summary="Get Capability Ontology Structure",
    description="""
    **Retrieve the complete capability ontology structure.**
    
    This endpoint returns the full capability ontology including all nodes,
    relationships, and metadata. Useful for understanding the capability
    hierarchy and building user interfaces.
    """,
    responses={
        200: {"description": "Ontology structure retrieved successfully"}
    }
)
async def get_ontology_structure(
    auth_info: APIKeyInfo = Depends(require_permission("agent:read"))
) -> Dict[str, Any]:
    """Get the complete capability ontology structure."""
    try:
        from semantic_agent_matcher import get_semantic_matcher
        matcher = await get_semantic_matcher()
        
        ontology_data = {}
        for name, node in matcher.ontology.nodes.items():
            ontology_data[name] = {
                "name": node.name,
                "parent": node.parent,
                "children": list(node.children),
                "aliases": list(node.aliases),
                "description": node.description,
                "weight": node.weight
            }
        
        return {
            "ontology": ontology_data,
            "total_nodes": len(ontology_data),
            "root_nodes": [
                name for name, node in matcher.ontology.nodes.items() 
                if node.parent is None
            ],
            "embeddings_available": len(matcher.capability_embeddings) > 0
        }
        
    except ImportError:
        return {
            "ontology": {},
            "total_nodes": 0,
            "root_nodes": [],
            "embeddings_available": False,
            "error": "Semantic matching not available"
        }
    except Exception as e:
        logger.error(f"Error retrieving ontology: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ontology: {str(e)}"
        )


@semantic_router.post(
    "/agents/sync",
    summary="Sync Agent Profiles with Database",
    description="""
    **Manually sync semantic matcher with database state.**
    
    This endpoint forces a synchronization between the semantic matcher's
    agent profiles and the current database state. Useful after bulk agent
    updates or system restarts.
    """,
    responses={
        200: {"description": "Sync completed successfully"}
    }
)
async def sync_agent_profiles(
    auth_info: APIKeyInfo = Depends(require_permission("agent:write"))
) -> Dict[str, Any]:
    """Manually sync agent profiles with database."""
    try:
        from semantic_agent_matcher import get_semantic_matcher
        from database import get_db_session
        
        matcher = await get_semantic_matcher()
        
        async with get_db_session() as db:
            await matcher.sync_with_database(db)
        
        return {
            "sync_completed": True,
            "agent_profiles_count": len(matcher.agent_profiles),
            "timestamp": "datetime.utcnow().isoformat()"
        }
        
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Semantic matching not available"
        )
    except Exception as e:
        logger.error(f"Error syncing agent profiles: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


# Add router to main application
def setup_semantic_routes(app):
    """Setup semantic matching routes in the main application."""
    app.include_router(semantic_router)
    logger.info("Semantic matching routes registered")


# For standalone testing
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI(
        title="Semantic Agent Matching API",
        description="Enhanced agent matching with semantic analysis",
        version="1.0.0"
    )
    
    setup_semantic_routes(app)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
