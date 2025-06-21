"""
Enhanced Semantic Agent Matching Endpoints

This module provides API endpoints that leverage semantic agent matching capabilities.
These endpoints demonstrate the integration of vector-based capability matching with
the existing agent orchestrator infrastructure.

Features:
- Semantic task-agent matching with detailed scoring
- Capability ontology integration
- Performance-based agent ranking
- Dynamic capability learning
- Real-time matching analytics
- Comprehensive matching explanations

Author: Agent Orchestrator Team
Version: 1.0.0
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import get_db_session
from db_service import AgentRepository, DatabaseOperationError
from auth import APIKeyInfo, require_permission
from validation import ValidationUtils

logger = logging.getLogger(__name__)


# Request/Response Models for Semantic Matching

class SemanticTaskRequest(BaseModel):
    """Request model for semantic task matching"""
    task_description: str = Field(
        ...,
        description="Natural language description of the task",
        min_length=10,
        max_length=1000,
        example="Analyze video feed from camera 3 for suspicious person activity in the parking lot"
    )
    required_capabilities: Optional[List[str]] = Field(
        default=None,
        description="List of required capabilities",
        example=["person_detection", "video_analysis", "real_time_monitoring"]
    )
    task_type: Optional[str] = Field(
        default="",
        description="Type or category of the task",
        example="surveillance_analysis"
    )
    priority: Optional[int] = Field(
        default=1,
        description="Task priority (1-5, higher is more urgent)",
        ge=1,
        le=5
    )
    max_agents: Optional[int] = Field(
        default=3,
        description="Maximum number of agents to return",
        ge=1,
        le=10
    )
    min_score: Optional[float] = Field(
        default=0.3,
        description="Minimum matching score threshold",
        ge=0.0,
        le=1.0
    )
    use_semantic: Optional[bool] = Field(
        default=True,
        description="Whether to use semantic matching (fallback to basic if false)"
    )


class AgentMatchingResult(BaseModel):
    """Agent matching result with detailed scoring"""
    agent_id: str
    agent_name: str
    agent_type: str
    agent_status: str
    
    # Scoring details
    combined_score: float = Field(description="Overall matching score (0-1)")
    capability_match_score: Optional[float] = Field(description="Capability matching score")
    semantic_similarity_score: Optional[float] = Field(description="Semantic similarity score")
    performance_score: Optional[float] = Field(description="Performance-based score")
    confidence: Optional[float] = Field(description="Confidence in the match")
    
    # Capability analysis
    matched_capabilities: List[str] = Field(description="Capabilities that match requirements")
    missing_capabilities: List[str] = Field(description="Required capabilities not available")
    extra_capabilities: List[str] = Field(description="Additional capabilities available")
    
    # Performance metrics
    success_rate: Optional[float] = Field(description="Historical success rate")
    avg_response_time: Optional[float] = Field(description="Average response time")
    task_count: Optional[int] = Field(description="Number of completed tasks")
    
    # Matching details
    matching_method: str = Field(description="Method used for matching (semantic/basic/fallback)")
    reasoning: Optional[str] = Field(description="Explanation of the matching decision")
    
    # Agent details
    agent_capabilities: List[str] = Field(description="All agent capabilities")
    last_seen: Optional[datetime] = Field(description="Last time agent was seen")


class SemanticMatchingResponse(BaseModel):
    """Response for semantic matching requests"""
    request_id: str
    task_description: str
    matching_timestamp: datetime
    
    # Results
    matched_agents: List[AgentMatchingResult]
    total_available_agents: int
    agents_evaluated: int
    
    # Matching analytics
    average_score: float
    best_score: float
    matching_method_used: str
    semantic_matching_available: bool
    
    # Performance metrics
    matching_duration_ms: float
    capability_expansion_count: int
    
    # Recommendations
    recommendations: List[str] = Field(description="Recommendations for improving matches")


class CapabilityAnalysisRequest(BaseModel):
    """Request for capability analysis"""
    capabilities: List[str] = Field(
        ...,
        description="List of capabilities to analyze",
        min_items=1,
        example=["person_detection", "video_analysis"]
    )


class CapabilityNode(BaseModel):
    """Capability node in the ontology"""
    name: str
    parent: Optional[str]
    children: List[str]
    aliases: List[str]
    description: str
    weight: float


class CapabilityAnalysisResponse(BaseModel):
    """Response for capability analysis"""
    analyzed_capabilities: List[str]
    expanded_capabilities: List[str]
    capability_tree: Dict[str, CapabilityNode]
    semantic_embeddings_available: bool
    capability_relationships: Dict[str, List[str]]
    suggestions: List[str]


class AgentPerformanceUpdate(BaseModel):
    """Request to update agent performance"""
    task_type: str = Field(..., description="Type of task completed")
    success: bool = Field(..., description="Whether the task was successful")
    response_time: float = Field(..., description="Task response time in seconds", gt=0)
    additional_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional performance metrics"
    )


# Enhanced Semantic Matching Endpoints

async def find_agents_semantic_enhanced(
    request: SemanticTaskRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("task:create"))
) -> SemanticMatchingResponse:
    """
    Find suitable agents using advanced semantic matching.
    
    This endpoint provides the most sophisticated agent matching available,
    using vector embeddings, capability ontology, and performance history.
    """
    start_time = datetime.utcnow()
    request_id = f"semantic_match_{int(start_time.timestamp())}"
    
    try:
        # Validate and sanitize input
        task_description = ValidationUtils.sanitize_string(request.task_description)
        required_capabilities = [
            ValidationUtils.sanitize_string(cap) 
            for cap in (request.required_capabilities or [])
        ]
        task_type = ValidationUtils.sanitize_string(request.task_type or "")
        
        # Get all available agents for analytics
        all_agents, _ = await AgentRepository.list_agents(
            db=db,
            status="idle",
            limit=1000,
            offset=0
        )
        total_available = len(all_agents)
        
        if total_available == 0:
            return SemanticMatchingResponse(
                request_id=request_id,
                task_description=task_description,
                matching_timestamp=start_time,
                matched_agents=[],
                total_available_agents=0,
                agents_evaluated=0,
                average_score=0.0,
                best_score=0.0,
                matching_method_used="none",
                semantic_matching_available=False,
                matching_duration_ms=0.0,
                capability_expansion_count=0,
                recommendations=["No agents available. Register agents first."]
            )
        
        # Use enhanced semantic matching
        matched_agents, matching_details = await AgentRepository.find_suitable_agents_semantic(
            task_description=task_description,
            required_capabilities=required_capabilities,
            task_type=task_type,
            db=db,
            top_k=request.max_agents,
            min_score=request.min_score,
            use_semantic=request.use_semantic
        )
        
        # Calculate analytics
        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        scores = [detail.get('score', 0.0) for detail in matching_details]
        average_score = sum(scores) / len(scores) if scores else 0.0
        best_score = max(scores) if scores else 0.0
        
        # Determine method used
        methods_used = set(detail.get('method', 'unknown') for detail in matching_details)
        primary_method = 'semantic' if 'semantic' in methods_used else (
            'basic' if 'basic' in methods_used else 
            'fallback' if 'fallback' in methods_used else 'unknown'
        )
        
        # Convert to response format
        result_agents = []
        for i, (agent, detail) in enumerate(zip(matched_agents, matching_details)):
            # Get agent capabilities and extra capabilities
            agent_caps = agent.capabilities or []
            matched_caps = detail.get('matched_capabilities', [])
            missing_caps = detail.get('missing_capabilities', [])
            extra_caps = [cap for cap in agent_caps if cap not in (required_capabilities or [])]
            
            result_agent = AgentMatchingResult(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_type=agent.type.value if hasattr(agent.type, 'value') else str(agent.type),
                agent_status=agent.status,
                
                # Scoring
                combined_score=detail.get('score', 0.0),
                capability_match_score=detail.get('capability_match_score'),
                semantic_similarity_score=detail.get('semantic_similarity_score'),
                performance_score=detail.get('performance_score'),
                confidence=detail.get('confidence', 0.5),
                
                # Capabilities
                matched_capabilities=matched_caps,
                missing_capabilities=missing_caps,
                extra_capabilities=extra_caps,
                agent_capabilities=agent_caps,
                
                # Performance
                success_rate=agent.performance_metrics.get('success_rate', 0.5) if agent.performance_metrics else 0.5,
                avg_response_time=agent.performance_metrics.get('avg_response_time', 1.0) if agent.performance_metrics else 1.0,
                task_count=agent.performance_metrics.get('task_count', 0) if agent.performance_metrics else 0,
                
                # Details
                matching_method=detail.get('method', 'unknown'),
                reasoning=detail.get('reasoning', f"Ranked #{i+1} by {detail.get('method', 'unknown')} matching"),
                last_seen=agent.last_seen
            )
            result_agents.append(result_agent)
        
        # Generate recommendations
        recommendations = []
        if not matched_agents:
            recommendations.append("No suitable agents found. Consider lowering min_score or training more agents.")
        elif len(matched_agents) < request.max_agents:
            recommendations.append(f"Only {len(matched_agents)} of {request.max_agents} requested agents found.")
        
        if average_score < 0.5:
            recommendations.append("Low average matching scores. Consider improving agent capabilities or task description.")
        
        if primary_method == 'fallback':
            recommendations.append("Using fallback matching. Check semantic matching service availability.")
        
        if missing_caps := [cap for detail in matching_details for cap in detail.get('missing_capabilities', [])]:
            unique_missing = list(set(missing_caps))
            recommendations.append(f"Consider training agents with these missing capabilities: {', '.join(unique_missing)}")
        
        # Try to get capability expansion count
        capability_expansion_count = 0
        try:
            from semantic_agent_matcher import get_semantic_matcher
            matcher = await get_semantic_matcher()
            expanded = matcher.ontology.get_expanded_capabilities(required_capabilities)
            capability_expansion_count = len(expanded) - len(required_capabilities)
        except:
            pass
        
        return SemanticMatchingResponse(
            request_id=request_id,
            task_description=task_description,
            matching_timestamp=start_time,
            matched_agents=result_agents,
            total_available_agents=total_available,
            agents_evaluated=len(all_agents),
            average_score=average_score,
            best_score=best_score,
            matching_method_used=primary_method,
            semantic_matching_available=primary_method in ['semantic'],
            matching_duration_ms=duration_ms,
            capability_expansion_count=capability_expansion_count,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Error in semantic agent matching: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Semantic matching failed: {str(e)}"
        )


async def analyze_capabilities_enhanced(
    request: CapabilityAnalysisRequest,
    auth_info: APIKeyInfo = Depends(require_permission("agent:read"))
) -> CapabilityAnalysisResponse:
    """
    Analyze capabilities using the capability ontology.
    
    This endpoint provides detailed analysis of capability relationships,
    expansion through the ontology, and semantic embeddings information.
    """
    try:
        # Validate and sanitize capabilities
        capabilities = [
            ValidationUtils.sanitize_string(cap) 
            for cap in request.capabilities
        ]
        
        # Get capability analysis
        try:
            from semantic_agent_matcher import get_semantic_matcher
            matcher = await get_semantic_matcher()
            
            # Get expanded capabilities
            expanded = matcher.ontology.get_expanded_capabilities(capabilities)
            expanded_list = list(expanded)
            
            # Build capability tree
            capability_tree = {}
            for cap_name in expanded_list:
                if cap_name in matcher.ontology.nodes:
                    node = matcher.ontology.nodes[cap_name]
                    capability_tree[cap_name] = CapabilityNode(
                        name=node.name,
                        parent=node.parent,
                        children=list(node.children),
                        aliases=list(node.aliases),
                        description=node.description,
                        weight=node.weight
                    )
            
            # Find relationships
            relationships = {}
            for cap in capabilities:
                related = []
                for other_cap in expanded_list:
                    if cap != other_cap:
                        similarity = matcher.ontology.calculate_capability_similarity(cap, other_cap)
                        if similarity > 0.5:
                            related.append(f"{other_cap} (similarity: {similarity:.2f})")
                relationships[cap] = related
            
            semantic_available = matcher.embedding_model is not None
            
            # Generate suggestions
            suggestions = []
            if len(expanded_list) > len(capabilities):
                suggestions.append(f"Capability ontology expanded {len(capabilities)} capabilities to {len(expanded_list)}")
            
            if semantic_available:
                suggestions.append("Semantic embeddings are available for advanced matching")
            else:
                suggestions.append("Semantic embeddings not available - install sentence-transformers for better matching")
            
            unknown_caps = [cap for cap in capabilities if cap not in matcher.ontology.nodes]
            if unknown_caps:
                suggestions.append(f"Unknown capabilities detected: {', '.join(unknown_caps)}. Consider adding to ontology.")
            
        except ImportError:
            # Fallback when semantic matcher not available
            expanded_list = capabilities  # No expansion available
            capability_tree = {}
            relationships = {cap: [] for cap in capabilities}
            semantic_available = False
            suggestions = [
                "Semantic matching not available",
                "Install sentence-transformers and scikit-learn for advanced capability analysis"
            ]
        
        return CapabilityAnalysisResponse(
            analyzed_capabilities=capabilities,
            expanded_capabilities=expanded_list,
            capability_tree=capability_tree,
            semantic_embeddings_available=semantic_available,
            capability_relationships=relationships,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Error in capability analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Capability analysis failed: {str(e)}"
        )


async def update_agent_performance_enhanced(
    agent_id: str,
    performance_update: AgentPerformanceUpdate,
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("agent:write"))
) -> Dict[str, Any]:
    """
    Update agent performance metrics for semantic matching.
    
    This endpoint updates both the database performance metrics and the
    semantic matcher's dynamic learning system.
    """
    try:
        # Validate agent ID
        if not ValidationUtils.validate_uuid(agent_id):
            raise HTTPException(status_code=400, detail="Invalid agent ID format")
        
        # Verify agent exists
        agent = await AgentRepository.get_agent_by_id(agent_id, db)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Update semantic matcher performance
        try:
            from semantic_agent_matcher import update_agent_performance_semantic
            await update_agent_performance_semantic(
                agent_id=agent_id,
                task_type=performance_update.task_type,
                success=performance_update.success,
                response_time=performance_update.response_time
            )
            semantic_updated = True
        except ImportError:
            logger.warning("Semantic matcher not available for performance update")
            semantic_updated = False
        except Exception as e:
            logger.warning(f"Failed to update semantic matcher: {e}")
            semantic_updated = False
        
        # Update database performance metrics
        current_metrics = agent.performance_metrics or {}
        
        # Update success rate (exponential moving average)
        alpha = 0.1
        current_success_rate = current_metrics.get("success_rate", 0.5)
        if performance_update.success:
            new_success_rate = current_success_rate * (1 - alpha) + alpha
        else:
            new_success_rate = current_success_rate * (1 - alpha)
        
        # Update response time
        current_response_time = current_metrics.get("avg_response_time", 1.0)
        new_response_time = current_response_time * (1 - alpha) + performance_update.response_time * alpha
        
        # Update task count
        task_count = current_metrics.get("task_count", 0) + 1
        
        # Update task-specific performance
        task_performance = current_metrics.get("task_performance", {})
        task_type = performance_update.task_type
        
        if task_type not in task_performance:
            task_performance[task_type] = {"success_rate": 0.5, "count": 0}
        
        task_perf = task_performance[task_type]
        task_perf["count"] += 1
        
        if performance_update.success:
            task_perf["success_rate"] = task_perf["success_rate"] * (1 - alpha) + alpha
        else:
            task_perf["success_rate"] = task_perf["success_rate"] * (1 - alpha)
        
        # Merge additional metrics
        if performance_update.additional_metrics:
            current_metrics.update(performance_update.additional_metrics)
        
        # Build updated metrics
        updated_metrics = {
            **current_metrics,
            "success_rate": new_success_rate,
            "avg_response_time": new_response_time,
            "task_count": task_count,
            "task_performance": task_performance,
            "last_performance_update": datetime.utcnow().isoformat()
        }
        
        # Update agent in database
        from sqlalchemy import update
        update_query = (
            update(Agent)
            .where(Agent.id == agent_id)
            .values(
                performance_metrics=updated_metrics,
                updated_at=datetime.utcnow()
            )
        )
        
        await db.execute(update_query)
        await db.commit()
        
        logger.info(f"Updated performance for agent {agent_id}: success_rate={new_success_rate:.3f}")
        
        return {
            "agent_id": agent_id,
            "performance_updated": True,
            "semantic_matcher_updated": semantic_updated,
            "updated_metrics": {
                "success_rate": new_success_rate,
                "avg_response_time": new_response_time,
                "task_count": task_count,
                "task_type_performance": task_perf
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent performance: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Performance update failed: {str(e)}"
        )


async def get_semantic_matching_status(
    auth_info: APIKeyInfo = Depends(require_permission("agent:read"))
) -> Dict[str, Any]:
    """
    Get the status of semantic matching capabilities.
    
    This endpoint provides information about the current state of semantic
    matching, including model availability, agent profiles, and performance.
    """
    try:
        status = {
            "semantic_matching_available": False,
            "embedding_model_loaded": False,
            "agent_profiles_count": 0,
            "capability_ontology_nodes": 0,
            "precomputed_embeddings": 0,
            "cache_size": 0,
            "last_sync_time": None,
            "model_name": None,
            "dependencies_installed": False
        }
        
        # Check if dependencies are available
        try:
            import sentence_transformers
            import sklearn
            status["dependencies_installed"] = True
        except ImportError:
            status["dependencies_installed"] = False
            return status
        
        # Get semantic matcher status
        try:
            from semantic_agent_matcher import get_semantic_matcher
            matcher = await get_semantic_matcher()
            
            status.update({
                "semantic_matching_available": True,
                "embedding_model_loaded": matcher.embedding_model is not None,
                "agent_profiles_count": len(matcher.agent_profiles),
                "capability_ontology_nodes": len(matcher.ontology.nodes),
                "precomputed_embeddings": len(matcher.capability_embeddings),
                "cache_size": len(matcher.task_embeddings_cache),
                "model_name": matcher.model_name
            })
            
            # Get last sync time from profiles
            if matcher.agent_profiles:
                last_updates = [
                    profile.last_updated 
                    for profile in matcher.agent_profiles.values()
                ]
                status["last_sync_time"] = max(last_updates).isoformat()
            
            # Additional statistics
            if matcher.agent_profiles:
                avg_capabilities = sum(
                    len(profile.capabilities) 
                    for profile in matcher.agent_profiles.values()
                ) / len(matcher.agent_profiles)
                
                avg_task_count = sum(
                    profile.task_count 
                    for profile in matcher.agent_profiles.values()
                ) / len(matcher.agent_profiles)
                
                status.update({
                    "average_capabilities_per_agent": avg_capabilities,
                    "average_task_count_per_agent": avg_task_count
                })
            
        except Exception as e:
            logger.warning(f"Error getting semantic matcher status: {e}")
            status["error"] = str(e)
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting semantic matching status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )


# Endpoint registration examples (to be used in main.py or router)
"""
Example usage in FastAPI app:

from semantic_endpoints import (
    find_agents_semantic_enhanced,
    analyze_capabilities_enhanced,
    update_agent_performance_enhanced,
    get_semantic_matching_status
)

app.post("/api/v2/agents/match/semantic", response_model=SemanticMatchingResponse)(
    find_agents_semantic_enhanced
)

app.post("/api/v2/capabilities/analyze", response_model=CapabilityAnalysisResponse)(
    analyze_capabilities_enhanced
)

app.post("/api/v2/agents/{agent_id}/performance", response_model=Dict[str, Any])(
    update_agent_performance_enhanced
)

app.get("/api/v2/semantic/status", response_model=Dict[str, Any])(
    get_semantic_matching_status
)
"""
