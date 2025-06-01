"""
Weaviate client for semantic retrieval of CameraEvent objects for the Prompt Service.
"""
import os
import weaviate
from weaviate import AuthApiKey

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=AuthApiKey(api_key=WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None,
)

def semantic_search(query: str, limit: int = 5) -> list[dict]:
    """
    Perform a nearText semantic search in Weaviate for CameraEvent context.
    Returns a list of result dicts with event properties.
    """
    response = (
        client.query
        .get("CameraEvent", ["event_id", "timestamp", "camera_id"])
        .with_near_text({"concepts": [query]})
        .with_limit(limit)
        .with_additional(["certainty"])
        .do()
    )
    return response.get("data", {}).get("Get", {}).get("CameraEvent", [])