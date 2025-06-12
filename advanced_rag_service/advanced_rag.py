"""
Advanced RAG Service with Temporal Ordering and Video Metadata

This module implements temporal-aware event handling with:
- Event insertion into Weaviate with timestamp fields (ISO 8601)
- SentenceTransformer embedding generation
- Vector similarity search with temporal ordering
- Chronological sorting and causality-focused LLM prompts
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import weaviate
import weaviate.classes as wvc
from sentence_transformers import SentenceTransformer
from openai import AsyncOpenAI
from prometheus_client import Gauge

# Configure logging
logger = logging.getLogger(__name__)

# Prometheus metrics
rag_explanation_confidence = Gauge(
    'rag_explanation_confidence',
    'Confidence score for RAG explanations based on vector similarity',
    ['camera_id', 'label']
)

# Environment configuration
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@dataclass
class QueryEvent:
    """Event structure for temporal queries"""
    camera_id: str
    timestamp: str  # ISO 8601 format
    label: str
    bbox: Optional[Dict[str, float]] = None

@dataclass  
class TemporalRAGResponse:
    """Response structure for temporal RAG queries"""
    linked_explanation: str
    retrieved_context: List[Dict[str, Any]]
    explanation_confidence: float

class AdvancedRAGService:
    """Advanced RAG Service with temporal ordering capabilities"""
    
    def __init__(self):
        """Initialize the Advanced RAG Service"""
        self.embedding_model = None
        self.weaviate_client = None
        self.openai_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize all required clients"""
        try:
            # Initialize SentenceTransformer
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info(f"Initialized SentenceTransformer model: {EMBEDDING_MODEL_NAME}")
            
            # Initialize Weaviate client
            self.weaviate_client = weaviate.connect_to_custom(
                http_host="weaviate",
                http_port=8080,
                http_secure=False,
                grpc_host="weaviate", 
                grpc_port=50051,
                grpc_secure=False,
                auth_credentials=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None,
                headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else None,
            )
            logger.info("Connected to Weaviate")
            
            # Initialize OpenAI client
            if OPENAI_API_KEY:
                self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                logger.info("Initialized OpenAI client")
            else:
                logger.warning("OpenAI API key not provided - LLM functionality will be limited")
                
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise
    
    def get_event_embedding(self, event: QueryEvent) -> List[float]:
        """
        Generate embeddings for a query event using SentenceTransformer
        
        Args:
            event: QueryEvent containing camera_id, timestamp, label, and bbox
            
        Returns:
            List of embedding values as floats
        """
        try:
            # Create text representation of the event for embedding
            event_text = f"Camera {event.camera_id} detected {event.label} at {event.timestamp}"
            if event.bbox:
                bbox_str = f"x:{event.bbox.get('x', 0):.2f} y:{event.bbox.get('y', 0):.2f} " \
                          f"w:{event.bbox.get('width', 0):.2f} h:{event.bbox.get('height', 0):.2f}"
                event_text += f" in region [{bbox_str}]"
            
            # Generate embedding
            embedding = self.embedding_model.encode(event_text, convert_to_tensor=False)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error generating embedding for event: {e}")
            raise
    
    def insert_event_to_weaviate(self, event: QueryEvent, additional_metadata: Optional[Dict] = None) -> str:
        """
        Insert event into Weaviate with timestamp fields (ISO 8601)
        
        Args:
            event: QueryEvent to insert
            additional_metadata: Optional additional metadata
            
        Returns:
            Event ID of inserted object
        """
        try:
            # Ensure Weaviate collection exists
            self._ensure_temporal_event_schema()
            
            # Generate embedding
            embedding = self.get_event_embedding(event)
            
            # Prepare properties with timestamp
            properties = {
                "camera_id": event.camera_id,
                "timestamp": event.timestamp,  # ISO 8601 format
                "label": event.label,
                "bbox_x": event.bbox.get("x", 0.0) if event.bbox else 0.0,
                "bbox_y": event.bbox.get("y", 0.0) if event.bbox else 0.0,
                "bbox_width": event.bbox.get("width", 0.0) if event.bbox else 0.0,
                "bbox_height": event.bbox.get("height", 0.0) if event.bbox else 0.0,
                "event_type": "temporal_event",
                "confidence": additional_metadata.get("confidence", 1.0) if additional_metadata else 1.0
            }
            
            # Add any additional metadata
            if additional_metadata:
                for key, value in additional_metadata.items():
                    if key not in properties:
                        properties[f"meta_{key}"] = str(value)
            
            # Insert into Weaviate
            collection = self.weaviate_client.collections.get("TemporalEvent")
            event_id = collection.data.insert(
                properties=properties,
                vector=embedding
            )
            
            logger.info(f"Inserted temporal event {event_id} for camera {event.camera_id}")
            return str(event_id)
            
        except Exception as e:
            logger.error(f"Error inserting event to Weaviate: {e}")
            raise
    
    def _ensure_temporal_event_schema(self):
        """Ensure TemporalEvent collection exists in Weaviate"""
        try:
            if not self.weaviate_client.collections.exists("TemporalEvent"):
                self.weaviate_client.collections.create(
                    name="TemporalEvent",
                    vectorizer_config=wvc.config.Configure.Vectorizer.none(),
                    properties=[
                        wvc.config.Property(name="camera_id", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="timestamp", data_type=wvc.config.DataType.DATE),
                        wvc.config.Property(name="label", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="bbox_x", data_type=wvc.config.DataType.NUMBER),
                        wvc.config.Property(name="bbox_y", data_type=wvc.config.DataType.NUMBER),
                        wvc.config.Property(name="bbox_width", data_type=wvc.config.DataType.NUMBER),
                        wvc.config.Property(name="bbox_height", data_type=wvc.config.DataType.NUMBER),
                        wvc.config.Property(name="event_type", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="confidence", data_type=wvc.config.DataType.NUMBER),
                    ]
                )
                logger.info("Created TemporalEvent collection in Weaviate")
        except Exception as e:
            logger.error(f"Error ensuring schema: {e}")
            raise
    
    def query_weaviate(self, query_event: QueryEvent, k: int = 10) -> List[Dict[str, Any]]:
        """
        Query Weaviate for top-k nearest neighbors by vector similarity
        
        Args:
            query_event: QueryEvent to search for similar events
            k: Number of nearest neighbors to retrieve
            
        Returns:
            List of similar events with metadata
        """
        try:
            # Generate embedding for query event
            query_embedding = self.get_event_embedding(query_event)
            
            # Query Weaviate
            collection = self.weaviate_client.collections.get("TemporalEvent")
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=k,
                return_metadata=wvc.query.MetadataQuery(
                    distance=True,
                    certainty=True,
                    creation_time=True
                )
            )
              # Convert results to list of dictionaries
            results = []
            for obj in response.objects:
                # Extract similarity score (distance) and normalize to 0-1 range
                # Weaviate distance is typically 0-2, where 0 = identical, 2 = most different
                # We convert to similarity: similarity = 1 - (distance / 2)
                distance = obj.metadata.distance if obj.metadata else 1.0
                similarity_score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
                
                result = {
                    "id": str(obj.uuid),
                    "properties": obj.properties,
                    "distance": distance,
                    "certainty": obj.metadata.certainty if obj.metadata else None,
                    "creation_time": obj.metadata.creation_time if obj.metadata else None,
                    "similarity_score": similarity_score
                }
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} similar events from Weaviate")
            return results
            
        except Exception as e:
            logger.error(f"Error querying Weaviate: {e}")
            raise
    
    def sort_by_timestamp(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort retrieved results by timestamp in ascending order (chronological)
        
        Args:
            events: List of events from Weaviate query
            
        Returns:
            Events sorted by timestamp in ascending order
        """
        try:
            def get_timestamp(event):
                try:
                    properties = event.get("properties", {})
                    if properties is None:
                        return datetime.min.replace(tzinfo=None)
                    
                    timestamp_str = properties.get("timestamp", "")
                    if not timestamp_str:
                        return datetime.min.replace(tzinfo=None)
                    
                    # Handle ISO 8601 format with Z suffix
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str.replace('Z', '+00:00')
                    
                    # Parse timestamp and convert to naive datetime for consistent comparison
                    dt = datetime.fromisoformat(timestamp_str)
                    if dt.tzinfo is not None:
                        # Convert to UTC and then make naive
                        dt = dt.replace(tzinfo=None)
                    
                    return dt
                except (ValueError, AttributeError, TypeError):
                    return datetime.min.replace(tzinfo=None)
            
            sorted_events = sorted(events, key=get_timestamp)
            logger.info(f"Sorted {len(sorted_events)} events chronologically")
            return sorted_events
            
        except Exception as e:
            logger.error(f"Error sorting events by timestamp: {e}")
            return events  # Return unsorted if sorting fails
    
    async def construct_temporal_prompt(self, query_event: QueryEvent, context_events: List[Dict[str, Any]]) -> str:
        """
        Construct LLM prompts emphasizing temporal flow and causality
        
        Args:
            query_event: The original query event
            context_events: Retrieved context events in chronological order
            
        Returns:
            Constructed prompt for LLM
        """
        try:
            # Build temporal context description
            temporal_context = []
            for i, event in enumerate(context_events):
                props = event["properties"]
                timestamp = props.get("timestamp", "unknown")
                camera_id = props.get("camera_id", "unknown")
                label = props.get("label", "unknown")
                confidence = props.get("confidence", 0.0)
                
                temporal_context.append(
                    f"{i+1}. [{timestamp}] Camera {camera_id}: {label} "
                    f"(confidence: {confidence:.2f})"
                )
            
            # Construct prompt emphasizing temporal flow and causality
            prompt = f"""
You are analyzing surveillance events with a focus on temporal relationships and causality. 

QUERY EVENT:
- Camera: {query_event.camera_id}
- Time: {query_event.timestamp}  
- Detection: {query_event.label}
- Location: {query_event.bbox if query_event.bbox else "Not specified"}

TEMPORAL CONTEXT (chronologically ordered):
{chr(10).join(temporal_context)}

ANALYSIS INSTRUCTIONS:
1. Focus on the temporal sequence and flow of events
2. Identify potential causal relationships between events
3. Consider spatial proximity (same camera vs different cameras)
4. Look for patterns that might indicate related activities
5. Assess if the query event fits into a larger sequence of events

Provide a detailed explanation that emphasizes:
- How events relate to each other temporally
- Potential cause-and-effect relationships  
- Whether this appears to be part of a larger pattern
- Any anomalies or significant changes in the sequence

Your response should help security personnel understand not just what happened, but how events may be connected through time and causality.
"""
            
            return prompt.strip()
            
        except Exception as e:
            logger.error(f"Error constructing temporal prompt: {e}")
            return f"Error constructing prompt for query event at {query_event.timestamp}"
    
    async def process_temporal_query(self, query_event: QueryEvent, k: int = 10) -> TemporalRAGResponse:
        """
        Process a complete temporal RAG query
        
        Args:
            query_event: Event to query for
            k: Number of similar events to retrieve
            
        Returns:
            TemporalRAGResponse with explanation and context
        """
        try:
            # Step 1: Query Weaviate for similar events
            similar_events = self.query_weaviate(query_event, k)
            
            # Step 2: Sort by timestamp chronologically
            chronological_events = self.sort_by_timestamp(similar_events)
            
            # Step 3: Construct temporal prompt
            prompt = await self.construct_temporal_prompt(query_event, chronological_events)
              # Step 4: Compute overall explanation confidence
            # Calculate average similarity score across all retrieved snippets
            similarity_scores = [event.get("similarity_score", 0.0) for event in chronological_events]
            explanation_confidence = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
            
            # Step 5: Generate LLM explanation
            explanation = ""
            if self.openai_client:
                try:
                    response = await self.openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=800,
                        temperature=0.3
                    )
                    explanation = response.choices[0].message.content.strip()
                except Exception as e:
                    logger.error(f"Error generating LLM explanation: {e}")
                    explanation = "LLM explanation unavailable due to API error"
            else:
                explanation = "LLM explanation unavailable - OpenAI API key not configured"
              # Step 6: Record Prometheus metric
            rag_explanation_confidence.labels(
                camera_id=query_event.camera_id,
                label=query_event.label
            ).set(explanation_confidence)
            
            # Step 7: Return structured response
            return TemporalRAGResponse(
                linked_explanation=explanation,
                retrieved_context=chronological_events,
                explanation_confidence=explanation_confidence
            )
            
        except Exception as e:
            logger.error(f"Error processing temporal query: {e}")
            raise

# Global instance
rag_service = AdvancedRAGService()
