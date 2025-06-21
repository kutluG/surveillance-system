"""
Dependency Injection Framework for Advanced RAG Service

This module provides dependency injection capabilities to decouple service
initialization from external dependencies, enabling better testability and
configurability.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Protocol definitions for dependency interfaces
class EmbeddingModelProtocol(Protocol):
    """Protocol for embedding model implementations"""
    
    def encode(self, text: str, convert_to_tensor: bool = False) -> List[float]:
        """Encode text to embeddings"""
        ...

class WeaviateClientProtocol(Protocol):
    """Protocol for Weaviate client implementations"""
    
    @property
    def collections(self):
        """Access to collections"""
        ...

class OpenAIClientProtocol(Protocol):
    """Protocol for OpenAI client implementations"""
    
    @property
    def chat(self):
        """Access to chat completions"""
        ...

# Abstract base classes for dependency implementations
class AbstractEmbeddingModel(ABC):
    """Abstract base class for embedding models"""
    
    @abstractmethod
    def encode(self, text: str, convert_to_tensor: bool = False) -> List[float]:
        """Encode text to embeddings"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if embedding model is available"""
        pass

class AbstractWeaviateClient(ABC):
    """Abstract base class for Weaviate clients"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to Weaviate"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to Weaviate"""
        pass
    
    @abstractmethod
    def query_similar_events(self, query_embedding: List[float], k: int = 10) -> List[Dict[str, Any]]:
        """Query for similar events"""
        pass

class AbstractOpenAIClient(ABC):
    """Abstract base class for OpenAI clients"""
    
    @abstractmethod
    async def generate_explanation(self, prompt: str, max_tokens: int = 800) -> str:
        """Generate explanation using LLM"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if OpenAI client is available"""
        pass

# Dependency registry
T = TypeVar('T')

@dataclass
class DependencyBinding(Generic[T]):
    """Represents a dependency binding"""
    interface: type
    implementation: type
    instance: Optional[T] = None
    singleton: bool = True
    factory_func: Optional[callable] = None
    initialization_params: Dict[str, Any] = field(default_factory=dict)

class DependencyContainer:
    """Dependency injection container"""
    
    def __init__(self):
        self._bindings: Dict[type, DependencyBinding] = {}
        self._instances: Dict[type, Any] = {}
        
    def bind(self, 
             interface: type, 
             implementation: type, 
             singleton: bool = True,
             factory_func: Optional[callable] = None,
             **kwargs) -> 'DependencyContainer':
        """Bind an interface to an implementation"""
        binding = DependencyBinding(
            interface=interface,
            implementation=implementation,
            singleton=singleton,
            factory_func=factory_func,
            initialization_params=kwargs
        )
        self._bindings[interface] = binding
        return self
    
    def bind_instance(self, interface: type, instance: Any) -> 'DependencyContainer':
        """Bind an interface to a specific instance"""
        binding = DependencyBinding(
            interface=interface,
            implementation=type(instance),
            instance=instance,
            singleton=True
        )
        self._bindings[interface] = binding
        self._instances[interface] = instance
        return self
    
    def get(self, interface: type) -> Any:
        """Get an instance of the specified interface"""
        if interface not in self._bindings:
            raise ValueError(f"No binding found for interface {interface}")
        
        binding = self._bindings[interface]
        
        # Return existing instance if singleton
        if binding.singleton and interface in self._instances:
            return self._instances[interface]
        
        # Use provided instance
        if binding.instance is not None:
            if binding.singleton:
                self._instances[interface] = binding.instance
            return binding.instance
        
        # Use factory function
        if binding.factory_func:
            instance = binding.factory_func(**binding.initialization_params)
        else:
            # Create new instance
            instance = binding.implementation(**binding.initialization_params)
        
        # Store singleton instance
        if binding.singleton:
            self._instances[interface] = instance
            
        return instance
    
    def is_bound(self, interface: type) -> bool:
        """Check if an interface is bound"""
        return interface in self._bindings
    
    def clear(self):
        """Clear all bindings and instances"""
        self._bindings.clear()
        self._instances.clear()

# Mock implementations for testing
class MockEmbeddingModel(AbstractEmbeddingModel):
    """Mock embedding model for testing"""
    
    def __init__(self, available: bool = True, embedding_size: int = 384):
        self.available = available
        self.embedding_size = embedding_size
        
    def encode(self, text: str, convert_to_tensor: bool = False) -> List[float]:
        if not self.available:
            raise Exception("Mock embedding model unavailable")
        # Return deterministic mock embeddings based on text hash
        import hashlib
        text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        return [(text_hash + i) / 1000000.0 for i in range(self.embedding_size)]
    
    def is_available(self) -> bool:
        return self.available

class MockWeaviateClient(AbstractWeaviateClient):
    """Mock Weaviate client for testing"""
    
    def __init__(self, connected: bool = True):
        self.connected = connected
        self.mock_data: List[Dict[str, Any]] = []
        
    def connect(self) -> bool:
        if not self.connected:
            raise Exception("Mock Weaviate connection failed")
        return True
    
    def is_connected(self) -> bool:
        return self.connected
    
    def query_similar_events(self, query_embedding: List[float], k: int = 10) -> List[Dict[str, Any]]:
        if not self.connected:
            raise Exception("Mock Weaviate not connected")
        
        # Return mock similar events
        return [
            {
                "id": f"mock_event_{i}",
                "properties": {
                    "camera_id": f"cam_{i % 3 + 1:03d}",
                    "timestamp": f"2025-06-13T10:{30 + i}:00Z",
                    "label": ["person_detected", "vehicle_detected", "motion_detected"][i % 3],
                    "confidence": 0.8 + (i % 3) * 0.05
                },
                "similarity_score": 0.9 - (i * 0.1),
                "distance": i * 0.1
            }
            for i in range(min(k, 5))  # Return up to 5 mock events
        ]
    
    def add_mock_event(self, event_data: Dict[str, Any]):
        """Add mock event data for testing"""
        self.mock_data.append(event_data)

class MockOpenAIClient(AbstractOpenAIClient):
    """Mock OpenAI client for testing"""
    
    def __init__(self, available: bool = True, response_template: str = None):
        self.available = available
        self.response_template = response_template or (
            "Mock temporal analysis for {query}. "
            "This is a test response from the mock OpenAI client. "
            "Retrieved events show temporal patterns consistent with surveillance data."
        )
        
    async def generate_explanation(self, prompt: str, max_tokens: int = 800) -> str:
        if not self.available:
            raise Exception("Mock OpenAI client unavailable")
        
        # Extract query information from prompt for more realistic responses
        query_info = "surveillance event"
        if "Camera" in prompt and "detected" in prompt:
            import re
            match = re.search(r'Camera (\w+).*detected (\w+)', prompt)
            if match:
                camera_id, label = match.groups()
                query_info = f"{label} on {camera_id}"
        
        return self.response_template.format(query=query_info)
    
    def is_available(self) -> bool:
        return self.available

# Pre-configured dependency configurations
class DependencyConfiguration:
    """Factory for common dependency configurations"""
    
    @staticmethod
    def create_production_container() -> DependencyContainer:
        """Create container with production dependencies"""
        # Import here to avoid circular imports
        try:
            from config import get_config
            config = get_config()
        except ImportError:
            # Fallback to environment variables if config system unavailable
            import os
            config = None
        
        from advanced_rag import SENTENCE_TRANSFORMERS_AVAILABLE, SentenceTransformer
        import weaviate
        from openai import AsyncOpenAI
        import os
        
        container = DependencyContainer()
        
        # Production embedding model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            model_name = config.embedding.model_name if config else os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
            container.bind(
                AbstractEmbeddingModel,
                SentenceTransformer,
                model_name_or_path=model_name
            )
        
        # Production Weaviate client
        if config:
            weaviate_url = config.weaviate.url
            weaviate_api_key = config.weaviate.api_key
        else:
            weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
            weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
            
        container.bind(
            AbstractWeaviateClient,
            weaviate.Client,
            url=weaviate_url,
            auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key) if weaviate_api_key else None
        )
        
        # Production OpenAI client
        if config:
            openai_api_key = config.openai.api_key
        else:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
        if openai_api_key:
            container.bind(
                AbstractOpenAIClient,
                AsyncOpenAI,
                api_key=openai_api_key
            )
        
        return container
    
    @staticmethod
    def create_test_container(
        embedding_available: bool = True,
        weaviate_connected: bool = True,
        openai_available: bool = True
    ) -> DependencyContainer:
        """Create container with mock dependencies for testing"""
        container = DependencyContainer()
        
        # Mock dependencies
        container.bind_instance(
            AbstractEmbeddingModel,
            MockEmbeddingModel(available=embedding_available)
        )
        
        container.bind_instance(
            AbstractWeaviateClient,
            MockWeaviateClient(connected=weaviate_connected)
        )
        
        container.bind_instance(
            AbstractOpenAIClient,
            MockOpenAIClient(available=openai_available)
        )
        
        return container
    
    @staticmethod
    def create_degraded_container() -> DependencyContainer:
        """Create container simulating degraded service conditions"""
        return DependencyConfiguration.create_test_container(
            embedding_available=False,
            weaviate_connected=True,
            openai_available=False
        )

# Global container instance
_global_container: Optional[DependencyContainer] = None

def get_container() -> DependencyContainer:
    """Get the global dependency container"""
    global _global_container
    if _global_container is None:
        _global_container = DependencyConfiguration.create_production_container()
    return _global_container

def set_container(container: DependencyContainer):
    """Set the global dependency container"""
    global _global_container
    _global_container = container

def reset_container():
    """Reset the global dependency container"""
    global _global_container
    _global_container = None
