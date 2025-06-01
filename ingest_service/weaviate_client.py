"""
Weaviate client initialization and schema management.
"""
import os
import ingest_service.weaviate_client as weaviate_client
from ingest_service.weaviate_client import AuthApiKey

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

# Create the client with optional API key auth
client = weaviate_client.Client(
    url=WEAVIATE_URL,
    auth_client_secret=AuthApiKey(api_key=WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None,
    additional_headers={"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")},
)

def init_schema():
    """
    Ensure the CameraEvent class exists in Weaviate schema.
    """
    schema = client.schema.get()
    classes = [c["class"] for c in schema.get("classes", [])]
    if "CameraEvent" not in classes:
        class_obj = {
            "class": "CameraEvent",
            "properties": [
                {"name": "event_id", "dataType": ["string"]},
                {"name": "timestamp", "dataType": ["date"]},
                {"name": "camera_id", "dataType": ["string"]},
                {"name": "event_type", "dataType": ["string"]},
            ],
        }
        client.schema.create_class(class_obj)