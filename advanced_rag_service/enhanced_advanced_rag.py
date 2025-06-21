"""
Enhanced Advanced RAG Service

This module integrates all the enhancements including:
- Configuration management
- Robust error handling with retry logic
- Performance monitoring and caching
- Circuit breaker pattern
- Comprehensive logging
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import weaviate
import weaviate.classes as wvc
from sentence_transformers import SentenceTransformer
from openai import AsyncOpenAI
from prometheus_client import Gauge, Counter, Histogram

# Import our enhancements
from config import RAGServiceConfig, config
from error_handling import (
    with_retry, handle_exceptions, EnhancedRAGError, 
    ConnectionError, ValidationError, TimeoutError,
    RetryConfig, CircuitBreaker
)
from performance import cache_result, monitor_performance, cache, performance_monitor

# Configure logging
logging.basicConfig(level=getattr(logging, config.log_level))
logger = logging.getLogger(__name__)

# Prometheus metrics
rag_explanation_confidence = Gauge(
    'rag_explanation_confidence',
    'Confidence score for RAG explanations based on vector similarity',
    ['camera_id', 'label']
)

rag_request_duration = Histogram(
    'rag_request_duration_seconds',
    'Duration of RAG requests',
    ['endpoint', 'status']
)

rag_cache_hits = Counter(
    'rag_cache_hits_total',
    'Number of cache hits',
    ['cache_type']
)

rag_errors = Counter(
    'rag_errors_total',
    'Number of errors by type',
    ['error_type', 'component']
)


@dataclass
class QueryEvent:
    """Event structure for temporal queries with validation"""
    camera_id: str
    timestamp: str  # ISO 8601 format
    label: str
    bbox: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        """Validate event data"""
        if not self.camera_id or not isinstance(self.camera_id, str):
            raise ValidationError("camera_id must be a non-empty string")
        
        if not self.timestamp or not isinstance(self.timestamp, str):
            raise ValidationError("timestamp must be a non-empty string")
        
        if not self.label or not isinstance(self.label, str):
            raise ValidationError("label must be a non-empty string")
        
        if self.bbox is not None:
            required_keys = {'x', 'y', 'width', 'height'}
            if not isinstance(self.bbox, dict) or not required_keys.issubset(self.bbox.keys()):
                raise ValidationError("bbox must contain x, y, width, height keys")


@dataclass  
class TemporalRAGResponse:
    """Response structure for temporal RAG queries with confidence"""
    linked_explanation: str
    retrieved_context: List[Dict[str, Any]]
    explanation_confidence: float
    processing_time: float = 0.0
    cache_hit: bool = False
    
    def __post_init__(self):
        """Validate response data"""
        if not isinstance(self.explanation_confidence, (int, float)):
            raise ValidationError("explanation_confidence must be a number")
        
        if not 0.0 <= self.explanation_confidence <= 1.0:
            raise ValidationError("explanation_confidence must be between 0.0 and 1.0")


class EnhancedAdvancedRAGService:
    """Enhanced Advanced RAG Service with comprehensive improvements"""
    
    def __init__(self, config: Optional[RAGServiceConfig] = None):
        """Initialize the Enhanced Advanced RAG Service"""
        self.config = config or globals()['config']
        self.embedding_model = None
        self.weaviate_client = None
        self.openai_client = None
        
        # Initialize circuit breakers
        self.weaviate_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2
        )
        
        self.openai_circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2
        )
        
        self._initialize_clients()
    
    @with_retry(
        config=RetryConfig(max_attempts=3, base_delay=1.0),
        exceptions=(Exception,)
    )
    @handle_exceptions(log_error=True, raise_on_critical=True)
    def _initialize_clients(self):
        """Initialize all required clients with retry logic"""
        try:
            # Initialize SentenceTransformer
            self.embedding_model = SentenceTransformer(self.config.embedding_model_name)
            logger.info(f"Initialized SentenceTransformer model: {self.config.embedding_model_name}")
            
            # Initialize Weaviate client
            weaviate_config = {
                "url": self.config.weaviate_url,
                "timeout_config": (self.config.weaviate_timeout, self.config.weaviate_timeout)
            }
            
            if self.config.weaviate_api_key:
                weaviate_config["auth_credentials"] = weaviate.AuthApiKey(api_key=self.config.weaviate_api_key)
            
            self.weaviate_client = weaviate.connect_to_custom(**weaviate_config)
            logger.info("Connected to Weaviate")
            
            # Initialize OpenAI client
            if self.config.openai_api_key:
                self.openai_client = AsyncOpenAI(
                    api_key=self.config.openai_api_key,
                    timeout=self.config.openai_timeout
                )
                logger.info("Initialized OpenAI client")
            else:
                logger.warning("OpenAI API key not provided - LLM functionality will be limited")
                
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            rag_errors.labels(error_type="initialization", component="client_setup").inc()
            raise ConnectionError(f"Failed to initialize RAG service clients: {e}", e)
    
    @cache_result(ttl=300, key_prefix="embedding")
    @with_retry(
        config=RetryConfig(max_attempts=2, base_delay=0.5),
        exceptions=(Exception,)
    )
    @handle_exceptions(default_return=[], log_error=True)
    def get_event_embedding(self, event: QueryEvent) -> List[float]:
        """
        Generate embeddings for a query event with caching and retry logic
        
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
            rag_errors.labels(error_type="embedding_generation", component="sentence_transformer").inc()
            raise EnhancedRAGError(f"Failed to generate embedding: {e}", "api_error", e)
    
    @with_retry(
        config=RetryConfig(max_attempts=3, base_delay=1.0),
        exceptions=(Exception,)
    )
    @handle_exceptions(log_error=True, raise_on_critical=True)
    def _ensure_temporal_event_schema(self):
        """Ensure TemporalEvent collection exists in Weaviate with retry logic"""
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
            rag_errors.labels(error_type="schema_creation", component="weaviate").inc()
            raise ConnectionError(f"Failed to ensure Weaviate schema: {e}", e)
    
    @monitor_performance("query_weaviate")
    @with_retry(
        config=RetryConfig(max_attempts=3, base_delay=1.0),
        exceptions=(Exception,)
    )
    @handle_exceptions(default_return=[], log_error=True)
    def query_weaviate(self, query_event: QueryEvent, k: int = 10) -> List[Dict[str, Any]]:
        """
        Query Weaviate for top-k nearest neighbors with enhanced error handling
        
        Args:
            query_event: QueryEvent to search for similar events
            k: Number of nearest neighbors to retrieve
            
        Returns:
            List of similar events with metadata
        """
        try:
            # Validate k parameter
            k = max(1, min(k, self.config.max_k))
            
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
                # Extract similarity score and normalize to 0-1 range
                distance = obj.metadata.distance if obj.metadata else 1.0
                similarity_score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
                
                # Filter out results below similarity threshold
                if similarity_score < self.config.similarity_threshold:
                    continue
                
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
            rag_errors.labels(error_type="query_error", component="weaviate").inc()
            raise ConnectionError(f"Failed to query Weaviate: {e}", e)
    
    @handle_exceptions(default_return=[], log_error=True)
    def sort_by_timestamp(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort retrieved results by timestamp with enhanced error handling
        
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
                        return time.time()  # Current time as fallback
                    
                    timestamp_str = properties.get("timestamp", "")
                    if not timestamp_str:
                        return time.time()
                    
                    # Handle ISO 8601 format with Z suffix
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str.replace('Z', '+00:00')
                    
                    # Parse timestamp and convert to unix timestamp for sorting
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp_str)
                    return dt.timestamp()
                    
                except (ValueError, AttributeError, TypeError) as e:
                    logger.warning(f"Invalid timestamp in event: {e}")
                    return time.time()  # Current time as fallback
            
            sorted_events = sorted(events, key=get_timestamp)
            logger.info(f"Sorted {len(sorted_events)} events chronologically")
            return sorted_events
            
        except Exception as e:
            logger.error(f"Error sorting events by timestamp: {e}")
            return events  # Return unsorted if sorting fails
    
    @cache_result(ttl=600, key_prefix="prompt")
    @handle_exceptions(log_error=True, raise_on_critical=False)
    async def construct_temporal_prompt(self, query_event: QueryEvent, context_events: List[Dict[str, Any]]) -> str:
        """
        Construct LLM prompts with enhanced context and error handling
        
        Args:
            query_event: The original query event
            context_events: Retrieved context events in chronological order
            
        Returns:
            Constructed prompt for LLM
        """
        try:
            # Build temporal context description with error handling
            temporal_context = []
            for i, event in enumerate(context_events):
                try:
                    props = event.get("properties", {})
                    if props is None:
                        continue
                        
                    timestamp = props.get("timestamp", "unknown")
                    camera_id = props.get("camera_id", "unknown")
                    label = props.get("label", "unknown")
                    confidence = props.get("confidence", 0.0)
                    similarity = event.get("similarity_score", 0.0)
                    
                    temporal_context.append(
                        f"{i+1}. [{timestamp}] Camera {camera_id}: {label} "
                        f"(confidence: {confidence:.2f}, similarity: {similarity:.2f})"
                    )
                except Exception as e:
                    logger.warning(f"Error processing context event {i}: {e}")
                    continue
            
            # Construct enhanced prompt with confidence metrics
            prompt = f"""
You are analyzing surveillance events with focus on temporal relationships and causality.

QUERY EVENT:
- Camera: {query_event.camera_id}
- Time: {query_event.timestamp}  
- Detection: {query_event.label}
- Location: {query_event.bbox if query_event.bbox else "Not specified"}

TEMPORAL CONTEXT ({len(temporal_context)} similar events, chronologically ordered):
{chr(10).join(temporal_context) if temporal_context else "No similar events found"}

ANALYSIS INSTRUCTIONS:
1. Focus on temporal sequence and flow of events
2. Identify potential causal relationships between events
3. Consider spatial proximity (same camera vs different cameras)
4. Look for patterns indicating related activities
5. Assess if the query event fits into a larger sequence
6. Consider similarity scores when interpreting relevance

Provide a detailed explanation emphasizing:
- How events relate temporally and causally
- Potential cause-and-effect relationships  
- Whether this appears part of a larger pattern
- Any anomalies or significant changes
- Confidence level based on similarity scores

Your response should help security personnel understand not just what happened, 
but how events may be connected through time and causality.
"""
            
            return prompt.strip()
            
        except Exception as e:
            logger.error(f"Error constructing temporal prompt: {e}")
            return f"Error constructing prompt for query event at {query_event.timestamp}"
    
    @monitor_performance("process_temporal_query") 
    @with_retry(
        config=RetryConfig(max_attempts=2, base_delay=1.0),
        exceptions=(ConnectionError, TimeoutError)
    )
    async def process_temporal_query(self, query_event: QueryEvent, k: int = 10) -> TemporalRAGResponse:
        """
        Process a complete temporal RAG query with comprehensive enhancements
        
        Args:
            query_event: Event to query for
            k: Number of similar events to retrieve
            
        Returns:
            TemporalRAGResponse with explanation and context
        """
        start_time = time.time()
        cache_hit = False
        
        try:
            # Validate input
            if not isinstance(query_event, QueryEvent):
                raise ValidationError("query_event must be a QueryEvent instance")
            
            # Check cache first
            cache_key = f"temporal_query:{query_event.camera_id}:{query_event.timestamp}:{query_event.label}:{k}"
            cached_result = await cache.get(cache_key)
            if cached_result:
                cache_hit = True
                rag_cache_hits.labels(cache_type="temporal_query").inc()
                await performance_monitor.record_cache_hit()
                logger.info("Returning cached temporal query result")
                cached_result.cache_hit = True
                return cached_result
            
            await performance_monitor.record_cache_miss()
            
            # Step 1: Query Weaviate for similar events
            similar_events = self.query_weaviate(query_event, k)
            
            # Step 2: Sort by timestamp chronologically
            chronological_events = self.sort_by_timestamp(similar_events)
            
            # Step 3: Construct temporal prompt
            prompt = await self.construct_temporal_prompt(query_event, chronological_events)
            
            # Step 4: Compute overall explanation confidence
            similarity_scores = [event.get("similarity_score", 0.0) for event in chronological_events]
            explanation_confidence = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
            
            # Step 5: Generate LLM explanation with circuit breaker
            explanation = "LLM explanation unavailable"
            if self.openai_client and self.openai_circuit_breaker.state != "OPEN":
                try:
                    response = await self.openai_client.chat.completions.create(
                        model=self.config.openai_model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=self.config.openai_max_tokens,
                        temperature=self.config.openai_temperature
                    )
                    explanation = response.choices[0].message.content.strip()
                    
                    # Update circuit breaker on success
                    if self.openai_circuit_breaker.state == "HALF_OPEN":
                        self.openai_circuit_breaker.state = "CLOSED"
                        
                except Exception as e:
                    logger.error(f"Error generating LLM explanation: {e}")
                    rag_errors.labels(error_type="llm_generation", component="openai").inc()
                    
                    # Update circuit breaker on failure
                    self.openai_circuit_breaker.failure_count += 1
                    if self.openai_circuit_breaker.failure_count >= self.openai_circuit_breaker.failure_threshold:
                        self.openai_circuit_breaker.state = "OPEN"
                        self.openai_circuit_breaker.last_failure_time = time.time()
                    
                    explanation = "LLM explanation unavailable due to API error"
            
            # Step 6: Record Prometheus metric
            rag_explanation_confidence.labels(
                camera_id=query_event.camera_id,
                label=query_event.label
            ).set(explanation_confidence)
            
            # Step 7: Create and cache response
            processing_time = time.time() - start_time
            response = TemporalRAGResponse(
                linked_explanation=explanation,
                retrieved_context=chronological_events,
                explanation_confidence=explanation_confidence,
                processing_time=processing_time,
                cache_hit=cache_hit
            )
            
            # Cache the response
            await cache.set(cache_key, response, ttl=self.config.cache_ttl_seconds)
            
            # Record performance metrics
            await performance_monitor.record_request("process_temporal_query", processing_time, True)
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            await performance_monitor.record_request("process_temporal_query", processing_time, False)
            logger.error(f"Error processing temporal query: {e}")
            rag_errors.labels(error_type="processing_error", component="temporal_query").inc()
            raise


# Enhanced global instance with configuration
enhanced_rag_service = EnhancedAdvancedRAGService(config)
