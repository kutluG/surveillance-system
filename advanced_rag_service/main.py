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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import base64
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
import numpy as np
from PIL import Image
import cv2
import weaviate
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
openai_client = AsyncOpenAI(api_key="your-openai-api-key")
weaviate_client = weaviate.Client("http://localhost:8080")


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


# Initialize engines
multimodal_analyzer = MultiModalAnalyzer()
correlation_engine = EvidenceCorrelationEngine()

# FastAPI App
app = FastAPI(
    title="Advanced RAG Service",
    description="Enhanced evidence processing with multi-modal analysis and correlation",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints
@app.post("/evidence/analyze")
async def analyze_evidence(file: UploadFile = File(...), metadata: str = "{}"):
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
        )

        # Calculate confidence score
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
        }

    except Exception as e:
        logger.error(f"Error analyzing evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evidence/correlate")
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
        )

        # Filter by minimum strength
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


@app.post("/evidence/chain")
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


@app.post("/query/advanced")
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


@app.post("/analyze/multi-modal")
async def analyze_multi_modal(request: MultiModalAnalysisRequest):
    """Run multi-modal analysis via the RAG pipeline"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://rag_service:8000/analysis", json={"query": request.query}
            )
            resp.raise_for_status()
            analysis = resp.json()

    except Exception as e:
        logger.error(f"Error performing RAG analysis: {e}")
        raise HTTPException(status_code=500, detail="RAG analysis failed")

    evidence_ids = analysis.get("evidence_ids", [])
    evidence_chain: Dict[str, Any] = {}
    if evidence_ids:
        try:
            evidence_chain = await build_evidence_chain(evidence_ids)
        except Exception as e:  # pragma: no cover - chain failures shouldn't crash
            logger.error(f"Evidence chain build failed: {e}")

    return {"analysis": analysis, "evidence_chain": evidence_chain}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)
