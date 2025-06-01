"""
Weaviate client for similarity search of CameraEvent objects.
"""
import os
import weaviate
import weaviate.classes as wvc

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

client = weaviate.connect_to_local(
    host="weaviate",
    port=8080
)

def semantic_search(query: str, limit: int = 5) -> list[dict]:
    """
    Perform a nearText semantic search in Weaviate for CameraEvent context.
    Returns a list of result dicts with event properties and score.
    """
    try:
        collection = client.collections.get("CameraEvent")
        response = collection.query.near_text(
            query=query,
            limit=limit,
            return_metadata=wvc.query.MetadataQuery(certainty=True)
        )
        return [
            {
                "event_id": obj.properties.get("event_id"),
                "timestamp": obj.properties.get("timestamp"),
                "camera_id": obj.properties.get("camera_id"),
                "event_type": obj.properties.get("event_type"),
                "certainty": obj.metadata.certainty if obj.metadata else None
            }
            for obj in response.objects
        ]
    except Exception as e:
        print(f"Weaviate search error: {e}")
        return []