"""
Enhanced Weaviate client for semantic retrieval with advanced features.
"""
import os
import weaviate
import weaviate.classes as wvc
from typing import List, Dict, Any, Optional

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

client = weaviate.connect_to_local(
    host="weaviate",
    port=8080
)

def semantic_search(
    query: str, 
    limit: int = 5, 
    conversation_context: Optional[List[Dict[str, str]]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Perform enhanced semantic search in Weaviate for CameraEvent context.
    
    Args:
        query: Search query
        limit: Maximum number of results
        conversation_context: Previous conversation messages for context
        filters: Additional filters (camera_id, event_type, time_range, etc.)
    
    Returns:
        List of result dicts with event properties and enhanced metadata
    """
    try:
        collection = client.collections.get("CameraEvent")
        
        # Build enhanced query considering conversation context
        enhanced_query = _build_enhanced_query(query, conversation_context)
        
        # Build where filter if filters provided
        where_filter = _build_where_filter(filters) if filters else None
        
        # Perform search
        if where_filter:
            response = collection.query.near_text(
                query=enhanced_query,
                limit=limit,
                where=where_filter,
                return_metadata=wvc.query.MetadataQuery(certainty=True, distance=True)
            )
        else:
            response = collection.query.near_text(
                query=enhanced_query,
                limit=limit,
                return_metadata=wvc.query.MetadataQuery(certainty=True, distance=True)
            )
        
        # Process results with enhanced metadata
        results = []
        for obj in response.objects:
            result = {
                "event_id": obj.properties.get("event_id"),
                "timestamp": obj.properties.get("timestamp"),
                "camera_id": obj.properties.get("camera_id"),
                "event_type": obj.properties.get("event_type"),
                "details": obj.properties.get("details", ""),
                "location": obj.properties.get("location", ""),
                "confidence": obj.properties.get("confidence", 0.0),
                
                # Enhanced metadata
                "certainty": obj.metadata.certainty if obj.metadata else None,
                "distance": obj.metadata.distance if obj.metadata else None,
                "relevance_score": _calculate_relevance_score(obj, query, conversation_context),
                "context_match": _assess_context_match(obj, conversation_context),
                
                # Additional context fields
                "detection_labels": obj.properties.get("detection_labels", []),
                "anomaly_score": obj.properties.get("anomaly_score", 0.0),
                "priority": obj.properties.get("priority", "low"),
                "related_events": obj.properties.get("related_events", [])
            }
            results.append(result)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return results
        
    except Exception as e:
        print(f"Enhanced Weaviate search error: {e}")
        return []

def semantic_search_with_patterns(
    query: str,
    limit: int = 5,
    include_patterns: bool = True,
    time_window_hours: int = 24
) -> Dict[str, Any]:
    """
    Semantic search with pattern analysis and temporal context.
    
    Returns:
        Dict with search results and detected patterns
    """
    try:
        # Get standard search results
        search_results = semantic_search(query, limit)
        
        result = {
            "results": search_results,
            "patterns": {},
            "temporal_analysis": {},
            "recommendations": []
        }
        
        if include_patterns and search_results:
            # Analyze patterns in results
            result["patterns"] = _analyze_event_patterns(search_results)
            result["temporal_analysis"] = _analyze_temporal_patterns(search_results, time_window_hours)
            result["recommendations"] = _generate_search_recommendations(search_results, query)
        
        return result
        
    except Exception as e:
        print(f"Pattern search error: {e}")
        return {"results": [], "patterns": {}, "temporal_analysis": {}, "recommendations": []}

def get_related_events(
    event_id: str, 
    relation_types: List[str] = ["temporal", "spatial", "semantic"],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Find events related to a given event by various relationships.
    
    Args:
        event_id: Reference event ID
        relation_types: Types of relationships to consider
        limit: Maximum number of related events
    
    Returns:
        List of related events with relationship metadata
    """
    try:
        # First get the reference event
        collection = client.collections.get("CameraEvent")
        ref_response = collection.query.fetch_objects(
            where=wvc.query.Filter.by_property("event_id").equal(event_id),
            limit=1
        )
        
        if not ref_response.objects:
            return []
        
        ref_event = ref_response.objects[0]
        related_events = []
        
        # Find temporally related events
        if "temporal" in relation_types:
            temporal_related = _find_temporal_related(ref_event, collection, limit // len(relation_types))
            related_events.extend(temporal_related)
        
        # Find spatially related events (same camera or nearby)
        if "spatial" in relation_types:
            spatial_related = _find_spatial_related(ref_event, collection, limit // len(relation_types))
            related_events.extend(spatial_related)
        
        # Find semantically related events
        if "semantic" in relation_types:
            semantic_related = _find_semantic_related(ref_event, collection, limit // len(relation_types))
            related_events.extend(semantic_related)
        
        # Remove duplicates and sort by relevance
        unique_events = {}
        for event in related_events:
            event_id = event.get("event_id")
            if event_id and event_id not in unique_events:
                unique_events[event_id] = event
        
        result = list(unique_events.values())
        result.sort(key=lambda x: x.get("relationship_strength", 0), reverse=True)
        
        return result[:limit]
        
    except Exception as e:
        print(f"Related events search error: {e}")
        return []

# Helper functions

def _build_enhanced_query(query: str, conversation_context: Optional[List[Dict[str, str]]]) -> str:
    """Build enhanced query incorporating conversation context."""
    if not conversation_context:
        return query
    
    # Extract relevant context from recent conversation
    context_terms = []
    for msg in conversation_context[-3:]:  # Last 3 messages
        if msg.get("role") == "user":
            content = msg.get("content", "")
            # Extract key terms (simple approach)
            words = content.lower().split()
            context_terms.extend([w for w in words if len(w) > 3])
    
    if context_terms:
        # Add most relevant context terms to query
        unique_terms = list(set(context_terms))[:3]
        enhanced_query = f"{query} {' '.join(unique_terms)}"
        return enhanced_query
    
    return query

def _build_where_filter(filters: Dict[str, Any]) -> wvc.query.Filter:
    """Build Weaviate where filter from filter dict."""
    filter_conditions = []
    
    if "camera_id" in filters:
        filter_conditions.append(
            wvc.query.Filter.by_property("camera_id").equal(filters["camera_id"])
        )
    
    if "event_type" in filters:
        filter_conditions.append(
            wvc.query.Filter.by_property("event_type").equal(filters["event_type"])
        )
    
    if "min_confidence" in filters:
        filter_conditions.append(
            wvc.query.Filter.by_property("confidence").greater_or_equal(filters["min_confidence"])
        )
    
    if "time_range" in filters:
        time_range = filters["time_range"]
        if "start" in time_range:
            filter_conditions.append(
                wvc.query.Filter.by_property("timestamp").greater_or_equal(time_range["start"])
            )
        if "end" in time_range:
            filter_conditions.append(
                wvc.query.Filter.by_property("timestamp").less_or_equal(time_range["end"])
            )
    
    # Combine conditions with AND
    if len(filter_conditions) == 1:
        return filter_conditions[0]
    elif len(filter_conditions) > 1:
        result = filter_conditions[0]
        for condition in filter_conditions[1:]:
            result = result & condition
        return result
    
    return None

def _calculate_relevance_score(
    obj: Any, 
    query: str, 
    conversation_context: Optional[List[Dict[str, str]]]
) -> float:
    """Calculate enhanced relevance score for a search result."""
    base_score = obj.metadata.certainty if obj.metadata else 0.5
    
    # Boost for exact query matches in details
    details = obj.properties.get("details", "").lower()
    query_lower = query.lower()
    if query_lower in details:
        base_score += 0.1
    
    # Boost for high confidence events
    confidence = obj.properties.get("confidence", 0.0)
    if confidence > 0.8:
        base_score += 0.05
    
    # Boost for recent events
    timestamp = obj.properties.get("timestamp", "")
    if timestamp:
        # Simple recency boost (would need proper date parsing in production)
        base_score += 0.02
    
    # Context relevance boost
    if conversation_context:
        context_score = _assess_context_match(obj, conversation_context)
        base_score += context_score * 0.1
    
    return min(base_score, 1.0)

def _assess_context_match(
    obj: Any, 
    conversation_context: Optional[List[Dict[str, str]]]
) -> float:
    """Assess how well the result matches conversation context."""
    if not conversation_context:
        return 0.0
    
    # Extract context from recent user messages
    context_text = ""
    for msg in conversation_context[-3:]:
        if msg.get("role") == "user":
            context_text += " " + msg.get("content", "")
    
    if not context_text:
        return 0.0
    
    # Simple keyword matching (would use more sophisticated methods in production)
    details = obj.properties.get("details", "").lower()
    event_type = obj.properties.get("event_type", "").lower()
    camera_id = obj.properties.get("camera_id", "").lower()
    
    search_text = f"{details} {event_type} {camera_id}"
    context_words = set(context_text.lower().split())
    search_words = set(search_text.split())
    
    if not context_words or not search_words:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(context_words.intersection(search_words))
    union = len(context_words.union(search_words))
    
    return intersection / union if union > 0 else 0.0

def _analyze_event_patterns(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze patterns in search results."""
    if not results:
        return {}
    
    patterns = {
        "most_common_cameras": {},
        "most_common_types": {},
        "confidence_distribution": {},
        "time_patterns": []
    }
    
    # Analyze camera frequency
    for result in results:
        camera_id = result.get("camera_id", "unknown")
        patterns["most_common_cameras"][camera_id] = patterns["most_common_cameras"].get(camera_id, 0) + 1
    
    # Analyze event type frequency
    for result in results:
        event_type = result.get("event_type", "unknown")
        patterns["most_common_types"][event_type] = patterns["most_common_types"].get(event_type, 0) + 1
    
    # Analyze confidence distribution
    confidences = [r.get("confidence", 0.0) for r in results]
    if confidences:
        patterns["confidence_distribution"] = {
            "average": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "high_confidence_count": len([c for c in confidences if c > 0.8])
        }
    
    return patterns

def _analyze_temporal_patterns(results: List[Dict[str, Any]], time_window_hours: int) -> Dict[str, Any]:
    """Analyze temporal patterns in search results."""
    # Simple temporal analysis - would be more sophisticated in production
    return {
        "events_in_window": len(results),
        "time_window_hours": time_window_hours,
        "analysis": "Basic temporal pattern analysis"
    }

def _generate_search_recommendations(results: List[Dict[str, Any]], query: str) -> List[str]:
    """Generate search recommendations based on results."""
    recommendations = []
    
    if not results:
        recommendations.append("Try broadening your search terms")
        recommendations.append("Check if the time range is appropriate")
        return recommendations
    
    # Analyze result patterns to suggest refinements
    cameras = set(r.get("camera_id") for r in results if r.get("camera_id"))
    event_types = set(r.get("event_type") for r in results if r.get("event_type"))
    
    if len(cameras) > 1:
        most_common_camera = max(cameras, key=lambda c: sum(1 for r in results if r.get("camera_id") == c))
        recommendations.append(f"Focus on camera {most_common_camera} for more specific results")
    
    if len(event_types) > 1:
        most_common_type = max(event_types, key=lambda t: sum(1 for r in results if r.get("event_type") == t))
        recommendations.append(f"Filter by event type '{most_common_type}' for related events")
    
    return recommendations

def _find_temporal_related(ref_event: Any, collection: Any, limit: int) -> List[Dict[str, Any]]:
    """Find temporally related events."""
    # Simplified temporal search - would use proper timestamp queries in production
    related = []
    
    try:
        response = collection.query.fetch_objects(
            where=wvc.query.Filter.by_property("camera_id").equal(
                ref_event.properties.get("camera_id", "")
            ),
            limit=limit
        )
        
        for obj in response.objects:
            if obj.properties.get("event_id") != ref_event.properties.get("event_id"):
                related.append({
                    "event_id": obj.properties.get("event_id"),
                    "timestamp": obj.properties.get("timestamp"),
                    "camera_id": obj.properties.get("camera_id"),
                    "event_type": obj.properties.get("event_type"),
                    "relationship_type": "temporal",
                    "relationship_strength": 0.8  # Would calculate based on time proximity
                })
    
    except Exception as e:
        print(f"Temporal search error: {e}")
    
    return related

def _find_spatial_related(ref_event: Any, collection: Any, limit: int) -> List[Dict[str, Any]]:
    """Find spatially related events."""
    # Similar to temporal but for spatial relationships
    return []  # Simplified for now

def _find_semantic_related(ref_event: Any, collection: Any, limit: int) -> List[Dict[str, Any]]:
    """Find semantically related events."""
    related = []
    
    try:
        # Use the event details for semantic search
        details = ref_event.properties.get("details", "")
        if details:
            response = collection.query.near_text(
                query=details,
                limit=limit,
                return_metadata=wvc.query.MetadataQuery(certainty=True)
            )
            
            for obj in response.objects:
                if obj.properties.get("event_id") != ref_event.properties.get("event_id"):
                    related.append({
                        "event_id": obj.properties.get("event_id"),
                        "timestamp": obj.properties.get("timestamp"),
                        "camera_id": obj.properties.get("camera_id"),
                        "event_type": obj.properties.get("event_type"),
                        "relationship_type": "semantic",
                        "relationship_strength": obj.metadata.certainty if obj.metadata else 0.5
                    })
    
    except Exception as e:
        print(f"Semantic search error: {e}")
    
    return related
