"""
Weaviate client initialization and schema management.
"""
import os
import weaviate
from weaviate import AuthApiKey

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

# Create the client with optional API key auth
client = weaviate.connect_to_custom(
    http_host="weaviate",
    http_port=8080,
    http_secure=False,
    grpc_host="weaviate",
    grpc_port=50051,
    grpc_secure=False,
    auth_credentials=AuthApiKey(api_key=WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None,
    headers={"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")},
)

def init_schema():
    """
    Ensure the CameraEvent class exists in Weaviate schema.
    """
    try:
        # Check if the collection exists
        collections = client.collections.list_all()
        if "CameraEvent" not in [c.name for c in collections]:
            # Create the collection using the new v4 API
            client.collections.create(
                name="CameraEvent",
                properties=[
                    weaviate.classes.config.Property(name="event_id", data_type=weaviate.classes.config.DataType.TEXT),
                    weaviate.classes.config.Property(name="timestamp", data_type=weaviate.classes.config.DataType.DATE),
                    weaviate.classes.config.Property(name="camera_id", data_type=weaviate.classes.config.DataType.TEXT),
                    weaviate.classes.config.Property(name="event_type", data_type=weaviate.classes.config.DataType.TEXT),
                ],
            )
    except Exception as e:
        print(f"Error initializing schema: {e}")
        # Fallback for compatibility
        pass