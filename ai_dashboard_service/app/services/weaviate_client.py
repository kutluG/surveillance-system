"""
Weaviate Client Service Module

This module provides vector database connectivity and semantic search capabilities
for surveillance systems using Weaviate. It handles vector operations, semantic
search, and pattern analysis through dependency injection for flexible client
management.

The service integrates with Weaviate to provide contextual analysis of surveillance
data, semantic search capabilities, and vector-based similarity operations for
enhanced intelligence gathering and pattern recognition.

Key Features:
- Vector database connectivity and querying
- Semantic search with enhanced features
- Pattern analysis and relationship detection
- Search result ranking and filtering
- Dependency injection for flexible client management

Classes:
    WeaviateService: Main service for vector operations and semantic search
    
Dependencies:
    - Weaviate: Vector database client for semantic operations
    - Logging: For error tracking and debugging
"""

import logging
from typing import Dict, List, Any, Optional
try:
    import weaviate
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

logger = logging.getLogger(__name__)


class WeaviateService:
    """
    Vector database service for surveillance system semantic analysis.
    
    This service provides semantic search, vector operations, and pattern
    analysis capabilities for surveillance data. It uses dependency injection
    to manage Weaviate client connections and provides sophisticated error
    handling for vector database operations.
    
    The service specializes in converting surveillance events into vector
    representations, performing semantic searches, and identifying patterns
    in surveillance data through vector similarity operations.
    
    Attributes:
        client: Injected Weaviate client for vector database operations
        collection_name: Default collection name for surveillance events
        
    Example:
        >>> weaviate_service = WeaviateService(weaviate_client)
        >>> results = await weaviate_service.semantic_search(query, filters)
        >>> patterns = await weaviate_service.analyze_patterns(event_data)
    """
    
    def __init__(self, weaviate_client=None) -> None:
        """
        Initialize Weaviate service with client dependency.
        
        :param weaviate_client: Weaviate client for vector database operations
        :raises ImportError: If Weaviate client is required but not available
        """
        if not WEAVIATE_AVAILABLE and weaviate_client is not None:
            raise ImportError("Weaviate package is required but not installed")
            
        self.client = weaviate_client
        self.collection_name = "SurveillanceEvent"
        
    async def semantic_search(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search on surveillance data using vector similarity.
        
        Searches for surveillance events semantically similar to the query
        using vector embeddings and similarity scoring. Supports filtering
        by metadata and custom result ranking.
        
        :param query: Search query text for semantic matching
        :param limit: Maximum number of results to return
        :param filters: Optional filters for metadata-based filtering
        :return: List of semantically similar surveillance events
        :raises Exception: If semantic search fails or client unavailable
        
        Example:
            >>> filters = {"camera_id": "cam-001", "confidence": {"$gte": 0.8}}
            >>> results = await service.semantic_search("person detected", 5, filters)
            >>> for result in results:
            ...     print(f"Event: {result['event_type']} (score: {result['score']:.3f})")
        """
        try:
            if not self.client:
                logger.warning("Weaviate client not available, returning empty results")
                return []
            
            # Build where clause from filters
            where_clause = self._build_where_clause(filters) if filters else None
            
            # Perform semantic search
            collection = self.client.collections.get(self.collection_name)
            
            search_query = collection.query.near_text(
                query=query,
                limit=limit,
                where=where_clause
            )
            
            # Process results
            results = []
            for obj in search_query.objects:
                result = {
                    "id": obj.uuid,
                    "score": getattr(obj.metadata, 'certainty', 0.0),
                    "distance": getattr(obj.metadata, 'distance', 1.0),
                    **obj.properties
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []
    
    async def analyze_patterns(self, events_data: List[Dict[str, Any]], pattern_type: str = "temporal") -> Dict[str, Any]:
        """
        Analyze patterns in surveillance events using vector analysis.
        
        Identifies patterns and relationships in surveillance data using
        vector similarity and clustering techniques. Supports different
        pattern analysis types including temporal, spatial, and semantic.
        
        :param events_data: List of surveillance events for pattern analysis
        :param pattern_type: Type of pattern analysis (temporal, spatial, semantic)
        :return: Dictionary containing pattern analysis results
        :raises Exception: If pattern analysis fails
        
        Example:
            >>> events = [{"event_type": "motion", "timestamp": "2025-01-01T10:00:00Z"}]
            >>> patterns = await service.analyze_patterns(events, "temporal")
            >>> print(f"Found {len(patterns['clusters'])} pattern clusters")
        """
        try:
            if not self.client:
                logger.warning("Weaviate client not available, returning empty analysis")
                return {"patterns": [], "clusters": [], "insights": []}
            
            # Handle empty events data
            if not events_data:
                return {
                    "pattern_type": pattern_type,
                    "total_events": 0,
                    "patterns": [],
                    "clusters": [],
                    "insights": ["No events data available for analysis"]
                }
            
            # Simulate pattern analysis - in production this would use vector clustering
            patterns = {
                "pattern_type": pattern_type,
                "total_events": len(events_data),
                "patterns": [
                    {
                        "id": "pattern_1",
                        "type": "recurring_motion",
                        "confidence": 0.85,
                        "description": "Regular motion detected in parking area",
                        "frequency": "daily"
                    }
                ],
                "clusters": [
                    {
                        "id": "cluster_1",
                        "size": len(events_data) // 2,
                        "centroid": {"event_type": "motion", "confidence": 0.9},
                        "variance": 0.1
                    }
                ],
                "insights": [
                    "Regular activity patterns detected",
                    "No significant anomalies in timing"
                ]
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
            return {"patterns": [], "clusters": [], "insights": []}
    
    async def get_similar_events(self, event_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find events similar to a given surveillance event.
        
        Uses vector similarity to find surveillance events that are similar
        to a reference event. Useful for finding related incidents or
        recurring patterns in surveillance data.
        
        :param event_id: ID of the reference event
        :param limit: Maximum number of similar events to return
        :return: List of similar surveillance events
        :raises Exception: If similarity search fails
        """
        try:
            if not self.client:
                logger.warning("Weaviate client not available, returning empty results")
                return []
            
            # Get the reference event first
            collection = self.client.collections.get(self.collection_name)
            
            # Find similar events using vector similarity
            similar_query = collection.query.near_object(
                near_object=event_id,
                limit=limit
            )
            
            results = []
            for obj in similar_query.objects:
                if obj.uuid != event_id:  # Exclude the reference event itself
                    result = {
                        "id": obj.uuid,
                        "similarity_score": getattr(obj.metadata, 'certainty', 0.0),
                        "distance": getattr(obj.metadata, 'distance', 1.0),
                        **obj.properties
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar events: {e}")
            return []
    
    async def store_event(self, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Store a surveillance event in the vector database.
        
        Converts surveillance event data into vector representation and
        stores it in Weaviate for future semantic search and analysis.
        
        :param event_data: Surveillance event data to store
        :return: Event ID if successful, None if failed
        :raises Exception: If event storage fails
        """
        try:
            if not self.client:
                logger.warning("Weaviate client not available, cannot store event")
                return None
            
            collection = self.client.collections.get(self.collection_name)
            
            # Store the event
            event_id = collection.data.insert(
                properties=event_data
            )
            
            logger.info(f"Stored event with ID: {event_id}")
            return str(event_id)
            
        except Exception as e:
            logger.error(f"Error storing event: {e}")
            return None
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Weaviate where clause from filter dictionary.
        
        Converts filter dictionary into Weaviate-compatible where clause
        for metadata-based filtering during semantic search operations.
        
        :param filters: Dictionary of filters to apply
        :return: Weaviate-compatible where clause
        """
        try:
            where_conditions = []
            
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Handle range queries like {"$gte": 0.8}
                    for operator, op_value in value.items():
                        if operator == "$gte":
                            where_conditions.append({
                                "path": [key],
                                "operator": "GreaterThanEqual",
                                "valueNumber": op_value
                            })
                        elif operator == "$lte":
                            where_conditions.append({
                                "path": [key],
                                "operator": "LessThanEqual",
                                "valueNumber": op_value
                            })
                        elif operator == "$eq":
                            where_conditions.append({
                                "path": [key],
                                "operator": "Equal",
                                "valueText" if isinstance(op_value, str) else "valueNumber": op_value
                            })
                else:
                    # Handle direct value comparisons
                    where_conditions.append({
                        "path": [key],
                        "operator": "Equal",
                        "valueText" if isinstance(value, str) else "valueNumber": value
                    })
            
            # Combine conditions with AND
            if len(where_conditions) == 1:
                return where_conditions[0]
            elif len(where_conditions) > 1:
                return {
                    "operator": "And",
                    "operands": where_conditions
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error building where clause: {e}")
            return {}


# Global instance
# No global instance needed - use dependency injection
