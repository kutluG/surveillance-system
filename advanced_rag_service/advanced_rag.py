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
import time
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import weaviate
import weaviate.classes as wvc
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    # Fallback if SentenceTransformers is not available
    logging.warning(f"SentenceTransformers not available: {e}")
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False
from openai import AsyncOpenAI
from prometheus_client import Gauge

# Import dependency injection framework
from dependency_injection import (
    AbstractEmbeddingModel, AbstractWeaviateClient, AbstractOpenAIClient,
    DependencyContainer, get_container
)

# Import structured configuration
from config import get_config, AdvancedRAGConfig

# Import comprehensive metrics system
try:
    from metrics import (
        metrics_collector, monitor_external_service, ServiceType
    )
    METRICS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Metrics system not available: {e}")
    METRICS_AVAILABLE = False
    # Mock metrics collector
    class MockMetricsCollector:
        def record_vector_search_metrics(self, *args, **kwargs): pass
        def record_embedding_metrics(self, *args, **kwargs): pass
        def record_external_service_metrics(self, *args, **kwargs): pass
        def time_vector_search(self, *args, **kwargs):
            from contextlib import nullcontext
            return nullcontext()
        def time_external_service(self, *args, **kwargs):
            from contextlib import nullcontext
            return nullcontext()
    metrics_collector = MockMetricsCollector()
    def monitor_external_service(*args, **kwargs):
        def decorator(func): return func
        return decorator

# Enhanced error handling imports
try:
    from error_handling import (
        WeaviateConnectionError, OpenAIAPIError, EmbeddingGenerationError,
        TemporalProcessingError, with_retry, handle_exceptions, RetryConfig
    )
    from service_status import service_status_manager
except ImportError as e:
    # Fallback if enhanced error handling is not available
    logging.warning(f"Enhanced error handling not available: {e}")
    # Define minimal fallback classes
    class WeaviateConnectionError(Exception): pass
    class OpenAIAPIError(Exception): pass
    class EmbeddingGenerationError(Exception): pass
    class TemporalProcessingError(Exception): pass
    class RetryConfig: 
        def __init__(self, **kwargs): pass
    def with_retry(**kwargs): 
        def decorator(func): return func
        return decorator
    def handle_exceptions(**kwargs): 
        def decorator(func): return func
        return decorator
    service_status_manager = None

# Advanced caching system imports
try:
    from advanced_caching import (
        AdvancedCacheManager, CacheType, get_cache_manager, cached
    )
    ADVANCED_CACHING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Advanced caching not available: {e}")
    ADVANCED_CACHING_AVAILABLE = False
    
    # Mock cache manager for fallback
    class MockCacheManager:
        async def get(self, *args, **kwargs): return None
        async def set(self, *args, **kwargs): pass
        async def delete(self, *args, **kwargs): return False
        async def clear(self, *args, **kwargs): pass
    
    async def get_cache_manager(): return MockCacheManager()
    
    class CacheType:
        EMBEDDING = "embedding"
        QUERY = "query"
        API_RESPONSE = "api_response"
        METADATA = "metadata"

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
    """Event structure for temporal queries with enhanced timestamp validation"""
    camera_id: str
    timestamp: str  # ISO 8601 format
    label: str
    bbox: Optional[Dict[str, float]] = None

    def __post_init__(self):
        """Validate timestamp format and constraints after initialization"""
        # Import here to avoid circular dependencies
        from error_handling import TemporalProcessingError
        
        # Validate timestamp type
        if not isinstance(self.timestamp, str):
            raise TemporalProcessingError(
                "timestamp must be a string in ISO 8601 format",
                original_error=TypeError(f"Expected str, got {type(self.timestamp)}")
            )
        
        # Validate ISO 8601 format requirements
        timestamp_str = self.timestamp.strip()
        
        # Must contain 'T' separator for date/time
        if 'T' not in timestamp_str:
            raise TemporalProcessingError(
                "timestamp must use 'T' separator between date and time (ISO 8601 format)",
                original_error=ValueError("Missing 'T' separator")
            )
        
        # Must include timezone information (Z or +/-offset)
        has_utc_z = timestamp_str.endswith('Z')
        has_offset = ('+' in timestamp_str[-6:] or '-' in timestamp_str[-6:])
        
        if not (has_utc_z or has_offset):
            raise TemporalProcessingError(
                "timestamp must include timezone information (Z for UTC or +/-HH:MM offset)",
                original_error=ValueError("Missing timezone information")
            )
        
        # Must be parseable as valid datetime
        try:
            # Convert Z suffix to standard +00:00 for parsing
            normalized_timestamp = timestamp_str.replace('Z', '+00:00')
            parsed_datetime = datetime.fromisoformat(normalized_timestamp)
            
            # Additional business rule validations
            self._validate_timestamp_constraints(parsed_datetime)
            
        except (ValueError, AttributeError, TypeError) as e:            raise TemporalProcessingError(
                f"timestamp '{timestamp_str}' is not a valid ISO 8601 format. "
                f"Expected format: 'YYYY-MM-DDTHH:MM:SSZ' or 'YYYY-MM-DDTHH:MM:SS+HH:MM'",
                original_error=e
            )
    
    def _validate_timestamp_constraints(self, parsed_datetime: datetime):
        """Apply business logic constraints to the timestamp"""
        from error_handling import TemporalProcessingError
        
        # Convert to UTC for consistent comparison
        if parsed_datetime.tzinfo is None:
            # If no timezone info, assume UTC
            utc_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            utc_datetime = parsed_datetime.astimezone(timezone.utc)
        
        now_utc = datetime.now(timezone.utc)
        
        # Check if timestamp is too far in the future (more than 1 minute)
        if utc_datetime > now_utc:
            time_diff = (utc_datetime - now_utc).total_seconds()
            if time_diff > 60:  # Allow small clock skew
                raise TemporalProcessingError(
                    f"timestamp cannot be more than 1 minute in the future (difference: {time_diff:.1f}s)",
                    original_error=ValueError("Future timestamp beyond tolerance")
                )
        
        # Check if timestamp is too old (more than 30 days)
        if utc_datetime < now_utc:
            time_diff = (now_utc - utc_datetime).total_seconds()
            max_age_seconds = 30 * 24 * 60 * 60  # 30 days
            if time_diff > max_age_seconds:
                raise TemporalProcessingError(
                    f"timestamp is too old (age: {time_diff / (24 * 60 * 60):.1f} days, max: 30 days)",
                    original_error=ValueError("Timestamp too old")
                )
    
    @property
    def parsed_timestamp(self) -> datetime:
        """Get the timestamp as a parsed datetime object"""
        # This property assumes timestamp has been validated in __post_init__
        normalized_timestamp = self.timestamp.replace('Z', '+00:00')
        return datetime.fromisoformat(normalized_timestamp)
    
    def is_recent(self, max_age_minutes: int = 60) -> bool:
        """Check if the event timestamp is recent within the specified minutes"""
        now = datetime.now(self.parsed_timestamp.tzinfo)
        age_seconds = (now - self.parsed_timestamp).total_seconds()
        return age_seconds <= (max_age_minutes * 60)

@dataclass  
class TemporalRAGResponse:
    """Response structure for temporal RAG queries"""
    linked_explanation: str
    retrieved_context: List[Dict[str, Any]]
    explanation_confidence: float

class AdvancedRAGService:
    """Advanced RAG Service with temporal ordering capabilities"""
    
    def __init__(self, container: Optional[DependencyContainer] = None):
        """Initialize the Advanced RAG Service with dependency injection
        
        Args:
            container: Dependency injection container. If None, uses global container.
        """
        self.container = container or get_container()
        self.embedding_model: Optional[AbstractEmbeddingModel] = None
        self.weaviate_client: Optional[AbstractWeaviateClient] = None
        self.openai_client: Optional[AbstractOpenAIClient] = None
        self._initialize_dependencies()

    def _initialize_dependencies(self):
        """Initialize dependencies from the container with enhanced error handling"""
        try:
            # Initialize embedding model with error handling
            try:
                if self.container.is_bound(AbstractEmbeddingModel):
                    self.embedding_model = self.container.get(AbstractEmbeddingModel)
                    logger.info(f"Initialized embedding model via dependency injection")
                else:
                    logger.warning("No embedding model bound - embedding functionality will be limited")
                    self.embedding_model = None
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                raise EmbeddingGenerationError(f"Failed to initialize embedding model: {e}", e)
            
            # Initialize Weaviate client with error handling
            try:
                if self.container.is_bound(AbstractWeaviateClient):
                    self.weaviate_client = self.container.get(AbstractWeaviateClient)
                    logger.info("Initialized Weaviate client via dependency injection")
                else:
                    logger.warning("No Weaviate client bound - vector search functionality will be limited")
                    self.weaviate_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Weaviate client: {e}")
                raise WeaviateConnectionError(f"Failed to initialize Weaviate client: {e}", e)
            
            # Initialize OpenAI client with error handling
            try:
                if self.container.is_bound(AbstractOpenAIClient):
                    self.openai_client = self.container.get(AbstractOpenAIClient)
                    logger.info("Initialized OpenAI client via dependency injection")
                else:
                    logger.warning("No OpenAI client bound - LLM functionality will be limited")
                    self.openai_client = None
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise OpenAIAPIError(f"Failed to initialize OpenAI client: {e}", e)
                
        except Exception as e:
            logger.error(f"Failed to initialize dependencies: {e}")
            raise

    @with_retry(
        config=RetryConfig(max_attempts=3, base_delay=0.5),
        exceptions=(Exception,)
    )
    @handle_exceptions(default_return=[], log_error=True, raise_on_critical=True)
    async def get_event_embedding(self, event: QueryEvent) -> List[float]:
        """
        Generate embeddings for a query event with advanced caching
        
        Args:
            event: QueryEvent containing camera_id, timestamp, label, and bbox
            
        Returns:
            List of embedding values as floats
        """
        import time
        start_time = time.time()
        
        try:
            # Create cache key from event data (excluding timestamp for better cache hits)
            cache_key = f"embedding:{event.camera_id}:{event.label}"
            if event.bbox:
                # Round bbox values for better cache hits
                bbox_rounded = {
                    k: round(v, 1) for k, v in event.bbox.items()
                }
                cache_key += f":{bbox_rounded}"
            
            # Try to get from cache first
            if ADVANCED_CACHING_AVAILABLE:
                cache_mgr = await get_cache_manager()
                cached_embedding = await cache_mgr.get(cache_key, CacheType.EMBEDDING)
                
                if cached_embedding:
                    duration = time.time() - start_time
                    logger.debug(f"Cache hit for embedding: {cache_key}")
                    
                    # Record cache hit metrics
                    if METRICS_AVAILABLE:
                        metrics_collector.record_embedding_metrics(
                            model_type="cached",
                            content_type="event_description",
                            duration=duration
                        )
                    
                    return cached_embedding
            
            # Check if embedding model is available
            if not self.embedding_model:
                raise EmbeddingGenerationError("Embedding model not available - SentenceTransformers dependency missing")
                
            # Create text representation of the event for embedding
            event_text = f"Camera {event.camera_id} detected {event.label} at {event.timestamp}"
            if event.bbox:
                bbox_str = f"x:{event.bbox.get('x', 0):.2f} y:{event.bbox.get('y', 0):.2f} " \
                          f"w:{event.bbox.get('width', 0):.2f} h:{event.bbox.get('height', 0):.2f}"
                event_text += f" in region [{bbox_str}]"
            
            # Generate embedding with metrics timing
            embedding = self.embedding_model.encode(event_text, convert_to_tensor=False)
            embedding_list = embedding.tolist()
            
            # Cache the embedding for future use (24 hour TTL)
            if ADVANCED_CACHING_AVAILABLE:
                await cache_mgr.set(cache_key, embedding_list, CacheType.EMBEDDING, ttl=24*3600)
                logger.debug(f"Cached embedding: {cache_key}")
            
            # Record embedding metrics
            duration = time.time() - start_time
            model_type = getattr(self.embedding_model, 'model_name', 'sentence_transformer')
            if METRICS_AVAILABLE:
                metrics_collector.record_embedding_metrics(
                    model_type=model_type,
                    content_type="event_description",
                    duration=duration
                )
            
            return embedding_list
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error generating embedding for event: {e}")
            
            # Record failed embedding attempt
            if METRICS_AVAILABLE:
                metrics_collector.record_embedding_metrics(
                    model_type="unknown",
                    content_type="event_description", 
                    duration=duration
                )
            raise EmbeddingGenerationError(f"Error generating embedding for event: {e}", e)
    
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
                        wvc.config.Property(name="confidence", data_type=wvc.config.DataType.NUMBER),                    ]
                )
                logger.info("Created TemporalEvent collection in Weaviate")
        except Exception as e:
            logger.error(f"Error ensuring schema: {e}")
            raise

    @with_retry(
        config=RetryConfig(max_attempts=3, base_delay=1.0),
        exceptions=(WeaviateConnectionError,)
    )
    @handle_exceptions(default_return=[], log_error=True, raise_on_critical=True)
    def query_weaviate(self, query_event: QueryEvent, k: int = 10) -> List[Dict[str, Any]]:
        """
        Query Weaviate for top-k nearest neighbors by vector similarity with enhanced error handling and metrics
        
        Args:
            query_event: QueryEvent to search for similar events
            k: Number of nearest neighbors to retrieve
            
        Returns:
            List of similar events with metadata
        """
        import time
        start_time = time.time()
        
        try:
            # Generate embedding for query event
            query_embedding = self.get_event_embedding(query_event)
            
            # Check if Weaviate client is available
            if not self.weaviate_client:
                raise WeaviateConnectionError("Weaviate client not initialized")            # Query Weaviate with error handling and metrics timing
            with metrics_collector.time_vector_search("weaviate", "similarity", str(k)):
                try:
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
                except Exception as e:
                    logger.error(f"Weaviate query failed: {e}")
                    raise WeaviateConnectionError(f"Failed to query Weaviate: {e}", e)
                
            # Convert results to list of dictionaries
            results = []
            for obj in response.objects:
                try:
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
                except Exception as e:
                    logger.warning(f"Error processing Weaviate result object: {e}")
                    continue
            
            logger.info(f"Retrieved {len(results)} similar events from Weaviate")
            return results
            
        except WeaviateConnectionError:
            raise  # Re-raise specific errors
        except EmbeddingGenerationError:
            raise  # Re-raise specific errors
        except Exception as e:
            logger.error(f"Unexpected error querying Weaviate: {e}")
            raise WeaviateConnectionError(f"Unexpected error during Weaviate query: {e}", e)
    
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
        Construct LLM prompts emphasizing temporal flow and causality with caching
        
        Args:
            query_event: The original query event
            context_events: Retrieved context events in chronological order
            
        Returns:
            Constructed prompt for LLM
        """
        try:
            # Create cache key based on query event and context events
            context_hashes = []
            for event in context_events:
                props = event.get("properties", {})
                event_key = f"{props.get('timestamp')}:{props.get('camera_id')}:{props.get('label')}"
                context_hashes.append(event_key)
            
            cache_key = {
                "query_event": {
                    "camera_id": query_event.camera_id,
                    "timestamp": str(query_event.timestamp),
                    "label": query_event.label,
                    "bbox": query_event.bbox
                },
                "context_events": context_hashes
            }
              # Try to get from cache first
            if ADVANCED_CACHING_AVAILABLE:
                cache_mgr = await get_cache_manager()
                cached_prompt = await cache_mgr.get(cache_key, CacheType.QUERY)
                
                if cached_prompt:
                    logger.debug(f"Cache hit for temporal prompt")
                    if METRICS_AVAILABLE:
                        metrics_collector.record_cache_metrics("temporal_prompt", "get", "hit")
                    return cached_prompt
            
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
            
            prompt = prompt.strip()
              # Cache the constructed prompt (6 hour TTL for temporal prompts)
            if ADVANCED_CACHING_AVAILABLE:
                await cache_mgr.set(cache_key, prompt, CacheType.QUERY, ttl=6*3600)
                logger.debug(f"Cached temporal prompt")
                # TODO: Fix metrics call formatting
                # if METRICS_AVAILABLE:
                #     metrics_collector.record_cache_metrics("temporal_prompt", "set", "success")
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error constructing temporal prompt: {e}")
            return f"Error constructing prompt for query event at {query_event.timestamp}"
    
    @with_retry(
        config=RetryConfig(max_attempts=2, base_delay=1.0),
        exceptions=(WeaviateConnectionError, OpenAIAPIError)
    )
    @handle_exceptions(log_error=True, raise_on_critical=True)
    async def process_temporal_query(self, query_event: QueryEvent, k: int = 10) -> TemporalRAGResponse:
        """
        Process a complete temporal RAG query with enhanced error handling
        
        Args:
            query_event: Event to query for
            k: Number of similar events to retrieve
              Returns:
            TemporalRAGResponse with explanation and context
        """
        try:
            # Validate input parameters
            if not isinstance(query_event, QueryEvent):
                raise TemporalProcessingError("query_event must be a QueryEvent instance")
            
            if k <= 0 or k > 100:
                raise TemporalProcessingError("k must be between 1 and 100")
            
            # Create cache key for the entire query response
            query_cache_key = {
                "query_event": {
                    "camera_id": query_event.camera_id,
                    "timestamp": str(query_event.timestamp),
                    "label": query_event.label,
                    "bbox": query_event.bbox
                },
                "k": k,
                "operation": "temporal_query"            }
            
            # Try to get complete response from cache first
            if ADVANCED_CACHING_AVAILABLE:
                cache_mgr = await get_cache_manager()
                cached_response = await cache_mgr.get(query_cache_key, CacheType.QUERY)
                if cached_response:
                    logger.debug(f"Cache hit for complete temporal query")
                    if METRICS_AVAILABLE:
                        # TODO: Fix metrics call formatting
                        # metrics_collector.record_cache_metrics("temporal_query", "get", "hit")
                        pass
                    return cached_response
            
            # Step 1: Query Weaviate for similar events with error handling
            try:
                similar_events = self.query_weaviate(query_event, k)
            except WeaviateConnectionError as e:
                logger.error(f"Weaviate connection failed during temporal query: {e}")
                # Return fallback response with empty context
                return TemporalRAGResponse(
                    linked_explanation=f"Unable to retrieve similar events due to database connection error. Query for {query_event.label} on camera {query_event.camera_id} at {query_event.timestamp} could not be processed.",
                    retrieved_context=[],
                    explanation_confidence=0.0
                )
            except EmbeddingGenerationError as e:
                logger.error(f"Embedding generation failed during temporal query: {e}")
                return TemporalRAGResponse(
                    linked_explanation=f"Unable to process query due to embedding generation error. Query for {query_event.label} on camera {query_event.camera_id} at {query_event.timestamp} could not be analyzed.",
                    retrieved_context=[],
                    explanation_confidence=0.0
                )
            
            # Step 2: Sort by timestamp chronologically
            chronological_events = self.sort_by_timestamp(similar_events)
            
            # Step 3: Construct temporal prompt
            try:
                prompt = await self.construct_temporal_prompt(query_event, chronological_events)
            except Exception as e:
                logger.warning(f"Error constructing temporal prompt: {e}")
                prompt = f"Analyze temporal sequence for {query_event.label} detected on camera {query_event.camera_id} at {query_event.timestamp}"
            
            # Step 4: Compute overall explanation confidence
            # Calculate average similarity score across all retrieved snippets
            similarity_scores = [event.get("similarity_score", 0.0) for event in chronological_events]
            explanation_confidence = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
              # Step 5: Generate LLM explanation with caching
            explanation = ""
            if self.openai_client:
                # Create cache key for OpenAI API response
                api_cache_key = {
                    "prompt_hash": hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
                    "model": "gpt-4",
                    "max_tokens": 800,
                    "temperature": 0.3,
                    "operation": "openai_completion"
                }
                
                # Check cache for API response first
                cached_explanation = None
                if ADVANCED_CACHING_AVAILABLE:
                    cached_explanation = await cache_mgr.get(api_cache_key, CacheType.API_RESPONSE)
                    if cached_explanation:
                        explanation = cached_explanation
                        logger.debug(f"Cache hit for OpenAI API response")
                        if METRICS_AVAILABLE:
                            metrics_collector.record_cache_hit("openai_api", "memory")
                
                # If not cached, make API call
                if not explanation:
                    try:
                        start_time = time.time()
                        response = await self.openai_client.chat.completions.create(
                            model="gpt-4",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=800,
                            temperature=0.3
                        )
                        explanation = response.choices[0].message.content.strip()
                        api_duration = time.time() - start_time
                        
                        # Cache the API response (2 hour TTL for OpenAI responses)
                        if ADVANCED_CACHING_AVAILABLE:
                            await cache_mgr.set(api_cache_key, explanation, CacheType.API_RESPONSE, ttl=2*3600)
                            logger.debug(f"Cached OpenAI API response")
                            if METRICS_AVAILABLE:
                                metrics_collector.record_cache_set("openai_api", len(explanation.encode('utf-8')))
                                metrics_collector.record_external_service_metrics(
                                    service="openai",
                                    operation="completion",
                                    duration=api_duration,
                                    success=True
                                )
                        
                    except Exception as e:
                        logger.error(f"OpenAI API error during temporal query: {e}")
                        # Record API failure metrics
                        if METRICS_AVAILABLE:
                            metrics_collector.record_external_service_metrics(
                                service="openai",
                                operation="completion", 
                                duration=0,
                                success=False
                            )
                        
                        # Provide fallback explanation when OpenAI fails
                        explanation = (
                            f"Temporal analysis for {query_event.label} detected on camera {query_event.camera_id} "
                            f"at {query_event.timestamp}. Retrieved {len(chronological_events)} similar events "
                            f"in chronological order. AI-generated explanation temporarily unavailable due to "
                            f"API limitations. Please review the retrieved context events for patterns and relationships."
                        )
                        # Mark degraded service status
                        if service_status_manager:
                            service_status_manager.services['openai'].consecutive_failures += 1
            else:
                explanation = (
                    f"Temporal analysis for {query_event.label} detected on camera {query_event.camera_id} "
                    f"at {query_event.timestamp}. Retrieved {len(chronological_events)} similar events "
                    f"in chronological order. AI-powered explanation not available - OpenAI API key not configured. "
                    f"Review the chronological context events to identify patterns and relationships."
                )
            
            # Step 6: Record Prometheus metric
            rag_explanation_confidence.labels(
                camera_id=query_event.camera_id,
                label=query_event.label
            ).set(explanation_confidence)
              # Step 7: Create and cache the response
            response = TemporalRAGResponse(
                linked_explanation=explanation,
                retrieved_context=chronological_events,
                explanation_confidence=explanation_confidence
            )
            
            # Cache the complete response (30 minute TTL for complete queries)
            if ADVANCED_CACHING_AVAILABLE:
                await cache_mgr.set(query_cache_key, response, CacheType.QUERY, ttl=30*60)
                logger.debug(f"Cached complete temporal query response")
                if METRICS_AVAILABLE:
                    response_size = len(explanation.encode('utf-8')) + len(str(chronological_events).encode('utf-8'))
                    metrics_collector.record_cache_set("temporal_query", response_size)
            
            return response
            
        except TemporalProcessingError:
            raise  # Re-raise validation errors
        except Exception as e:
            logger.error(f"Unexpected error processing temporal query: {e}", exc_info=True)
            # Return fallback response for unexpected errors
            return TemporalRAGResponse(
                linked_explanation=f"System error occurred while processing temporal query for {query_event.label} on camera {query_event.camera_id}. Please try again later.",
                retrieved_context=[],
                explanation_confidence=0.0
            )

# Global instance - initialized lazily
rag_service = None

def get_rag_service(container: Optional[DependencyContainer] = None):
    """Get or create the global RAG service instance with dependency injection
    
    Args:
        container: Optional dependency container. If provided, creates a new instance.
                  If None, uses or creates the global singleton instance.
    
    Returns:
        AdvancedRAGService instance
    """
    global rag_service
    
    # If container is provided, always create a new instance
    if container is not None:
        return AdvancedRAGService(container)
    
    # Otherwise use singleton pattern
    if rag_service is None:
        rag_service = AdvancedRAGService()
    return rag_service

def create_rag_service_with_container(container: DependencyContainer) -> AdvancedRAGService:
    """Create a new RAG service instance with specific dependencies
    
    Args:
        container: Dependency injection container with configured dependencies
        
    Returns:
        New AdvancedRAGService instance with injected dependencies
    """
    return AdvancedRAGService(container)
