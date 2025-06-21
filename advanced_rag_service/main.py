"""
Advanced RAG Service Enhancements

This service extends the basic RAG service with:
- Multi-modal evidence processing (video, images, metadata)
- Advanced evidence correlation and linking
- Confidence scoring and uncertainty quantification
- Temporal context analysis
- Cross-reference validation
- Evidence chain reconstruction
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import base64
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
import redis.asyncio as redis
import httpx
import numpy as np
from PIL import Image
import cv2
import weaviate
from openai import AsyncOpenAI

# Import shared middleware for rate limiting
from shared.middleware import add_rate_limiting

# Import comprehensive metrics system
from metrics import (
    metrics_collector, monitor_query_performance, monitor_external_service,
    ServiceType, MetricType
)

# Import advanced RAG module  
import advanced_rag
from advanced_rag import QueryEvent

# Import structured configuration
from config import get_config, AdvancedRAGConfig

# Import API versioning system
from api_versioning import (
    create_versioned_app, get_current_api_version, version_manager,
    APIVersion, get_api_versions_info, v1_endpoint, v2_endpoint, legacy_endpoint
)

# Import enhanced error handling
from error_handling import (
    EnhancedRAGError, WeaviateConnectionError, OpenAIAPIError, 
    EmbeddingGenerationError, TemporalProcessingError, ServiceDegradationError,
    FallbackTemporalRAGResponse, with_retry, handle_exceptions,
    RetryConfig, ErrorType
)
from service_status import service_status_manager, ServiceStatus

# Import comprehensive metrics system
from metrics import (
    metrics_collector, monitor_query_performance, monitor_external_service,
    ServiceType, MetricType
)

# API Versioning Information Endpoints
@legacy_endpoint
# FIXED: @app.get("/api/versions", 
# FIXED:          tags=["API Information"],
# FIXED:          summary="Get API Version Information",
# FIXED:          description="Get information about all supported API versions")
# FIXED: async def get_api_versions():
async def get_api_versions_placeholder():
    """Placeholder - moved to after app creation"""
    pass
    """Get comprehensive API version information"""
    return get_api_versions_info()

@legacy_endpoint
# FIXED: @app.get("/api/version", 
# FIXED:          tags=["API Information"],
# FIXED:          summary="Get Current API Version",
# FIXED:          description="Get current API version being used for this request")
# FIXED: async def get_current_version(api_version: APIVersion = Depends(get_current_api_version)):
async def get_current_version_placeholder():
    """Placeholder - moved to after app creation"""
    pass
    """Get current API version for this request"""
    info = version_manager.get_version_info(api_version)
    return {
        "version": api_version.value,
        "status": info.status if info else "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "deprecation_warnings": version_manager.get_deprecation_warnings(api_version)
    }

@v1_endpoint
# FIXED: @app.get("/api/v1/version",
# FIXED:          tags=["v1.0", "v1.1", "API Information"],
# FIXED:          summary="Get V1 API Version Info",
# FIXED:          description="Get version information for V1 API endpoints")
# FIXED: async def get_v1_version_info():
async def get_v1_version_info_placeholder():
    """Placeholder - moved to after app creation"""
    pass
    """Get V1 API version information"""
    v1_info = version_manager.get_version_info(APIVersion.V1_0)
    v1_1_info = version_manager.get_version_info(APIVersion.V1_1)
    
    return {
        "v1.0": {
            "status": v1_info.status if v1_info else "unknown",
            "release_date": v1_info.release_date.isoformat() if v1_info else None,
            "deprecation_date": v1_info.deprecation_date.isoformat() if v1_info and v1_info.deprecation_date else None,
            "sunset_date": v1_info.sunset_date.isoformat() if v1_info and v1_info.sunset_date else None,
            "days_until_sunset": v1_info.days_until_sunset if v1_info else None
        },
        "v1.1": {
            "status": v1_1_info.status if v1_1_info else "unknown", 
            "release_date": v1_1_info.release_date.isoformat() if v1_1_info else None,
            "changelog": v1_1_info.changelog if v1_1_info else []
        },
        "recommended": APIVersion.get_latest().value
    }

@v2_endpoint
# FIXED: @app.get("/api/v2/preview",
# FIXED:          tags=["v2.0", "API Information"],
# FIXED:          summary="V2 API Preview",
# FIXED:          description="Preview of upcoming V2 API features")
# FIXED: async def get_v2_preview():
async def get_v2_preview_placeholder():
    """Placeholder - moved to after app creation"""
    pass
    """Get preview of V2 API features"""
    v2_info = version_manager.get_version_info(APIVersion.V2_0)
    
    return {
        "version": "2.0",
        "status": "planned",
        "planned_release": v2_info.release_date.isoformat() if v2_info else None,
        "new_features": v2_info.changelog if v2_info else [],
        "breaking_changes": v2_info.breaking_changes if v2_info else [],
        "migration_guide": "/docs/v2-migration"  # Future documentation
    }
    

# Application startup and shutdown handlers
# FIXED: @app.on_event("startup")
# FIXED: async def startup_event():
async def startup_event_placeholder():
    """Placeholder - moved to after app creation"""
    pass
    """Enhanced startup with service initialization and health monitoring"""
    logger.info("Starting Advanced RAG Service with enhanced error handling...")
    
    try:
        # Initialize clients
        await initialize_clients_with_health_checks()
        
        # Define health check functions
        health_checks = {
            "weaviate": check_weaviate_health,
            "openai": check_openai_health,
            "redis": check_redis_health,
        }
        
        # Start health monitoring
        await service_status_manager.start_health_monitoring(health_checks)
        
        # Initial health checks
        for service_name, health_check_func in health_checks.items():
            await service_status_manager.check_service_health(service_name, health_check_func)
        
        logger.info("Advanced RAG Service startup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Don't fail startup completely - allow service to run in degraded mode
        logger.warning("Service starting in degraded mode due to initialization errors")

# FIXED: @app.on_event("shutdown")
# FIXED: async def shutdown_event():
async def shutdown_event_placeholder():
    """Placeholder - moved to after app creation"""
    pass
    """Graceful shutdown with cleanup"""
    logger.info("Shutting down Advanced RAG Service...")
    
    try:
        # Clean up connections
        if weaviate_client:
            try:
                weaviate_client.close()
                logger.info("Weaviate client closed")
            except Exception as e:
                logger.error(f"Error closing Weaviate client: {e}")
        
        if redis_client:
            try:
                await redis_client.close()
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
        
        logger.info("Advanced RAG Service shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/7")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set - AI analysis will be limited")

# Enhanced client initialization with detailed error handling
async def initialize_clients_with_health_checks():
    """Initialize clients with comprehensive error handling and health checks"""
    global openai_client, weaviate_client
    
    # Initialize OpenAI client
    try:
        if OPENAI_API_KEY:
            openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI client initialized successfully")
        else:
            openai_client = None
            logger.warning("OpenAI client not initialized - no API key provided")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        openai_client = None
    
    # Initialize Weaviate client
    try:
        weaviate_client = weaviate.Client(
            url=WEAVIATE_URL,
            auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None
        )
        logger.info("Weaviate client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Weaviate client: {e}")
        weaviate_client = None

# Service health check functions
async def check_openai_health():
    """Check OpenAI service health"""
    if not openai_client:
        return False
    try:
        # Simple health check - list models (lightweight operation)
        models = await openai_client.models.list()
        return len(models.data) > 0
    except Exception as e:
        logger.debug(f"OpenAI health check failed: {e}")
        return False

async def check_weaviate_health():
    """Check Weaviate service health"""
    if not weaviate_client:
        return False
    try:
        # Simple health check - get cluster info
        health = weaviate_client.cluster.get_nodes_status()
        return len(health) > 0
    except Exception as e:
        logger.debug(f"Weaviate health check failed: {e}")
        return False

async def check_redis_health():
    """Check Redis service health"""
    try:
        # Check Redis connection
        test_client = redis.from_url(REDIS_URL)
        await test_client.ping()
        await test_client.close()
        return True
    except Exception as e:
        logger.debug(f"Redis health check failed: {e}")
        return False

# Initialize clients (will be called during startup)
openai_client = None
weaviate_client = None


# Enums
class EvidenceType(str, Enum):
    VIDEO_CLIP = "video_clip"
    IMAGE = "image"
    AUDIO = "audio"
    METADATA = "metadata"
    SENSOR_DATA = "sensor_data"
    TEXT_LOG = "text_log"


class ConfidenceLevel(str, Enum):
    HIGH = "high"  # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"  # 0.3 - 0.5
    VERY_LOW = "very_low"  # < 0.3


class CorrelationType(str, Enum):
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    CAUSAL = "causal"
    CONTEXTUAL = "contextual"
    SEMANTIC = "semantic"


# Data Models
@dataclass
class Evidence:
    id: str
    type: EvidenceType
    source: str
    timestamp: datetime
    location: Optional[str]
    content: Any
    metadata: Dict[str, Any]
    confidence_score: float
    embedding: Optional[List[float]] = None
    analysis_results: Optional[Dict] = None


@dataclass
class EvidenceCorrelation:
    evidence1_id: str
    evidence2_id: str
    correlation_type: CorrelationType
    strength: float
    description: str
    supporting_factors: List[str]


@dataclass
class EvidenceChain:
    id: str
    name: str
    description: str
    evidence_ids: List[str]
    correlations: List[EvidenceCorrelation]
    confidence_score: float
    temporal_span: Tuple[datetime, datetime]
    conclusion: str


@dataclass
class MultiModalQuery:
    text_query: str
    image_query: Optional[bytes] = None
    video_query: Optional[bytes] = None
    temporal_filters: Optional[Dict] = None
    spatial_filters: Optional[Dict] = None
    confidence_threshold: float = 0.5


# Request/Response Models
class AdvancedQueryRequest(BaseModel):
    query: str
    evidence_types: List[EvidenceType] = []
    temporal_range: Optional[dict] = None
    spatial_filters: Optional[dict] = None
    confidence_threshold: float = 0.5
    include_correlations: bool = True
    max_results: int = 50


class EvidenceAnalysisRequest(BaseModel):
    evidence_ids: List[str]
    analysis_type: str = "comprehensive"
    include_cross_references: bool = True


class CorrelationAnalysisRequest(BaseModel):
    evidence_ids: List[str]
    correlation_types: List[CorrelationType] = []
    min_strength: float = 0.3


class MultiModalAnalysisRequest(BaseModel):
    """Request model for multi-modal RAG analysis"""

    query: str
    include_video: bool = False
    include_images: bool = False
    time_range: Optional[str] = None


class TemporalRAGQueryRequest(BaseModel):
    """Request model for temporal RAG queries"""
    query_event: Dict[str, Any] = Field(..., description="Query event with camera_id, timestamp, label, and optional bbox")
    k: int = Field(default=10, ge=1, le=100, description="Number of similar events to retrieve")


class TemporalRAGQueryResponse(BaseModel):
    """Response model for temporal RAG queries"""
    linked_explanation: str = Field(..., description="LLM explanation emphasizing temporal flow and causality")
    retrieved_context: List[Dict[str, Any]] = Field(..., description="Retrieved events in chronological order")
    explanation_confidence: float = Field(..., description="Confidence score (0-1) based on vector similarity of retrieved context")


# Global state
redis_client: Optional[redis.Redis] = None


async def get_redis_client():
    """Get Redis client"""
    global redis_client
    if not redis_client:
        redis_client = redis.from_url("redis://localhost:6379/7")
    return redis_client


# Multi-Modal Analysis Engine
class MultiModalAnalyzer:
    def __init__(self):
        self.supported_formats = {
            "video": [".mp4", ".avi", ".mov", ".mkv"],
            "image": [".jpg", ".jpeg", ".png", ".bmp"],
            "audio": [".wav", ".mp3", ".aac"],
        }

    async def analyze_video_content(self, video_data: bytes) -> Dict:
        """Analyze video content for objects, activities, and scenes"""
        try:
            # Save video temporarily
            temp_path = f"/tmp/video_{uuid.uuid4().hex}.mp4"
            with open(temp_path, "wb") as f:
                f.write(video_data)

            # Extract frames for analysis
            cap = cv2.VideoCapture(temp_path)
            frames = []
            frame_count = 0

            while cap.isOpened() and frame_count < 10:  # Analyze up to 10 frames
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
                frame_count += 1

            cap.release()

            # Analyze each frame
            analysis_results = {
                "objects_detected": [],
                "activities": [],
                "scene_description": "",
                "technical_metadata": {},
                "temporal_analysis": [],
            }

            for i, frame in enumerate(frames):
                frame_analysis = await self._analyze_frame(frame, i)
                analysis_results["objects_detected"].extend(
                    frame_analysis.get("objects", [])
                )
                analysis_results["activities"].extend(
                    frame_analysis.get("activities", [])
                )
                analysis_results["temporal_analysis"].append(frame_analysis)

            # Generate overall scene description
            analysis_results["scene_description"] = (
                await self._generate_scene_description(analysis_results)
            )

            # Clean up
            Path(temp_path).unlink(missing_ok=True)

            return analysis_results

        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            return {"error": str(e)}

    async def _analyze_frame(self, frame: np.ndarray, frame_index: int) -> Dict:
        """Analyze individual video frame"""
        # Convert frame to base64 for OpenAI Vision API
        _, buffer = cv2.imencode(".jpg", frame)
        frame_base64 = base64.b64encode(buffer).decode("utf-8")

        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this surveillance frame. Identify objects, people, activities, and any notable events. Provide specific details about locations, movements, and interactions.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{frame_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=500,
            )

            analysis_text = response.choices[0].message.content

            # Parse analysis into structured format
            return {
                "frame_index": frame_index,
                "raw_analysis": analysis_text,
                "objects": self._extract_objects_from_analysis(analysis_text),
                "activities": self._extract_activities_from_analysis(analysis_text),
                "timestamp": frame_index * 0.5,  # Assuming 2 FPS sampling
            }

        except Exception as e:
            logger.error(f"Error analyzing frame {frame_index}: {e}")
            return {"frame_index": frame_index, "error": str(e)}

    def _extract_objects_from_analysis(self, analysis_text: str) -> List[Dict]:
        """Extract object information from analysis text"""
        # Simple keyword-based extraction (in practice, use NLP)
        objects = []
        object_keywords = [
            "person",
            "car",
            "vehicle",
            "bag",
            "weapon",
            "door",
            "window",
        ]

        for keyword in object_keywords:
            if keyword in analysis_text.lower():
                objects.append(
                    {
                        "type": keyword,
                        "confidence": 0.8,  # Placeholder
                        "location": "detected",
                    }
                )

        return objects

    def _extract_activities_from_analysis(self, analysis_text: str) -> List[Dict]:
        """Extract activity information from analysis text"""
        activities = []
        activity_keywords = [
            "walking",
            "running",
            "standing",
            "sitting",
            "entering",
            "leaving",
        ]

        for keyword in activity_keywords:
            if keyword in analysis_text.lower():
                activities.append(
                    {
                        "type": keyword,
                        "confidence": 0.7,
                        "description": f"Person {keyword}",
                    }
                )

        return activities

    async def _generate_scene_description(self, analysis_results: Dict) -> str:
        """Generate overall scene description from frame analyses"""
        objects = analysis_results.get("objects_detected", [])
        activities = analysis_results.get("activities", [])

        description_prompt = f"""
        Based on the following detected objects and activities, generate a comprehensive scene description:
        
        Objects: {objects}
        Activities: {activities}
        
        Provide a concise but detailed description of what's happening in this surveillance footage.
        """

        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": description_prompt}],
                max_tokens=200,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating scene description: {e}")
            return "Scene analysis unavailable"

    async def analyze_image_content(self, image_data: bytes) -> Dict:
        """Analyze image content"""
        try:
            # Convert to base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            response = await openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this surveillance image. Describe everything you see including people, objects, activities, and environmental details. Be specific about locations and any notable events.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            analysis = response.choices[0].message.content

            return {
                "description": analysis,
                "objects": self._extract_objects_from_analysis(analysis),
                "activities": self._extract_activities_from_analysis(analysis),
                "scene_type": "surveillance_image",
            }

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {"error": str(e)}


# Evidence Correlation Engine
class EvidenceCorrelationEngine:
    def __init__(self):
        self.correlation_algorithms = {
            CorrelationType.TEMPORAL: self._analyze_temporal_correlation,
            CorrelationType.SPATIAL: self._analyze_spatial_correlation,
            CorrelationType.CAUSAL: self._analyze_causal_correlation,
            CorrelationType.CONTEXTUAL: self._analyze_contextual_correlation,
            CorrelationType.SEMANTIC: self._analyze_semantic_correlation,
        }

    async def find_correlations(
        self,
        evidence_list: List[Evidence],
        correlation_types: List[CorrelationType] = None,
    ) -> List[EvidenceCorrelation]:
        """Find correlations between pieces of evidence"""
        if not correlation_types:
            correlation_types = list(CorrelationType)

        correlations = []

        # Compare each pair of evidence
        for i, evidence1 in enumerate(evidence_list):
            for j, evidence2 in enumerate(evidence_list[i + 1 :], i + 1):
                for corr_type in correlation_types:
                    correlation = await self._analyze_correlation(
                        evidence1, evidence2, corr_type
                    )
                    if correlation and correlation.strength > 0.3:
                        correlations.append(correlation)

        return correlations

    async def _analyze_correlation(
        self,
        evidence1: Evidence,
        evidence2: Evidence,
        correlation_type: CorrelationType,
    ) -> Optional[EvidenceCorrelation]:
        """Analyze correlation between two pieces of evidence"""
        algorithm = self.correlation_algorithms.get(correlation_type)
        if not algorithm:
            return None

        return await algorithm(evidence1, evidence2)

    async def _analyze_temporal_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze temporal correlation"""
        time_diff = abs((evidence1.timestamp - evidence2.timestamp).total_seconds())

        # Strong temporal correlation if within 5 minutes
        if time_diff <= 300:
            strength = 1.0 - (time_diff / 300)
            return EvidenceCorrelation(
                evidence1_id=evidence1.id,
                evidence2_id=evidence2.id,
                correlation_type=CorrelationType.TEMPORAL,
                strength=strength,
                description=f"Events occurred {time_diff:.0f} seconds apart",
                supporting_factors=[f"Time difference: {time_diff:.0f}s"],
            )

        return None

    async def _analyze_spatial_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze spatial correlation"""
        if evidence1.location and evidence2.location:
            # Simple string matching for locations
            if evidence1.location == evidence2.location:
                return EvidenceCorrelation(
                    evidence1_id=evidence1.id,
                    evidence2_id=evidence2.id,
                    correlation_type=CorrelationType.SPATIAL,
                    strength=0.9,
                    description=f"Both events occurred at {evidence1.location}",
                    supporting_factors=[f"Same location: {evidence1.location}"],
                )
            elif (
                evidence1.location in evidence2.location
                or evidence2.location in evidence1.location
            ):
                return EvidenceCorrelation(
                    evidence1_id=evidence1.id,
                    evidence2_id=evidence2.id,
                    correlation_type=CorrelationType.SPATIAL,
                    strength=0.6,
                    description=f"Events in related locations",
                    supporting_factors=[
                        f"Related locations: {evidence1.location}, {evidence2.location}"
                    ],
                )

        return None

    async def _analyze_causal_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze causal correlation using LLM"""
        try:
            causal_prompt = f"""
            Analyze if there's a causal relationship between these two events:
            
            Event 1: {evidence1.metadata.get('description', 'No description')}
            Time: {evidence1.timestamp}
            Location: {evidence1.location}
            
            Event 2: {evidence2.metadata.get('description', 'No description')}
            Time: {evidence2.timestamp}
            Location: {evidence2.location}
            
            Could Event 1 have caused Event 2 or vice versa? 
            Respond with JSON:
            {{
                "has_causal_relationship": true/false,
                "strength": 0.0-1.0,
                "description": "explanation",
                "direction": "1->2" or "2->1" or "bidirectional"
            }}
            """

            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": causal_prompt}],
                temperature=0.3,
            )

            analysis = json.loads(response.choices[0].message.content)

            if analysis.get("has_causal_relationship"):
                return EvidenceCorrelation(
                    evidence1_id=evidence1.id,
                    evidence2_id=evidence2.id,
                    correlation_type=CorrelationType.CAUSAL,
                    strength=analysis.get("strength", 0.5),
                    description=analysis.get(
                        "description", "Causal relationship detected"
                    ),
                    supporting_factors=[
                        f"Direction: {analysis.get('direction', 'unknown')}"
                    ],
                )

        except Exception as e:
            logger.error(f"Error analyzing causal correlation: {e}")

        return None

    async def _analyze_contextual_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze contextual correlation"""
        # Check if evidence types are contextually related
        contextual_pairs = [
            (EvidenceType.VIDEO_CLIP, EvidenceType.IMAGE),
            (EvidenceType.METADATA, EvidenceType.SENSOR_DATA),
            (EvidenceType.AUDIO, EvidenceType.VIDEO_CLIP),
        ]

        evidence_types = (evidence1.type, evidence2.type)
        if (
            evidence_types in contextual_pairs
            or evidence_types[::-1] in contextual_pairs
        ):
            return EvidenceCorrelation(
                evidence1_id=evidence1.id,
                evidence2_id=evidence2.id,
                correlation_type=CorrelationType.CONTEXTUAL,
                strength=0.7,
                description=f"Contextually related evidence types: {evidence1.type} and {evidence2.type}",
                supporting_factors=[
                    f"Evidence types: {evidence1.type}, {evidence2.type}"
                ],
            )

        return None

    async def _analyze_semantic_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze semantic correlation using embeddings"""
        if evidence1.embedding and evidence2.embedding:
            # Calculate cosine similarity
            v1 = np.array(evidence1.embedding)
            v2 = np.array(evidence2.embedding)

            similarity = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

            if similarity > 0.7:
                return EvidenceCorrelation(
                    evidence1_id=evidence1.id,
                    evidence2_id=evidence2.id,
                    correlation_type=CorrelationType.SEMANTIC,
                    strength=float(similarity),
                    description=f"High semantic similarity (score: {similarity:.2f})",
                    supporting_factors=[f"Cosine similarity: {similarity:.3f}"],
                )

        return None


# Confidence Scoring Engine
class ConfidenceScorer:
    @staticmethod
    def calculate_evidence_confidence(evidence: Evidence) -> float:
        """Calculate confidence score for a piece of evidence"""
        factors = {
            "source_reliability": 0.3,
            "technical_quality": 0.2,
            "temporal_consistency": 0.2,
            "cross_validation": 0.3,
        }

        scores = {
            "source_reliability": ConfidenceScorer._assess_source_reliability(evidence),
            "technical_quality": ConfidenceScorer._assess_technical_quality(evidence),
            "temporal_consistency": ConfidenceScorer._assess_temporal_consistency(
                evidence
            ),
            "cross_validation": ConfidenceScorer._assess_cross_validation(evidence),
        }

        weighted_score = sum(
            scores[factor] * weight for factor, weight in factors.items()
        )
        return min(max(weighted_score, 0.0), 1.0)

    @staticmethod
    def _assess_source_reliability(evidence: Evidence) -> float:
        """Assess reliability of evidence source"""
        source = evidence.source.lower()

        if "camera" in source or "video" in source:
            return 0.9
        elif "sensor" in source:
            return 0.8
        elif "manual" in source or "report" in source:
            return 0.6
        else:
            return 0.5

    @staticmethod
    def _assess_technical_quality(evidence: Evidence) -> float:
        """Assess technical quality of evidence"""
        if evidence.type == EvidenceType.VIDEO_CLIP:
            # Check for resolution, clarity indicators in metadata
            quality_indicators = evidence.metadata.get("quality_score", 0.7)
            return quality_indicators
        elif evidence.type == EvidenceType.IMAGE:
            # Check image quality metrics
            return evidence.metadata.get("clarity_score", 0.8)
        else:
            return 0.7  # Default for other types

    @staticmethod
    def _assess_temporal_consistency(evidence: Evidence) -> float:
        """Assess temporal consistency"""
        # Check if timestamp is reasonable
        now = datetime.utcnow()
        evidence_age = (now - evidence.timestamp).total_seconds()

        # Fresh evidence (< 24 hours) gets higher score
        if evidence_age < 86400:  # 24 hours
            return 0.9
        elif evidence_age < 604800:  # 1 week
            return 0.7
        else:
            return 0.5

    @staticmethod
    def _assess_cross_validation(evidence: Evidence) -> float:
        """Assess cross-validation with other evidence"""
        # This would check against other evidence in the system
        # For now, return default
        return 0.7


# Initialize configuration
config = get_config()

# Initialize engines
multimodal_analyzer = MultiModalAnalyzer()
correlation_engine = EvidenceCorrelationEngine()

# FastAPI App with versioning support
app = create_versioned_app("Advanced RAG Service")

# CORS middleware - use configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
add_rate_limiting(app, service_name="advanced_rag_service")


# API Endpoints

@v1_endpoint
@app.post("/api/v1/evidence/analyze", 
         tags=["v1.0", "v1.1", "Evidence Analysis"],
         summary="Analyze Evidence File",
         description="Analyze uploaded evidence file with multi-modal processing")
async def analyze_evidence_v1(file: UploadFile = File(...), metadata: str = "{}", 
                               api_version: APIVersion = Depends(get_current_api_version)):
    """Analyze uploaded evidence file"""
    try:
        file_content = await file.read()
        metadata_dict = json.loads(metadata)

        # Determine evidence type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension in multimodal_analyzer.supported_formats["video"]:
            evidence_type = EvidenceType.VIDEO_CLIP
            analysis = await multimodal_analyzer.analyze_video_content(file_content)
        elif file_extension in multimodal_analyzer.supported_formats["image"]:
            evidence_type = EvidenceType.IMAGE
            analysis = await multimodal_analyzer.analyze_image_content(file_content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Create evidence object
        evidence = Evidence(
            id=str(uuid.uuid4()),
            type=evidence_type,
            source=metadata_dict.get("source", "upload"),
            timestamp=datetime.utcnow(),
            location=metadata_dict.get("location"),
            content=file_content,
            metadata={**metadata_dict, **analysis},
            confidence_score=0.0,  # Will be calculated
        )        # Calculate confidence score
        evidence.confidence_score = ConfidenceScorer.calculate_evidence_confidence(
            evidence
        )
        
        # Store evidence
        redis_client = await get_redis_client()
        await redis_client.hset(
            "evidence", evidence.id, json.dumps(asdict(evidence), default=str)
        )
        
        return {
            "evidence_id": evidence.id,
            "analysis": analysis,
            "confidence_score": evidence.confidence_score,
            "evidence_type": evidence_type,
            "api_version": api_version.value,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@v1_endpoint
@app.post("/api/v1/evidence/correlate")
async def find_evidence_correlations(request: CorrelationAnalysisRequest):
    """Find correlations between evidence pieces"""
    try:
        # Retrieve evidence
        redis_client = await get_redis_client()
        evidence_list = []

        for evidence_id in request.evidence_ids:
            evidence_data = await redis_client.hget("evidence", evidence_id)
            if evidence_data:
                evidence_dict = json.loads(evidence_data)
                evidence = Evidence(**evidence_dict)
                evidence_list.append(evidence)

        # Find correlations
        correlations = await correlation_engine.find_correlations(
            evidence_list, request.correlation_types or list(CorrelationType)
        )        # Filter by minimum strength
        filtered_correlations = [
            corr for corr in correlations if corr.strength >= request.min_strength
        ]
        
        return {
            "correlations": [asdict(corr) for corr in filtered_correlations],
            "total_found": len(filtered_correlations),
        }
    except Exception as e:
        logger.error(f"Error finding correlations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@v1_endpoint
@app.post("/api/v1/evidence/chain")
async def build_evidence_chain(evidence_ids: List[str]):
    """Build evidence chain from correlated evidence"""
    try:
        # Get evidence and correlations
        correlation_request = CorrelationAnalysisRequest(evidence_ids=evidence_ids)
        correlations_response = await find_evidence_correlations(correlation_request)
        correlations = correlations_response["correlations"]

        # Build chain
        chain_id = str(uuid.uuid4())

        # Calculate overall confidence
        redis_client = await get_redis_client()
        confidence_scores = []
        for evidence_id in evidence_ids:
            evidence_data = await redis_client.hget("evidence", evidence_id)
            if evidence_data:
                evidence_dict = json.loads(evidence_data)
                confidence_scores.append(evidence_dict.get("confidence_score", 0.5))

        overall_confidence = np.mean(confidence_scores) if confidence_scores else 0.5

        # Generate conclusion using LLM
        conclusion = await _generate_evidence_conclusion(evidence_ids, correlations)

        evidence_chain = EvidenceChain(
            id=chain_id,
            name=f"Evidence Chain {chain_id[:8]}",
            description="Automatically generated evidence chain",
            evidence_ids=evidence_ids,
            correlations=[EvidenceCorrelation(**corr) for corr in correlations],
            confidence_score=overall_confidence,
            temporal_span=(datetime.utcnow() - timedelta(hours=1), datetime.utcnow()),
            conclusion=conclusion,
        )

        # Store chain
        await redis_client.hset(
            "evidence_chains", chain_id, json.dumps(asdict(evidence_chain), default=str)
        )

        return {
            "chain_id": chain_id,
            "evidence_chain": asdict(evidence_chain),
            "confidence_level": _get_confidence_level(overall_confidence),
        }

    except Exception as e:
        logger.error(f"Error building evidence chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_evidence_conclusion(
    evidence_ids: List[str], correlations: List[Dict]
) -> str:
    """Generate conclusion from evidence chain"""
    try:
        conclusion_prompt = f"""
        Based on the following evidence and correlations, generate a comprehensive conclusion:
        
        Evidence IDs: {evidence_ids}
        Correlations: {json.dumps(correlations, indent=2)}
        
        Provide a clear, factual conclusion about what this evidence collectively indicates.
        Focus on the most likely scenario based on the correlations and confidence scores.
        """

        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": conclusion_prompt}],
            max_tokens=300,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error generating conclusion: {e}")
        return "Unable to generate conclusion from available evidence."


def _get_confidence_level(score: float) -> ConfidenceLevel:
    """Convert confidence score to level"""
    if score > 0.8:
        return ConfidenceLevel.HIGH
    elif score > 0.5:
        return ConfidenceLevel.MEDIUM
    elif score > 0.3:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW


@v1_endpoint
@app.post("/api/v1/query/advanced")
async def advanced_query(request: AdvancedQueryRequest):
    """Perform advanced multi-modal query with correlation analysis"""
    try:
        multi_request = MultiModalAnalysisRequest(
            query=request.query,
            include_video=EvidenceType.VIDEO_CLIP in request.evidence_types,
            include_images=EvidenceType.IMAGE in request.evidence_types,
            time_range=(request.temporal_range or {}).get("range"),
        )
        return await analyze_multi_modal(multi_request)
    except Exception as e:
        logger.error(f"Error processing advanced query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@v1_endpoint
@app.post("/api/v1/analyze/multi-modal")
async def analyze_multi_modal(request: MultiModalAnalysisRequest):
    """Run multi-modal analysis via the RAG pipeline"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://rag_service:8000/analysis", json={"query": request.query}
            )
            resp.raise_for_status()
            analysis = resp.json()

        evidence_ids = analysis.get("evidence_ids", [])
        evidence_chain: Dict[str, Any] = {}
        if evidence_ids:
            try:
                evidence_chain = await build_evidence_chain(evidence_ids)
            except Exception as e:  # pragma: no cover - chain failures shouldn't crash
                logger.error(f"Evidence chain build failed: {e}")
        
        return {"analysis": analysis, "evidence_chain": evidence_chain}
    except Exception as e:
        logger.error(f"Error performing RAG analysis: {e}")
        raise HTTPException(status_code=500, detail="RAG analysis failed")


@v1_endpoint
@app.post("/api/v1/rag/query", 
         response_model=TemporalRAGQueryResponse,
         tags=["v1.0", "v1.1", "RAG Queries"],
         summary="Temporal RAG Query",
         description="Process temporal RAG query with chronological event analysis")
@with_retry(
    config=RetryConfig(max_attempts=2, base_delay=1.0),
    exceptions=(WeaviateConnectionError, OpenAIAPIError, TemporalProcessingError)
)
@handle_exceptions(log_error=True, raise_on_critical=False)
async def temporal_rag_query_v1(request: TemporalRAGQueryRequest, 
                                api_version: APIVersion = Depends(get_current_api_version)):
    """
    Process temporal RAG query with enhanced error handling and graceful degradation
    
    This endpoint accepts a query event and returns similar events in chronological order
    with an LLM-generated explanation emphasizing temporal flow and causality.
    
    Features graceful degradation when external services are unavailable.
    """
    query_event = None
    
    try:
        # Validate and create QueryEvent from request
        query_event_data = request.query_event
        
        # Ensure required fields are present
        required_fields = ["camera_id", "timestamp", "label"]
        for field in required_fields:
            if field not in query_event_data:
                raise TemporalProcessingError(
                    f"Missing required field in query_event: {field}"
                )
        
        # Create QueryEvent object
        query_event = QueryEvent(
            camera_id=query_event_data["camera_id"],
            timestamp=query_event_data["timestamp"], 
            label=query_event_data["label"],
            bbox=query_event_data.get("bbox")
        )
        
        # Validate ISO 8601 timestamp format with timezone
        try:
            if not isinstance(query_event.timestamp, str):
                raise ValueError("timestamp must be a string")
            
            # Check for proper ISO 8601 format with timezone
            timestamp_str = query_event.timestamp
            
            # Must contain 'T' separator and timezone info (Z or +/-offset)
            if 'T' not in timestamp_str:
                raise ValueError("timestamp must use 'T' separator")
            
            if not (timestamp_str.endswith('Z') or '+' in timestamp_str[-6:] or '-' in timestamp_str[-6:]):
                raise ValueError("timestamp must include timezone information")
            
            # Must be parseable as datetime
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
        except (ValueError, AttributeError, TypeError) as e:
            raise TemporalProcessingError(
                "timestamp must be in ISO 8601 format (e.g., '2025-06-06T10:30:00Z')",
                original_error=e
            )
        
        # Check service availability before processing
        services_status = {
            'weaviate': service_status_manager.get_service_status('weaviate'),
            'openai': service_status_manager.get_service_status('openai'),
            'embedding_model': service_status_manager.get_service_status('embedding_model')
        }
        
        # Log service status for debugging
        logger.info(f"Service status for temporal query: {services_status}")
        
        # Determine if we can process the request or need fallback
        critical_services_down = []
        if not service_status_manager.is_service_available('weaviate'):
            critical_services_down.append('weaviate')
        if not service_status_manager.is_service_available('embedding_model'):
            critical_services_down.append('embedding_model')
              # If critical services are down, return fallback response
        if critical_services_down:
            logger.warning(f"Critical services unavailable for temporal query: {critical_services_down}")
            fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                query_event, 
                f"Critical services unavailable: {', '.join(critical_services_down)}"
            )
            
            return TemporalRAGQueryResponse(
                linked_explanation=fallback_response.linked_explanation,
                retrieved_context=fallback_response.retrieved_context,
                explanation_confidence=fallback_response.explanation_confidence
            )
            
        # Process the temporal RAG query with enhanced error handling
        try:
            result = await advanced_rag.get_rag_service().process_temporal_query(query_event, request.k)
            
            # Check if result indicates degraded service
            if hasattr(result, 'degraded_mode') and result.degraded_mode:
                logger.info(f"Temporal query processed in degraded mode")
                
            return TemporalRAGQueryResponse(
                linked_explanation=result.linked_explanation,
                retrieved_context=result.retrieved_context,
                explanation_confidence=result.explanation_confidence
            )
            
        except WeaviateConnectionError as e:
            logger.error(f"Weaviate connection error during temporal query: {e}")
            service_status_manager.services['weaviate'].consecutive_failures += 1
            
            # Return fallback response
            fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                query_event, "Weaviate service connection error", e
            )
            
            return TemporalRAGQueryResponse(
                linked_explanation=fallback_response.linked_explanation,
                retrieved_context=fallback_response.retrieved_context,
                explanation_confidence=fallback_response.explanation_confidence
            )
            
        except OpenAIAPIError as e:
            logger.error(f"OpenAI API error during temporal query: {e}")
            service_status_manager.services['openai'].consecutive_failures += 1
            
            # Try to process without OpenAI (degraded mode)
            try:
                # Get events from Weaviate but skip LLM explanation
                similar_events = advanced_rag.get_rag_service().query_weaviate(query_event, request.k)
                chronological_events = advanced_rag.get_rag_service().sort_by_timestamp(similar_events)
                
                # Calculate basic confidence score
                similarity_scores = [event.get("similarity_score", 0.0) for event in chronological_events]
                explanation_confidence = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
                
                degraded_explanation = (
                    f"Temporal analysis for {query_event.label} detected on camera {query_event.camera_id} "
                    f"at {query_event.timestamp}. Retrieved {len(chronological_events)} similar events "
                    f"in chronological order. Detailed AI analysis temporarily unavailable due to "
                    f"AI service limitations. Please review the context events for patterns."
                )
                
                return TemporalRAGQueryResponse(
                    linked_explanation=degraded_explanation,
                    retrieved_context=chronological_events,
                    explanation_confidence=explanation_confidence
                )
                
            except Exception as fallback_error:
                logger.error(f"Fallback processing also failed: {fallback_error}")
                fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                    query_event, "Both primary and fallback processing failed", fallback_error
                )
                
                return TemporalRAGQueryResponse(
                    linked_explanation=fallback_response.linked_explanation,
                    retrieved_context=fallback_response.retrieved_context,
                    explanation_confidence=fallback_response.explanation_confidence
                )
        
        except EmbeddingGenerationError as e:
            logger.error(f"Embedding generation error during temporal query: {e}")
            service_status_manager.services['embedding_model'].consecutive_failures += 1
            
            fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                query_event, "Embedding generation service error", e
            )
            
            return TemporalRAGQueryResponse(
                linked_explanation=fallback_response.linked_explanation,
                retrieved_context=fallback_response.retrieved_context,
                explanation_confidence=fallback_response.explanation_confidence
            )
            
    except TemporalProcessingError as e:
        logger.error(f"Temporal processing validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except EnhancedRAGError as e:
        logger.error(f"Enhanced RAG error during temporal query: {e}")
        raise HTTPException(
            status_code=500 if e.error_type == ErrorType.UNKNOWN_ERROR else 400,
            detail=f"RAG service error: {str(e)}"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error processing temporal RAG query: {e}", exc_info=True)
        
        # Create fallback response even for unexpected errors
        if query_event:
            fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                query_event, "Unexpected system error", e
            )
            
            return TemporalRAGQueryResponse(
                linked_explanation=fallback_response.linked_explanation,
                retrieved_context=fallback_response.retrieved_context,
                explanation_confidence=fallback_response.explanation_confidence
            )
        else:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@legacy_endpoint
@app.get("/health",
         tags=["System Health"],
         summary="Health Check",
         description="Basic health check endpoint")
async def health_check():
    """Enhanced health check endpoint with service dependency status"""
    try:
        # Get service health summary
        service_health = service_status_manager.get_service_health_summary()
        
        # Determine overall health status
        unavailable_services = service_status_manager.get_unavailable_services()
        degraded_services = service_status_manager.get_degraded_services()
        
        if len(unavailable_services) == 0:
            if len(degraded_services) == 0:
                overall_status = "healthy"
            else:
                overall_status = "degraded"
        else:
            # Check if critical services are down
            critical_services = ["weaviate", "embedding_model"]
            critical_down = any(service in unavailable_services for service in critical_services)
            overall_status = "critical" if critical_down else "degraded"
        
        health_info = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": service_health,
            "degraded_services": degraded_services,
            "unavailable_services": unavailable_services,
            "features": {
                "temporal_rag": len(unavailable_services) == 0 or not any(
                    service in unavailable_services for service in ["weaviate", "embedding_model"]
                ),
                "ai_explanations": "openai" not in unavailable_services,
                "vector_search": "weaviate" not in unavailable_services,
                "embedding_generation": "embedding_model" not in unavailable_services
            }
        }
        
        # Return appropriate HTTP status code
        if overall_status == "healthy":
            return health_info
        elif overall_status == "degraded":
            return JSONResponse(content=health_info, status_code=200)  # Still operational
        else:  # critical
            return JSONResponse(content=health_info, status_code=503)  # Service unavailable
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            },
            status_code=503
        )

@legacy_endpoint
@app.get("/health/services")
async def detailed_service_health():
    """Detailed service health endpoint for monitoring"""
    try:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": service_status_manager.get_service_health_summary(),
            "uptime_checks": {
                "weaviate_available": service_status_manager.is_service_available("weaviate"),
                "openai_available": service_status_manager.is_service_available("openai"),
                "redis_available": service_status_manager.is_service_available("redis"),
                "embedding_model_available": service_status_manager.is_service_available("embedding_model")
            }
        }
    except Exception as e:
        logger.error(f"Service health check error: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


# Import shared middleware for rate limiting
from shared.middleware import add_rate_limiting

# Import advanced RAG module  
import advanced_rag
from advanced_rag import QueryEvent

# Import structured configuration
from config import get_config, AdvancedRAGConfig

# Import API versioning system
from api_versioning import (
    create_versioned_app, get_current_api_version, version_manager,
    APIVersion, get_api_versions_info, v1_endpoint, v2_endpoint, legacy_endpoint
)

# Import enhanced error handling
from error_handling import (
    EnhancedRAGError, WeaviateConnectionError, OpenAIAPIError, 
    EmbeddingGenerationError, TemporalProcessingError, ServiceDegradationError,
    FallbackTemporalRAGResponse, with_retry, handle_exceptions,
    RetryConfig, ErrorType
)
from service_status import service_status_manager, ServiceStatus

# Import comprehensive metrics system
from metrics import (
    metrics_collector, monitor_query_performance, monitor_external_service,
    ServiceType, MetricType
)

# API Versioning Information Endpoints
@legacy_endpoint
@app.get("/api/versions", 
         tags=["API Information"],
         summary="Get API Version Information",
         description="Get information about all supported API versions")
async def get_api_versions():
    """Get comprehensive API version information"""
    return get_api_versions_info()

@legacy_endpoint
@app.get("/api/version", 
         tags=["API Information"],
         summary="Get Current API Version",
         description="Get current API version being used for this request")
async def get_current_version(api_version: APIVersion = Depends(get_current_api_version)):
    """Get current API version for this request"""
    info = version_manager.get_version_info(api_version)
    return {
        "version": api_version.value,
        "status": info.status if info else "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "deprecation_warnings": version_manager.get_deprecation_warnings(api_version)
    }

@v1_endpoint
@app.get("/api/v1/version",
         tags=["v1.0", "v1.1", "API Information"],
         summary="Get V1 API Version Info",
         description="Get version information for V1 API endpoints")
async def get_v1_version_info():
    """Get V1 API version information"""
    v1_info = version_manager.get_version_info(APIVersion.V1_0)
    v1_1_info = version_manager.get_version_info(APIVersion.V1_1)
    
    return {
        "v1.0": {
            "status": v1_info.status if v1_info else "unknown",
            "release_date": v1_info.release_date.isoformat() if v1_info else None,
            "deprecation_date": v1_info.deprecation_date.isoformat() if v1_info and v1_info.deprecation_date else None,
            "sunset_date": v1_info.sunset_date.isoformat() if v1_info and v1_info.sunset_date else None,
            "days_until_sunset": v1_info.days_until_sunset if v1_info else None
        },
        "v1.1": {
            "status": v1_1_info.status if v1_1_info else "unknown", 
            "release_date": v1_1_info.release_date.isoformat() if v1_1_info else None,
            "changelog": v1_1_info.changelog if v1_1_info else []
        },
        "recommended": APIVersion.get_latest().value
    }

@v2_endpoint
@app.get("/api/v2/preview",
         tags=["v2.0", "API Information"],
         summary="V2 API Preview",
         description="Preview of upcoming V2 API features")
async def get_v2_preview():
    """Get preview of V2 API features"""
    v2_info = version_manager.get_version_info(APIVersion.V2_0)
    
    return {
        "version": "2.0",
        "status": "planned",
        "planned_release": v2_info.release_date.isoformat() if v2_info else None,
        "new_features": v2_info.changelog if v2_info else [],
        "breaking_changes": v2_info.breaking_changes if v2_info else [],
        "migration_guide": "/docs/v2-migration"  # Future documentation
    }
    

# Application startup and shutdown handlers
@app.on_event("startup")
async def startup_event():
    """Enhanced startup with service initialization and health monitoring"""
    logger.info("Starting Advanced RAG Service with enhanced error handling...")
    
    try:
        # Initialize clients
        await initialize_clients_with_health_checks()
        
        # Define health check functions
        health_checks = {
            "weaviate": check_weaviate_health,
            "openai": check_openai_health,
            "redis": check_redis_health,
        }
        
        # Start health monitoring
        await service_status_manager.start_health_monitoring(health_checks)
        
        # Initial health checks
        for service_name, health_check_func in health_checks.items():
            await service_status_manager.check_service_health(service_name, health_check_func)
        
        logger.info("Advanced RAG Service startup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Don't fail startup completely - allow service to run in degraded mode
        logger.warning("Service starting in degraded mode due to initialization errors")

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown with cleanup"""
    logger.info("Shutting down Advanced RAG Service...")
    
    try:
        # Clean up connections
        if weaviate_client:
            try:
                weaviate_client.close()
                logger.info("Weaviate client closed")
            except Exception as e:
                logger.error(f"Error closing Weaviate client: {e}")
        
        if redis_client:
            try:
                await redis_client.close()
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
        
        logger.info("Advanced RAG Service shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/7")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set - AI analysis will be limited")

# Enhanced client initialization with detailed error handling
async def initialize_clients_with_health_checks():
    """Initialize clients with comprehensive error handling and health checks"""
    global openai_client, weaviate_client
    
    # Initialize OpenAI client
    try:
        if OPENAI_API_KEY:
            openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI client initialized successfully")
        else:
            openai_client = None
            logger.warning("OpenAI client not initialized - no API key provided")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        openai_client = None
    
    # Initialize Weaviate client
    try:
        weaviate_client = weaviate.Client(
            url=WEAVIATE_URL,
            auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None
        )
        logger.info("Weaviate client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Weaviate client: {e}")
        weaviate_client = None

# Service health check functions
async def check_openai_health():
    """Check OpenAI service health"""
    if not openai_client:
        return False
    try:
        # Simple health check - list models (lightweight operation)
        models = await openai_client.models.list()
        return len(models.data) > 0
    except Exception as e:
        logger.debug(f"OpenAI health check failed: {e}")
        return False

async def check_weaviate_health():
    """Check Weaviate service health"""
    if not weaviate_client:
        return False
    try:
        # Simple health check - get cluster info
        health = weaviate_client.cluster.get_nodes_status()
        return len(health) > 0
    except Exception as e:
        logger.debug(f"Weaviate health check failed: {e}")
        return False

async def check_redis_health():
    """Check Redis service health"""
    try:
        # Check Redis connection
        test_client = redis.from_url(REDIS_URL)
        await test_client.ping()
        await test_client.close()
        return True
    except Exception as e:
        logger.debug(f"Redis health check failed: {e}")
        return False

# Initialize clients (will be called during startup)
openai_client = None
weaviate_client = None


# Enums
class EvidenceType(str, Enum):
    VIDEO_CLIP = "video_clip"
    IMAGE = "image"
    AUDIO = "audio"
    METADATA = "metadata"
    SENSOR_DATA = "sensor_data"
    TEXT_LOG = "text_log"


class ConfidenceLevel(str, Enum):
    HIGH = "high"  # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"  # 0.3 - 0.5
    VERY_LOW = "very_low"  # < 0.3


class CorrelationType(str, Enum):
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    CAUSAL = "causal"
    CONTEXTUAL = "contextual"
    SEMANTIC = "semantic"


# Data Models
@dataclass
class Evidence:
    id: str
    type: EvidenceType
    source: str
    timestamp: datetime
    location: Optional[str]
    content: Any
    metadata: Dict[str, Any]
    confidence_score: float
    embedding: Optional[List[float]] = None
    analysis_results: Optional[Dict] = None


@dataclass
class EvidenceCorrelation:
    evidence1_id: str
    evidence2_id: str
    correlation_type: CorrelationType
    strength: float
    description: str
    supporting_factors: List[str]


@dataclass
class EvidenceChain:
    id: str
    name: str
    description: str
    evidence_ids: List[str]
    correlations: List[EvidenceCorrelation]
    confidence_score: float
    temporal_span: Tuple[datetime, datetime]
    conclusion: str


@dataclass
class MultiModalQuery:
    text_query: str
    image_query: Optional[bytes] = None
    video_query: Optional[bytes] = None
    temporal_filters: Optional[Dict] = None
    spatial_filters: Optional[Dict] = None
    confidence_threshold: float = 0.5


# Request/Response Models
class AdvancedQueryRequest(BaseModel):
    query: str
    evidence_types: List[EvidenceType] = []
    temporal_range: Optional[dict] = None
    spatial_filters: Optional[dict] = None
    confidence_threshold: float = 0.5
    include_correlations: bool = True
    max_results: int = 50


class EvidenceAnalysisRequest(BaseModel):
    evidence_ids: List[str]
    analysis_type: str = "comprehensive"
    include_cross_references: bool = True


class CorrelationAnalysisRequest(BaseModel):
    evidence_ids: List[str]
    correlation_types: List[CorrelationType] = []
    min_strength: float = 0.3


class MultiModalAnalysisRequest(BaseModel):
    """Request model for multi-modal RAG analysis"""

    query: str
    include_video: bool = False
    include_images: bool = False
    time_range: Optional[str] = None


class TemporalRAGQueryRequest(BaseModel):
    """Request model for temporal RAG queries"""
    query_event: Dict[str, Any] = Field(..., description="Query event with camera_id, timestamp, label, and optional bbox")
    k: int = Field(default=10, ge=1, le=100, description="Number of similar events to retrieve")


class TemporalRAGQueryResponse(BaseModel):
    """Response model for temporal RAG queries"""
    linked_explanation: str = Field(..., description="LLM explanation emphasizing temporal flow and causality")
    retrieved_context: List[Dict[str, Any]] = Field(..., description="Retrieved events in chronological order")
    explanation_confidence: float = Field(..., description="Confidence score (0-1) based on vector similarity of retrieved context")


# Global state
redis_client: Optional[redis.Redis] = None


async def get_redis_client():
    """Get Redis client"""
    global redis_client
    if not redis_client:
        redis_client = redis.from_url("redis://localhost:6379/7")
    return redis_client


# Multi-Modal Analysis Engine
class MultiModalAnalyzer:
    def __init__(self):
        self.supported_formats = {
            "video": [".mp4", ".avi", ".mov", ".mkv"],
            "image": [".jpg", ".jpeg", ".png", ".bmp"],
            "audio": [".wav", ".mp3", ".aac"],
        }

    async def analyze_video_content(self, video_data: bytes) -> Dict:
        """Analyze video content for objects, activities, and scenes"""
        try:
            # Save video temporarily
            temp_path = f"/tmp/video_{uuid.uuid4().hex}.mp4"
            with open(temp_path, "wb") as f:
                f.write(video_data)

            # Extract frames for analysis
            cap = cv2.VideoCapture(temp_path)
            frames = []
            frame_count = 0

            while cap.isOpened() and frame_count < 10:  # Analyze up to 10 frames
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
                frame_count += 1

            cap.release()

            # Analyze each frame
            analysis_results = {
                "objects_detected": [],
                "activities": [],
                "scene_description": "",
                "technical_metadata": {},
                "temporal_analysis": [],
            }

            for i, frame in enumerate(frames):
                frame_analysis = await self._analyze_frame(frame, i)
                analysis_results["objects_detected"].extend(
                    frame_analysis.get("objects", [])
                )
                analysis_results["activities"].extend(
                    frame_analysis.get("activities", [])
                )
                analysis_results["temporal_analysis"].append(frame_analysis)

            # Generate overall scene description
            analysis_results["scene_description"] = (
                await self._generate_scene_description(analysis_results)
            )

            # Clean up
            Path(temp_path).unlink(missing_ok=True)

            return analysis_results

        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            return {"error": str(e)}

    async def _analyze_frame(self, frame: np.ndarray, frame_index: int) -> Dict:
        """Analyze individual video frame"""
        # Convert frame to base64 for OpenAI Vision API
        _, buffer = cv2.imencode(".jpg", frame)
        frame_base64 = base64.b64encode(buffer).decode("utf-8")

        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this surveillance frame. Identify objects, people, activities, and any notable events. Provide specific details about locations, movements, and interactions.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{frame_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=500,
            )

            analysis_text = response.choices[0].message.content

            # Parse analysis into structured format
            return {
                "frame_index": frame_index,
                "raw_analysis": analysis_text,
                "objects": self._extract_objects_from_analysis(analysis_text),
                "activities": self._extract_activities_from_analysis(analysis_text),
                "timestamp": frame_index * 0.5,  # Assuming 2 FPS sampling
            }

        except Exception as e:
            logger.error(f"Error analyzing frame {frame_index}: {e}")
            return {"frame_index": frame_index, "error": str(e)}

    def _extract_objects_from_analysis(self, analysis_text: str) -> List[Dict]:
        """Extract object information from analysis text"""
        # Simple keyword-based extraction (in practice, use NLP)
        objects = []
        object_keywords = [
            "person",
            "car",
            "vehicle",
            "bag",
            "weapon",
            "door",
            "window",
        ]

        for keyword in object_keywords:
            if keyword in analysis_text.lower():
                objects.append(
                    {
                        "type": keyword,
                        "confidence": 0.8,  # Placeholder
                        "location": "detected",
                    }
                )

        return objects

    def _extract_activities_from_analysis(self, analysis_text: str) -> List[Dict]:
        """Extract activity information from analysis text"""
        activities = []
        activity_keywords = [
            "walking",
            "running",
            "standing",
            "sitting",
            "entering",
            "leaving",
        ]

        for keyword in activity_keywords:
            if keyword in analysis_text.lower():
                activities.append(
                    {
                        "type": keyword,
                        "confidence": 0.7,
                        "description": f"Person {keyword}",
                    }
                )

        return activities

    async def _generate_scene_description(self, analysis_results: Dict) -> str:
        """Generate overall scene description from frame analyses"""
        objects = analysis_results.get("objects_detected", [])
        activities = analysis_results.get("activities", [])

        description_prompt = f"""
        Based on the following detected objects and activities, generate a comprehensive scene description:
        
        Objects: {objects}
        Activities: {activities}
        
        Provide a concise but detailed description of what's happening in this surveillance footage.
        """

        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": description_prompt}],
                max_tokens=200,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating scene description: {e}")
            return "Scene analysis unavailable"

    async def analyze_image_content(self, image_data: bytes) -> Dict:
        """Analyze image content"""
        try:
            # Convert to base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            response = await openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this surveillance image. Describe everything you see including people, objects, activities, and environmental details. Be specific about locations and any notable events.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            analysis = response.choices[0].message.content

            return {
                "description": analysis,
                "objects": self._extract_objects_from_analysis(analysis),
                "activities": self._extract_activities_from_analysis(analysis),
                "scene_type": "surveillance_image",
            }

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {"error": str(e)}


# Evidence Correlation Engine
class EvidenceCorrelationEngine:
    def __init__(self):
        self.correlation_algorithms = {
            CorrelationType.TEMPORAL: self._analyze_temporal_correlation,
            CorrelationType.SPATIAL: self._analyze_spatial_correlation,
            CorrelationType.CAUSAL: self._analyze_causal_correlation,
            CorrelationType.CONTEXTUAL: self._analyze_contextual_correlation,
            CorrelationType.SEMANTIC: self._analyze_semantic_correlation,
        }

    async def find_correlations(
        self,
        evidence_list: List[Evidence],
        correlation_types: List[CorrelationType] = None,
    ) -> List[EvidenceCorrelation]:
        """Find correlations between pieces of evidence"""
        if not correlation_types:
            correlation_types = list(CorrelationType)

        correlations = []

        # Compare each pair of evidence
        for i, evidence1 in enumerate(evidence_list):
            for j, evidence2 in enumerate(evidence_list[i + 1 :], i + 1):
                for corr_type in correlation_types:
                    correlation = await self._analyze_correlation(
                        evidence1, evidence2, corr_type
                    )
                    if correlation and correlation.strength > 0.3:
                        correlations.append(correlation)

        return correlations

    async def _analyze_correlation(
        self,
        evidence1: Evidence,
        evidence2: Evidence,
        correlation_type: CorrelationType,
    ) -> Optional[EvidenceCorrelation]:
        """Analyze correlation between two pieces of evidence"""
        algorithm = self.correlation_algorithms.get(correlation_type)
        if not algorithm:
            return None

        return await algorithm(evidence1, evidence2)

    async def _analyze_temporal_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze temporal correlation"""
        time_diff = abs((evidence1.timestamp - evidence2.timestamp).total_seconds())

        # Strong temporal correlation if within 5 minutes
        if time_diff <= 300:
            strength = 1.0 - (time_diff / 300)
            return EvidenceCorrelation(
                evidence1_id=evidence1.id,
                evidence2_id=evidence2.id,
                correlation_type=CorrelationType.TEMPORAL,
                strength=strength,
                description=f"Events occurred {time_diff:.0f} seconds apart",
                supporting_factors=[f"Time difference: {time_diff:.0f}s"],
            )

        return None

    async def _analyze_spatial_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze spatial correlation"""
        if evidence1.location and evidence2.location:
            # Simple string matching for locations
            if evidence1.location == evidence2.location:
                return EvidenceCorrelation(
                    evidence1_id=evidence1.id,
                    evidence2_id=evidence2.id,
                    correlation_type=CorrelationType.SPATIAL,
                    strength=0.9,
                    description=f"Both events occurred at {evidence1.location}",
                    supporting_factors=[f"Same location: {evidence1.location}"],
                )
            elif (
                evidence1.location in evidence2.location
                or evidence2.location in evidence1.location
            ):
                return EvidenceCorrelation(
                    evidence1_id=evidence1.id,
                    evidence2_id=evidence2.id,
                    correlation_type=CorrelationType.SPATIAL,
                    strength=0.6,
                    description=f"Events in related locations",
                    supporting_factors=[
                        f"Related locations: {evidence1.location}, {evidence2.location}"
                    ],
                )

        return None

    async def _analyze_causal_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze causal correlation using LLM"""
        try:
            causal_prompt = f"""
            Analyze if there's a causal relationship between these two events:
            
            Event 1: {evidence1.metadata.get('description', 'No description')}
            Time: {evidence1.timestamp}
            Location: {evidence1.location}
            
            Event 2: {evidence2.metadata.get('description', 'No description')}
            Time: {evidence2.timestamp}
            Location: {evidence2.location}
            
            Could Event 1 have caused Event 2 or vice versa? 
            Respond with JSON:
            {{
                "has_causal_relationship": true/false,
                "strength": 0.0-1.0,
                "description": "explanation",
                "direction": "1->2" or "2->1" or "bidirectional"
            }}
            """

            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": causal_prompt}],
                temperature=0.3,
            )

            analysis = json.loads(response.choices[0].message.content)

            if analysis.get("has_causal_relationship"):
                return EvidenceCorrelation(
                    evidence1_id=evidence1.id,
                    evidence2_id=evidence2.id,
                    correlation_type=CorrelationType.CAUSAL,
                    strength=analysis.get("strength", 0.5),
                    description=analysis.get(
                        "description", "Causal relationship detected"
                    ),
                    supporting_factors=[
                        f"Direction: {analysis.get('direction', 'unknown')}"
                    ],
                )

        except Exception as e:
            logger.error(f"Error analyzing causal correlation: {e}")

        return None

    async def _analyze_contextual_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze contextual correlation"""
        # Check if evidence types are contextually related
        contextual_pairs = [
            (EvidenceType.VIDEO_CLIP, EvidenceType.IMAGE),
            (EvidenceType.METADATA, EvidenceType.SENSOR_DATA),
            (EvidenceType.AUDIO, EvidenceType.VIDEO_CLIP),
        ]

        evidence_types = (evidence1.type, evidence2.type)
        if (
            evidence_types in contextual_pairs
            or evidence_types[::-1] in contextual_pairs
        ):
            return EvidenceCorrelation(
                evidence1_id=evidence1.id,
                evidence2_id=evidence2.id,
                correlation_type=CorrelationType.CONTEXTUAL,
                strength=0.7,
                description=f"Contextually related evidence types: {evidence1.type} and {evidence2.type}",
                supporting_factors=[
                    f"Evidence types: {evidence1.type}, {evidence2.type}"
                ],
            )

        return None

    async def _analyze_semantic_correlation(
        self, evidence1: Evidence, evidence2: Evidence
    ) -> Optional[EvidenceCorrelation]:
        """Analyze semantic correlation using embeddings"""
        if evidence1.embedding and evidence2.embedding:
            # Calculate cosine similarity
            v1 = np.array(evidence1.embedding)
            v2 = np.array(evidence2.embedding)

            similarity = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

            if similarity > 0.7:
                return EvidenceCorrelation(
                    evidence1_id=evidence1.id,
                    evidence2_id=evidence2.id,
                    correlation_type=CorrelationType.SEMANTIC,
                    strength=float(similarity),
                    description=f"High semantic similarity (score: {similarity:.2f})",
                    supporting_factors=[f"Cosine similarity: {similarity:.3f}"],
                )

        return None


# Confidence Scoring Engine
class ConfidenceScorer:
    @staticmethod
    def calculate_evidence_confidence(evidence: Evidence) -> float:
        """Calculate confidence score for a piece of evidence"""
        factors = {
            "source_reliability": 0.3,
            "technical_quality": 0.2,
            "temporal_consistency": 0.2,
            "cross_validation": 0.3,
        }

        scores = {
            "source_reliability": ConfidenceScorer._assess_source_reliability(evidence),
            "technical_quality": ConfidenceScorer._assess_technical_quality(evidence),
            "temporal_consistency": ConfidenceScorer._assess_temporal_consistency(
                evidence
            ),
            "cross_validation": ConfidenceScorer._assess_cross_validation(evidence),
        }

        weighted_score = sum(
            scores[factor] * weight for factor, weight in factors.items()
        )
        return min(max(weighted_score, 0.0), 1.0)

    @staticmethod
    def _assess_source_reliability(evidence: Evidence) -> float:
        """Assess reliability of evidence source"""
        source = evidence.source.lower()

        if "camera" in source or "video" in source:
            return 0.9
        elif "sensor" in source:
            return 0.8
        elif "manual" in source or "report" in source:
            return 0.6
        else:
            return 0.5

    @staticmethod
    def _assess_technical_quality(evidence: Evidence) -> float:
        """Assess technical quality of evidence"""
        if evidence.type == EvidenceType.VIDEO_CLIP:
            # Check for resolution, clarity indicators in metadata
            quality_indicators = evidence.metadata.get("quality_score", 0.7)
            return quality_indicators
        elif evidence.type == EvidenceType.IMAGE:
            # Check image quality metrics
            return evidence.metadata.get("clarity_score", 0.8)
        else:
            return 0.7  # Default for other types

    @staticmethod
    def _assess_temporal_consistency(evidence: Evidence) -> float:
        """Assess temporal consistency"""
        # Check if timestamp is reasonable
        now = datetime.utcnow()
        evidence_age = (now - evidence.timestamp).total_seconds()

        # Fresh evidence (< 24 hours) gets higher score
        if evidence_age < 86400:  # 24 hours
            return 0.9
        elif evidence_age < 604800:  # 1 week
            return 0.7
        else:
            return 0.5

    @staticmethod
    def _assess_cross_validation(evidence: Evidence) -> float:
        """Assess cross-validation with other evidence"""
        # This would check against other evidence in the system
        # For now, return default
        return 0.7


# Initialize configuration
config = get_config()

# Initialize engines
multimodal_analyzer = MultiModalAnalyzer()
correlation_engine = EvidenceCorrelationEngine()

# FastAPI App with versioning support
app = create_versioned_app("Advanced RAG Service")

# CORS middleware - use configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
add_rate_limiting(app, service_name="advanced_rag_service")


# API Endpoints

@v1_endpoint
@app.post("/api/v1/evidence/analyze", 
         tags=["v1.0", "v1.1", "Evidence Analysis"],
         summary="Analyze Evidence File",
         description="Analyze uploaded evidence file with multi-modal processing")
async def analyze_evidence_v1(file: UploadFile = File(...), metadata: str = "{}", 
                               api_version: APIVersion = Depends(get_current_api_version)):
    """Analyze uploaded evidence file"""
    try:
        file_content = await file.read()
        metadata_dict = json.loads(metadata)

        # Determine evidence type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension in multimodal_analyzer.supported_formats["video"]:
            evidence_type = EvidenceType.VIDEO_CLIP
            analysis = await multimodal_analyzer.analyze_video_content(file_content)
        elif file_extension in multimodal_analyzer.supported_formats["image"]:
            evidence_type = EvidenceType.IMAGE
            analysis = await multimodal_analyzer.analyze_image_content(file_content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Create evidence object
        evidence = Evidence(
            id=str(uuid.uuid4()),
            type=evidence_type,
            source=metadata_dict.get("source", "upload"),
            timestamp=datetime.utcnow(),
            location=metadata_dict.get("location"),
            content=file_content,
            metadata={**metadata_dict, **analysis},
            confidence_score=0.0,  # Will be calculated
        )        # Calculate confidence score
        evidence.confidence_score = ConfidenceScorer.calculate_evidence_confidence(
            evidence
        )
        
        # Store evidence
        redis_client = await get_redis_client()
        await redis_client.hset(
            "evidence", evidence.id, json.dumps(asdict(evidence), default=str)
        )
        
        return {
            "evidence_id": evidence.id,
            "analysis": analysis,
            "confidence_score": evidence.confidence_score,
            "evidence_type": evidence_type,
            "api_version": api_version.value,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@v1_endpoint
@app.post("/api/v1/evidence/correlate")
async def find_evidence_correlations(request: CorrelationAnalysisRequest):
    """Find correlations between evidence pieces"""
    try:
        # Retrieve evidence
        redis_client = await get_redis_client()
        evidence_list = []

        for evidence_id in request.evidence_ids:
            evidence_data = await redis_client.hget("evidence", evidence_id)
            if evidence_data:
                evidence_dict = json.loads(evidence_data)
                evidence = Evidence(**evidence_dict)
                evidence_list.append(evidence)

        # Find correlations
        correlations = await correlation_engine.find_correlations(
            evidence_list, request.correlation_types or list(CorrelationType)
        )        # Filter by minimum strength
        filtered_correlations = [
            corr for corr in correlations if corr.strength >= request.min_strength
        ]
        
        return {
            "correlations": [asdict(corr) for corr in filtered_correlations],
            "total_found": len(filtered_correlations),
        }
    except Exception as e:
        logger.error(f"Error finding correlations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@v1_endpoint
@app.post("/api/v1/evidence/chain")
async def build_evidence_chain(evidence_ids: List[str]):
    """Build evidence chain from correlated evidence"""
    try:
        # Get evidence and correlations
        correlation_request = CorrelationAnalysisRequest(evidence_ids=evidence_ids)
        correlations_response = await find_evidence_correlations(correlation_request)
        correlations = correlations_response["correlations"]

        # Build chain
        chain_id = str(uuid.uuid4())

        # Calculate overall confidence
        redis_client = await get_redis_client()
        confidence_scores = []
        for evidence_id in evidence_ids:
            evidence_data = await redis_client.hget("evidence", evidence_id)
            if evidence_data:
                evidence_dict = json.loads(evidence_data)
                confidence_scores.append(evidence_dict.get("confidence_score", 0.5))

        overall_confidence = np.mean(confidence_scores) if confidence_scores else 0.5

        # Generate conclusion using LLM
        conclusion = await _generate_evidence_conclusion(evidence_ids, correlations)

        evidence_chain = EvidenceChain(
            id=chain_id,
            name=f"Evidence Chain {chain_id[:8]}",
            description="Automatically generated evidence chain",
            evidence_ids=evidence_ids,
            correlations=[EvidenceCorrelation(**corr) for corr in correlations],
            confidence_score=overall_confidence,
            temporal_span=(datetime.utcnow() - timedelta(hours=1), datetime.utcnow()),
            conclusion=conclusion,
        )

        # Store chain
        await redis_client.hset(
            "evidence_chains", chain_id, json.dumps(asdict(evidence_chain), default=str)
        )

        return {
            "chain_id": chain_id,
            "evidence_chain": asdict(evidence_chain),
            "confidence_level": _get_confidence_level(overall_confidence),
        }

    except Exception as e:
        logger.error(f"Error building evidence chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_evidence_conclusion(
    evidence_ids: List[str], correlations: List[Dict]
) -> str:
    """Generate conclusion from evidence chain"""
    try:
        conclusion_prompt = f"""
        Based on the following evidence and correlations, generate a comprehensive conclusion:
        
        Evidence IDs: {evidence_ids}
        Correlations: {json.dumps(correlations, indent=2)}
        
        Provide a clear, factual conclusion about what this evidence collectively indicates.
        Focus on the most likely scenario based on the correlations and confidence scores.
        """

        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": conclusion_prompt}],
            max_tokens=300,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error generating conclusion: {e}")
        return "Unable to generate conclusion from available evidence."


def _get_confidence_level(score: float) -> ConfidenceLevel:
    """Convert confidence score to level"""
    if score > 0.8:
        return ConfidenceLevel.HIGH
    elif score > 0.5:
        return ConfidenceLevel.MEDIUM
    elif score > 0.3:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW


@v1_endpoint
@app.post("/api/v1/query/advanced")
async def advanced_query(request: AdvancedQueryRequest):
    """Perform advanced multi-modal query with correlation analysis"""
    try:
        multi_request = MultiModalAnalysisRequest(
            query=request.query,
            include_video=EvidenceType.VIDEO_CLIP in request.evidence_types,
            include_images=EvidenceType.IMAGE in request.evidence_types,
            time_range=(request.temporal_range or {}).get("range"),
        )
        return await analyze_multi_modal(multi_request)
    except Exception as e:
        logger.error(f"Error processing advanced query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@v1_endpoint
@app.post("/api/v1/analyze/multi-modal")
async def analyze_multi_modal(request: MultiModalAnalysisRequest):
    """Run multi-modal analysis via the RAG pipeline"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://rag_service:8000/analysis", json={"query": request.query}
            )
            resp.raise_for_status()
            analysis = resp.json()

        evidence_ids = analysis.get("evidence_ids", [])
        evidence_chain: Dict[str, Any] = {}
        if evidence_ids:
            try:
                evidence_chain = await build_evidence_chain(evidence_ids)
            except Exception as e:  # pragma: no cover - chain failures shouldn't crash
                logger.error(f"Evidence chain build failed: {e}")
        
        return {"analysis": analysis, "evidence_chain": evidence_chain}
    except Exception as e:
        logger.error(f"Error performing RAG analysis: {e}")
        raise HTTPException(status_code=500, detail="RAG analysis failed")


@v1_endpoint
@app.post("/api/v1/rag/query", 
         response_model=TemporalRAGQueryResponse,
         tags=["v1.0", "v1.1", "RAG Queries"],
         summary="Temporal RAG Query",
         description="Process temporal RAG query with chronological event analysis")
@with_retry(
    config=RetryConfig(max_attempts=2, base_delay=1.0),
    exceptions=(WeaviateConnectionError, OpenAIAPIError, TemporalProcessingError)
)
@handle_exceptions(log_error=True, raise_on_critical=False)
async def temporal_rag_query_v1(request: TemporalRAGQueryRequest, 
                                api_version: APIVersion = Depends(get_current_api_version)):
    """
    Process temporal RAG query with enhanced error handling and graceful degradation
    
    This endpoint accepts a query event and returns similar events in chronological order
    with an LLM-generated explanation emphasizing temporal flow and causality.
    
    Features graceful degradation when external services are unavailable.
    """
    query_event = None
    
    try:
        # Validate and create QueryEvent from request
        query_event_data = request.query_event
        
        # Ensure required fields are present
        required_fields = ["camera_id", "timestamp", "label"]
        for field in required_fields:
            if field not in query_event_data:
                raise TemporalProcessingError(
                    f"Missing required field in query_event: {field}"
                )
        
        # Create QueryEvent object
        query_event = QueryEvent(
            camera_id=query_event_data["camera_id"],
            timestamp=query_event_data["timestamp"], 
            label=query_event_data["label"],
            bbox=query_event_data.get("bbox")
        )
        
        # Validate ISO 8601 timestamp format with timezone
        try:
            if not isinstance(query_event.timestamp, str):
                raise ValueError("timestamp must be a string")
            
            # Check for proper ISO 8601 format with timezone
            timestamp_str = query_event.timestamp
            
            # Must contain 'T' separator and timezone info (Z or +/-offset)
            if 'T' not in timestamp_str:
                raise ValueError("timestamp must use 'T' separator")
            
            if not (timestamp_str.endswith('Z') or '+' in timestamp_str[-6:] or '-' in timestamp_str[-6:]):
                raise ValueError("timestamp must include timezone information")
            
            # Must be parseable as datetime
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
        except (ValueError, AttributeError, TypeError) as e:
            raise TemporalProcessingError(
                "timestamp must be in ISO 8601 format (e.g., '2025-06-06T10:30:00Z')",
                original_error=e
            )
        
        # Check service availability before processing
        services_status = {
            'weaviate': service_status_manager.get_service_status('weaviate'),
            'openai': service_status_manager.get_service_status('openai'),
            'embedding_model': service_status_manager.get_service_status('embedding_model')
        }
        
        # Log service status for debugging
        logger.info(f"Service status for temporal query: {services_status}")
        
        # Determine if we can process the request or need fallback
        critical_services_down = []
        if not service_status_manager.is_service_available('weaviate'):
            critical_services_down.append('weaviate')
        if not service_status_manager.is_service_available('embedding_model'):
            critical_services_down.append('embedding_model')
              # If critical services are down, return fallback response
        if critical_services_down:
            logger.warning(f"Critical services unavailable for temporal query: {critical_services_down}")
            fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                query_event, 
                f"Critical services unavailable: {', '.join(critical_services_down)}"
            )
            
            return TemporalRAGQueryResponse(
                linked_explanation=fallback_response.linked_explanation,
                retrieved_context=fallback_response.retrieved_context,
                explanation_confidence=fallback_response.explanation_confidence
            )
            
        # Process the temporal RAG query with enhanced error handling
        try:
            result = await advanced_rag.get_rag_service().process_temporal_query(query_event, request.k)
            
            # Check if result indicates degraded service
            if hasattr(result, 'degraded_mode') and result.degraded_mode:
                logger.info(f"Temporal query processed in degraded mode")
                
            return TemporalRAGQueryResponse(
                linked_explanation=result.linked_explanation,
                retrieved_context=result.retrieved_context,
                explanation_confidence=result.explanation_confidence
            )
            
        except WeaviateConnectionError as e:
            logger.error(f"Weaviate connection error during temporal query: {e}")
            service_status_manager.services['weaviate'].consecutive_failures += 1
            
            # Return fallback response
            fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                query_event, "Weaviate service connection error", e
            )
            
            return TemporalRAGQueryResponse(
                linked_explanation=fallback_response.linked_explanation,
                retrieved_context=fallback_response.retrieved_context,
                explanation_confidence=fallback_response.explanation_confidence
            )
            
        except OpenAIAPIError as e:
            logger.error(f"OpenAI API error during temporal query: {e}")
            service_status_manager.services['openai'].consecutive_failures += 1
            
            # Try to process without OpenAI (degraded mode)
            try:
                # Get events from Weaviate but skip LLM explanation
                similar_events = advanced_rag.get_rag_service().query_weaviate(query_event, request.k)
                chronological_events = advanced_rag.get_rag_service().sort_by_timestamp(similar_events)
                
                # Calculate basic confidence score
                similarity_scores = [event.get("similarity_score", 0.0) for event in chronological_events]
                explanation_confidence = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
                
                degraded_explanation = (
                    f"Temporal analysis for {query_event.label} detected on camera {query_event.camera_id} "
                    f"at {query_event.timestamp}. Retrieved {len(chronological_events)} similar events "
                    f"in chronological order. Detailed AI analysis temporarily unavailable due to "
                    f"AI service limitations. Please review the context events for patterns."
                )
                
                return TemporalRAGQueryResponse(
                    linked_explanation=degraded_explanation,
                    retrieved_context=chronological_events,
                    explanation_confidence=explanation_confidence
                )
                
            except Exception as fallback_error:
                logger.error(f"Fallback processing also failed: {fallback_error}")
                fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                    query_event, "Both primary and fallback processing failed", fallback_error
                )
                
                return TemporalRAGQueryResponse(
                    linked_explanation=fallback_response.linked_explanation,
                    retrieved_context=fallback_response.retrieved_context,
                    explanation_confidence=fallback_response.explanation_confidence
                )
        
        except EmbeddingGenerationError as e:
            logger.error(f"Embedding generation error during temporal query: {e}")
            service_status_manager.services['embedding_model'].consecutive_failures += 1
            
            fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                query_event, "Embedding generation service error", e
            )
            
            return TemporalRAGQueryResponse(
                linked_explanation=fallback_response.linked_explanation,
                retrieved_context=fallback_response.retrieved_context,
                explanation_confidence=fallback_response.explanation_confidence
            )
            
    except TemporalProcessingError as e:
        logger.error(f"Temporal processing validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except EnhancedRAGError as e:
        logger.error(f"Enhanced RAG error during temporal query: {e}")
        raise HTTPException(
            status_code=500 if e.error_type == ErrorType.UNKNOWN_ERROR else 400,
            detail=f"RAG service error: {str(e)}"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error processing temporal RAG query: {e}", exc_info=True)
        
        # Create fallback response even for unexpected errors
        if query_event:
            fallback_response = FallbackTemporalRAGResponse.create_minimal_response(
                query_event, "Unexpected system error", e
            )
            
            return TemporalRAGQueryResponse(
                linked_explanation=fallback_response.linked_explanation,
                retrieved_context=fallback_response.retrieved_context,
                explanation_confidence=fallback_response.explanation_confidence
            )
        else:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# =============================================================================
# METRICS AND MONITORING ENDPOINTS
# =============================================================================

@legacy_endpoint
@app.get("/metrics",
         tags=["Monitoring", "Metrics"],
         summary="Prometheus Metrics",
         description="Get Prometheus-compatible metrics for monitoring",
         response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Get Prometheus metrics endpoint for monitoring and alerting"""
    try:
        # Update current service availability before returning metrics
        await update_service_availability_metrics()
        
        # Return Prometheus-formatted metrics
        from fastapi.responses import PlainTextResponse
        metrics_data = metrics_collector.get_metrics_data()
        return PlainTextResponse(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return PlainTextResponse(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain"
        )

@legacy_endpoint
@app.get("/metrics/summary",
         tags=["Monitoring", "Metrics"],
         summary="Metrics Summary",
         description="Get human-readable metrics summary")
async def get_metrics_summary():
    """Get metrics summary in JSON format"""
    try:
        # Update service availability
        await update_service_availability_metrics()
        
        # Calculate some basic statistics
        current_time = datetime.utcnow()
        
        return {
            "timestamp": current_time.isoformat(),
            "service": "advanced_rag_service",
            "version": "1.0.0",
            "metrics_enabled": metrics_collector.enabled,
            "service_status": {
                "weaviate": service_status_manager.is_service_available("weaviate"),
                "openai": service_status_manager.is_service_available("openai"),
                "redis": service_status_manager.is_service_available("redis"),
                "embedding_model": service_status_manager.is_service_available("embedding_model")
            },
            "performance_indicators": {
                "active_queries": "See /metrics for detailed Prometheus metrics",
                "cache_hit_rates": "See /metrics for detailed cache statistics",
                "service_response_times": "See /metrics for detailed latency histograms"
            },
            "metrics_endpoint": "/metrics",
            "documentation": "Use /metrics endpoint for Prometheus scraping"
        }
    except Exception as e:
        logger.error(f"Error generating metrics summary: {e}")
        return JSONResponse(
            content={"error": str(e), "timestamp": datetime.utcnow().isoformat()},
            status_code=500
        )

async def update_service_availability_metrics():
    """Update service availability metrics for Prometheus"""
    try:
        # Check and update service availability
        weaviate_available = await check_weaviate_health()
        openai_available = await check_openai_health()
        redis_available = await check_redis_health()
        
        # Update metrics
        metrics_collector.update_service_availability(ServiceType.WEAVIATE, weaviate_available)
        metrics_collector.update_service_availability(ServiceType.OPENAI, openai_available)
        metrics_collector.update_service_availability(ServiceType.REDIS, redis_available)
        
        # Update embedding model availability based on service status
        embedding_available = service_status_manager.is_service_available("embedding_model")
        metrics_collector.update_service_availability(ServiceType.EMBEDDING_MODEL, embedding_available)
        
    except Exception as e:
        logger.error(f"Error updating service availability metrics: {e}")