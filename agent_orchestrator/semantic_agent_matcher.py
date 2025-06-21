"""
Semantic Agent Matching with Vector-based Capability Matching

This module provides advanced agent discovery using semantic similarity and embeddings.
It enhances the basic capability matching with vector-based similarity, capability
ontology, and dynamic learning from agent performance.

Features:
- Vector-based capability matching using embeddings
- Hierarchical capability ontology with inheritance
- Dynamic capability learning from performance metrics
- Cosine similarity for task-agent matching
- Performance-weighted agent scoring
- Capability expansion and normalization
- Caching for improved performance
- Advanced learning algorithms with memory decay
- Multi-dimensional scoring with confidence estimation
- Contextual capability relationships

Author: Agent Orchestrator Team
Version: 2.0.0 - Enhanced with Advanced Learning
"""

import asyncio
import logging
import json
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
from pathlib import Path
import hashlib
import math
from statistics import mean, stdev

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from database import get_db_session
from db_service import AgentRepository, DatabaseOperationError
from models import Agent, AgentTypeEnum

logger = logging.getLogger(__name__)


@dataclass
class CapabilityNode:
    """Represents a node in the capability ontology tree"""
    name: str
    parent: Optional[str] = None
    children: Set[str] = field(default_factory=set)
    aliases: Set[str] = field(default_factory=set)
    description: str = ""
    weight: float = 1.0  # Importance weight for this capability
    domain: str = "general"  # Domain categorization
    complexity_score: float = 1.0  # Complexity estimation
    prerequisites: Set[str] = field(default_factory=set)  # Required capabilities
    tags: Set[str] = field(default_factory=set)  # Additional metadata tags


@dataclass
class PerformanceMetric:
    """Enhanced performance metric with temporal tracking"""
    value: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    weight: float = 1.0


@dataclass
class AgentCapabilityProfile:
    """Enhanced agent capability profile with embeddings and performance data"""
    agent_id: str
    capabilities: List[str]
    capability_embeddings: Optional[np.ndarray] = None
    performance_scores: Dict[str, float] = field(default_factory=dict)
    success_rate: float = 0.5
    avg_response_time: float = 1.0
    task_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    specialization_scores: Dict[str, float] = field(default_factory=dict)
    
    # Enhanced learning features
    performance_history: Dict[str, List[PerformanceMetric]] = field(default_factory=dict)
    capability_confidence: Dict[str, float] = field(default_factory=dict)
    learning_rate: float = 0.1
    adaptation_score: float = 0.5  # How well agent adapts to new tasks
    domain_expertise: Dict[str, float] = field(default_factory=dict)
    collaboration_history: Dict[str, int] = field(default_factory=dict)
    failure_patterns: List[Dict[str, Any]] = field(default_factory=list)
    
    def update_performance_with_context(self, task_type: str, success: bool, 
                                      response_time: float, context: Dict[str, Any] = None):
        """Update performance with contextual information"""
        if task_type not in self.performance_history:
            self.performance_history[task_type] = deque(maxlen=100)  # Keep last 100 records
        
        metric = PerformanceMetric(
            value=1.0 if success else 0.0,
            timestamp=datetime.utcnow(),
            context=context or {},
            confidence=self._calculate_confidence(task_type, context),
            weight=self._calculate_weight(task_type, response_time)
        )
        
        self.performance_history[task_type].append(metric)
        self._update_derived_metrics(task_type)
    
    def _calculate_confidence(self, task_type: str, context: Dict[str, Any] = None) -> float:
        """Calculate confidence based on historical performance and context"""
        if task_type not in self.performance_history:
            return 0.5
        
        recent_performance = list(self.performance_history[task_type])[-10:]  # Last 10 tasks
        if not recent_performance:
            return 0.5
        
        # Base confidence from success rate
        success_rate = mean([m.value for m in recent_performance])
        
        # Adjust for consistency (lower variance = higher confidence)
        if len(recent_performance) > 1:
            variance = stdev([m.value for m in recent_performance])
            consistency_factor = max(0.1, 1.0 - variance)
        else:
            consistency_factor = 0.5
        
        # Context-based adjustments
        context_factor = 1.0
        if context:
            # Similar contexts should increase confidence
            similar_contexts = sum(1 for m in recent_performance if m.context.keys() & context.keys())
            context_factor = min(1.2, 1.0 + (similar_contexts / len(recent_performance) * 0.2))
        
        return min(1.0, success_rate * consistency_factor * context_factor)
    
    def _calculate_weight(self, task_type: str, response_time: float) -> float:
        """Calculate importance weight for this performance metric"""
        # More recent tasks have higher weight
        recency_weight = 1.0
        
        # Faster responses (within reason) get higher weight
        time_weight = max(0.5, min(1.5, 2.0 / (1.0 + response_time / 2.0)))
        
        # Tasks that are more frequent for this agent get higher weight
        task_frequency = len(self.performance_history.get(task_type, [])) / max(1, self.task_count)
        frequency_weight = min(1.5, 1.0 + task_frequency)
        
        return recency_weight * time_weight * frequency_weight
    
    def _update_derived_metrics(self, task_type: str):
        """Update derived performance metrics"""
        if task_type not in self.performance_history:
            return
        
        metrics = list(self.performance_history[task_type])
        if not metrics:
            return
        
        # Calculate weighted performance score
        total_weight = sum(m.weight for m in metrics)
        if total_weight > 0:
            weighted_score = sum(m.value * m.weight for m in metrics) / total_weight
            self.performance_scores[task_type] = weighted_score
        
        # Update confidence
        self.capability_confidence[task_type] = mean([m.confidence for m in metrics])
        
        # Update adaptation score based on recent performance trend
        if len(metrics) >= 5:
            recent_scores = [m.value for m in metrics[-5:]]
            older_scores = [m.value for m in metrics[-10:-5]] if len(metrics) >= 10 else []
            
            if older_scores:
                recent_avg = mean(recent_scores)
                older_avg = mean(older_scores)
                adaptation = min(1.0, max(0.0, (recent_avg - older_avg + 1.0) / 2.0))
                self.adaptation_score = (self.adaptation_score * 0.8) + (adaptation * 0.2)


@dataclass
class TaskMatchingResult:
    """Result of task-agent matching with detailed scoring"""
    agent_id: str
    agent_name: str
    similarity_score: float
    capability_match_score: float
    performance_score: float
    combined_score: float
    matched_capabilities: List[str]
    missing_capabilities: List[str]
    confidence: float
    reasoning: str
    
    # Enhanced scoring details
    domain_match_score: float = 0.0
    adaptation_score: float = 0.0
    collaboration_potential: float = 0.0
    learning_trajectory: str = "stable"
    risk_assessment: str = "low"
    recommended_training: List[str] = field(default_factory=list)


class CapabilityOntology:
    """Enhanced hierarchical capability ontology with inheritance and relationships"""
    
    def __init__(self):
        self.nodes: Dict[str, CapabilityNode] = {}
        self.capability_embeddings: Dict[str, np.ndarray] = {}
        self.domain_clusters: Dict[str, List[str]] = {}
        self.capability_relationships: Dict[str, Dict[str, float]] = {}
        self._build_enhanced_ontology()
    def _build_enhanced_ontology(self):
        """Build the enhanced capability ontology for surveillance system"""
        # Enhanced surveillance capabilities with domains and complexity
        ontology_structure = {
            "surveillance": {
                "domain": "security", "complexity": 1.0,
                "description": "Core surveillance and monitoring capabilities",
                "children": {
                    "detection": {
                        "domain": "computer_vision", "complexity": 2.0,
                        "description": "Object and event detection capabilities",
                        "aliases": {"detect", "identify", "recognize"},
                        "children": {
                            "person_detection": {"domain": "cv_detection", "complexity": 2.5, "tags": {"real_time", "accuracy_critical"}},
                            "vehicle_detection": {"domain": "cv_detection", "complexity": 2.0, "tags": {"traffic", "monitoring"}},
                            "object_detection": {"domain": "cv_detection", "complexity": 3.0, "tags": {"general_purpose"}},
                            "anomaly_detection": {"domain": "cv_analysis", "complexity": 4.0, "tags": {"ai_intensive", "pattern_recognition"}},
                            "motion_detection": {"domain": "cv_basic", "complexity": 1.5, "tags": {"low_latency", "edge_computing"}},
                            "face_detection": {"domain": "biometrics", "complexity": 3.0, "tags": {"privacy_sensitive", "accuracy_critical"}},
                            "license_plate_detection": {"domain": "ocr", "complexity": 3.5, "tags": {"text_recognition", "traffic"}},
                        }
                    },
                    "tracking": {
                        "domain": "computer_vision", "complexity": 3.0,
                        "description": "Object tracking and movement analysis",
                        "aliases": {"track", "follow", "monitor"},
                        "children": {
                            "person_tracking": {"domain": "cv_tracking", "complexity": 3.5, "prerequisites": {"person_detection"}},
                            "vehicle_tracking": {"domain": "cv_tracking", "complexity": 3.0, "prerequisites": {"vehicle_detection"}},
                            "multi_object_tracking": {"domain": "cv_advanced", "complexity": 4.5, "prerequisites": {"object_detection"}},
                            "trajectory_analysis": {"domain": "analytics", "complexity": 4.0, "prerequisites": {"tracking"}},
                        }
                    },
                    "analysis": {
                        "domain": "analytics", "complexity": 3.5,
                        "description": "Data analysis and processing capabilities",
                        "aliases": {"analyze", "process", "evaluate"},
                        "children": {
                            "behavior_analysis": {"domain": "ai_analysis", "complexity": 4.5, "tags": {"machine_learning", "pattern_recognition"}},
                            "crowd_analysis": {"domain": "social_analytics", "complexity": 4.0, "tags": {"statistical_analysis"}},
                            "activity_recognition": {"domain": "ai_analysis", "complexity": 4.0, "prerequisites": {"behavior_analysis"}},
                            "risk_assessment": {"domain": "decision_support", "complexity": 4.5, "tags": {"predictive", "critical"}},
                            "pattern_recognition": {"domain": "ai_core", "complexity": 4.0, "tags": {"machine_learning"}},
                        }
                    },
                    "alerting": {
                        "domain": "notification", "complexity": 2.0,
                        "description": "Alert generation and notification",
                        "aliases": {"notify", "alert", "warn"},
                        "children": {
                            "real_time_alerts": {"domain": "notification", "complexity": 2.5, "tags": {"low_latency", "critical"}},
                            "email_notifications": {"domain": "communication", "complexity": 1.5, "tags": {"standard"}},
                            "sms_alerts": {"domain": "communication", "complexity": 1.5, "tags": {"mobile"}},
                            "dashboard_updates": {"domain": "ui", "complexity": 2.0, "tags": {"visualization"}},
                            "escalation_management": {"domain": "workflow", "complexity": 3.0, "tags": {"business_logic"}},
                        }
                    }
                }
            },
            "ai_processing": {
                "domain": "artificial_intelligence", "complexity": 4.0,
                "description": "AI and machine learning processing capabilities",
                "children": {
                    "rag_query": {
                        "domain": "information_retrieval", "complexity": 3.5,
                        "description": "Retrieval Augmented Generation queries",
                        "aliases": {"search", "retrieval", "knowledge_query"},
                        "tags": {"nlp", "vector_search", "embeddings"}
                    },
                    "prompt_generation": {
                        "domain": "natural_language", "complexity": 3.0,
                        "description": "AI prompt generation and optimization",
                        "aliases": {"prompt", "generation", "text_generation"},
                        "tags": {"llm", "text_processing"}
                    },
                    "rule_generation": {
                        "domain": "automation", "complexity": 4.0,
                        "description": "Automated rule creation and validation",
                        "aliases": {"rules", "automation", "logic"},
                        "tags": {"expert_systems", "decision_trees"}
                    },
                    "classification": {
                        "domain": "machine_learning", "complexity": 3.5,
                        "description": "Data classification and categorization",
                        "tags": {"supervised_learning", "prediction"}
                    }
                }
            },
            "data_processing": {
                "domain": "infrastructure", "complexity": 2.0,
                "description": "Data processing and management capabilities",
                "children": {
                    "video_processing": {"domain": "media", "complexity": 3.0, "tags": {"gpu_intensive", "streaming"}},
                    "image_processing": {"domain": "media", "complexity": 2.5, "tags": {"cpu_intensive"}},
                    "stream_processing": {"domain": "data_streaming", "complexity": 3.5, "tags": {"real_time", "scalability"}},
                    "data_compression": {"domain": "optimization", "complexity": 2.5, "tags": {"storage"}},
                    "format_conversion": {"domain": "media", "complexity": 2.0, "tags": {"compatibility"}},
                }
            }
        }
        
        # Build nodes from structure
        self._build_nodes_from_structure(ontology_structure)
        
        # Compute relationships
        self._compute_capability_relationships()
        
        # Create domain clusters
        self._create_domain_clusters()
    
    def _build_nodes_from_structure(self, structure: Dict[str, Any], parent: str = None):
        """Recursively build capability nodes from structure"""
        for capability, details in structure.items():
            # Handle string details (leaf nodes)
            if isinstance(details, str):
                details = {"domain": "general", "complexity": 1.0}
            
            # Create node
            node = CapabilityNode(
                name=capability,
                parent=parent,
                domain=details.get("domain", "general"),
                complexity_score=details.get("complexity", 1.0),
                description=details.get("description", f"Capability: {capability}"),
                weight=details.get("weight", 1.0),
                tags=set(details.get("tags", [])),
                prerequisites=set(details.get("prerequisites", []))
            )
            
            # Add aliases
            if "aliases" in details:
                node.aliases.update(details["aliases"])
            
            self.nodes[capability] = node
            
            # Update parent's children
            if parent and parent in self.nodes:
                self.nodes[parent].children.add(capability)
            
            # Recursively process children
            if "children" in details:
                self._build_nodes_from_structure(details["children"], capability)
    
    def _compute_capability_relationships(self):
        """Compute semantic relationships between all capabilities"""
        capabilities = list(self.nodes.keys())
        
        for cap1 in capabilities:
            self.capability_relationships[cap1] = {}
            for cap2 in capabilities:
                if cap1 != cap2:
                    similarity = self.calculate_enhanced_similarity(cap1, cap2)
                    if similarity > 0.1:  # Only store significant relationships
                        self.capability_relationships[cap1][cap2] = similarity
    
    def _create_domain_clusters(self):
        """Group capabilities by domain for enhanced matching"""
        for capability, node in self.nodes.items():
            domain = node.domain
            if domain not in self.domain_clusters:
                self.domain_clusters[domain] = []
            self.domain_clusters[domain].append(capability)
    
    def get_expanded_capabilities(self, capabilities: List[str]) -> Set[str]:
        """Expand capabilities to include parent and child capabilities with enhanced logic"""
        expanded = set(capabilities)
        
        for capability in capabilities:
            if capability in self.nodes:
                node = self.nodes[capability]
                
                # Add parent capabilities
                current = node.parent
                while current:
                    expanded.add(current)
                    current = self.nodes[current].parent if current in self.nodes else None
                
                # Add direct children
                expanded.update(node.children)
                
                # Add prerequisites
                expanded.update(node.prerequisites)
                
                # Add highly related capabilities
                if capability in self.capability_relationships:
                    for related_cap, similarity in self.capability_relationships[capability].items():
                        if similarity > 0.8:  # High similarity threshold
                            expanded.add(related_cap)
                
                # Add aliases
                expanded.update(node.aliases)
            
            # Check aliases in all nodes
            for node_name, node in self.nodes.items():
                if capability.lower() in {alias.lower() for alias in node.aliases}:
                    expanded.add(node_name)
                    expanded.update(node.children)
                    if node.parent:
                        expanded.add(node.parent)
        
        return expanded
    
    def get_capability_domain_score(self, capabilities: List[str], target_domain: str) -> float:
        """Calculate how well capabilities match a target domain"""
        if not capabilities:
            return 0.0
        
        domain_matches = 0
        total_weight = 0
        
        for capability in capabilities:
            if capability in self.nodes:
                node = self.nodes[capability]
                weight = node.weight * node.complexity_score
                total_weight += weight
                
                if node.domain == target_domain:
                    domain_matches += weight
                elif self._domains_related(node.domain, target_domain):
                    domain_matches += weight * 0.6
        
        return domain_matches / total_weight if total_weight > 0 else 0.0
    
    def suggest_capability_improvements(self, current_capabilities: List[str], 
                                      target_capabilities: List[str]) -> List[str]:
        """Suggest capabilities that would help bridge the gap"""
        suggestions = []
        missing = set(target_capabilities) - set(current_capabilities)
        
        for missing_cap in missing:
            if missing_cap in self.nodes:
                node = self.nodes[missing_cap]
                
                # Check prerequisites
                unmet_prereqs = node.prerequisites - set(current_capabilities)
                if unmet_prereqs:
                    suggestions.extend([f"Learn {prereq} (prerequisite for {missing_cap})" 
                                     for prereq in unmet_prereqs])
                
                # Find stepping stone capabilities
                for current_cap in current_capabilities:
                    if (current_cap in self.capability_relationships and 
                        missing_cap in self.capability_relationships[current_cap]):
                        similarity = self.capability_relationships[current_cap][missing_cap]
                        if 0.5 < similarity < 0.8:
                            suggestions.append(f"Strengthen {current_cap} to develop {missing_cap}")
        
        return list(set(suggestions))  # Remove duplicates
    
    def calculate_enhanced_similarity(self, cap1: str, cap2: str) -> float:
        """Calculate enhanced semantic similarity between two capabilities"""
        if cap1 == cap2:
            return 1.0
        
        if cap1 not in self.nodes or cap2 not in self.nodes:
            return 0.0
        
        node1, node2 = self.nodes[cap1], self.nodes[cap2]
        
        # Direct relationships
        if cap1 in node2.children or cap2 in node1.children:
            return 0.9  # Parent-child
        
        if cap1 in node2.prerequisites or cap2 in node1.prerequisites:
            return 0.8  # Prerequisite relationship
        
        # Sibling relationship (same parent)
        if node1.parent and node2.parent and node1.parent == node2.parent:
            return 0.7
        
        # Domain similarity
        domain_similarity = 0.0
        if node1.domain == node2.domain:
            domain_similarity = 0.6
        elif self._domains_related(node1.domain, node2.domain):
            domain_similarity = 0.4
        
        # Tag overlap
        tag_similarity = 0.0
        if node1.tags and node2.tags:
            common_tags = node1.tags & node2.tags
            total_tags = node1.tags | node2.tags
            tag_similarity = len(common_tags) / len(total_tags) * 0.3
        
        # Complexity similarity (similar complexity levels might be related)
        complexity_diff = abs(node1.complexity_score - node2.complexity_score)
        complexity_similarity = max(0, 0.2 * (1 - complexity_diff / 5.0))
        
        # Check aliases
        alias_similarity = 0.0
        if cap2 in node1.aliases or cap1 in node2.aliases:
            alias_similarity = 0.95
        
        # Use embedding similarity if available
        embedding_similarity = 0.0
        if (cap1 in self.capability_embeddings and 
            cap2 in self.capability_embeddings):
            cosine_sim = cosine_similarity(
                self.capability_embeddings[cap1].reshape(1, -1),
                self.capability_embeddings[cap2].reshape(1, -1)
            )[0][0]
            embedding_similarity = float(cosine_sim) * 0.4
        
        # Combine all similarity scores
        total_similarity = max(
            alias_similarity,  # Aliases have highest priority
            domain_similarity + tag_similarity + complexity_similarity + embedding_similarity
        )
        
        return min(1.0, total_similarity)
    
    def _domains_related(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are related"""
        related_domains = {
            "computer_vision": {"cv", "cv_detection", "cv_tracking", "cv_analysis", "cv_advanced", "cv_basic"},
            "ai": {"machine_learning", "deep_learning", "ai_analysis", "ai_core", "artificial_intelligence"},
            "communication": {"notification", "ui", "workflow"},
            "media": {"data_streaming", "optimization"}
        }
        
        for related_group in related_domains.values():
            if domain1 in related_group and domain2 in related_group:
                return True
        return False


class SemanticAgentMatcher:
    """Advanced agent matching using semantic similarity and performance data"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.embedding_model = None
        self.ontology = CapabilityOntology()
        self.agent_profiles: Dict[str, AgentCapabilityProfile] = {}
        self.capability_embeddings: Dict[str, np.ndarray] = {}
        self.task_embeddings_cache: Dict[str, np.ndarray] = {}
        self.cache_ttl = timedelta(hours=1)
        
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(model_name)
                logger.info(f"Initialized semantic matcher with model: {model_name}")
                self._precompute_capability_embeddings()
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                self.embedding_model = None
        else:
            logger.warning("Sentence transformers not available, using fallback matching")
    
    def _precompute_capability_embeddings(self):
        """Precompute embeddings for all known capabilities"""
        if not self.embedding_model:
            return
        
        all_capabilities = set()
        for node in self.ontology.nodes.values():
            all_capabilities.add(node.name)
            all_capabilities.update(node.aliases)
            all_capabilities.add(node.description)
        
        # Add common surveillance capabilities
        common_caps = [
            "motion detection", "face recognition", "person detection",
            "vehicle detection", "object tracking", "anomaly detection",
            "video analysis", "audio analysis", "real time monitoring",
            "alert generation", "pattern recognition", "behavior analysis",
            "rag query", "search", "retrieval", "prompt generation",
            "rule generation", "classification", "prediction"
        ]
        all_capabilities.update(common_caps)
        
        try:
            capability_list = list(all_capabilities)
            embeddings = self.embedding_model.encode(capability_list)
            
            for cap, embedding in zip(capability_list, embeddings):
                self.capability_embeddings[cap] = embedding
                self.ontology.capability_embeddings[cap] = embedding
            
            logger.info(f"Precomputed embeddings for {len(capability_list)} capabilities")
        except Exception as e:
            logger.error(f"Failed to precompute capability embeddings: {e}")
    
    def _get_task_embedding(self, task_description: str) -> Optional[np.ndarray]:
        """Get or compute embedding for task description with caching"""
        if not self.embedding_model:
            return None
        
        # Create cache key
        cache_key = hashlib.md5(task_description.encode()).hexdigest()
        
        # Check cache
        if cache_key in self.task_embeddings_cache:
            return self.task_embeddings_cache[cache_key]
        
        try:
            embedding = self.embedding_model.encode([task_description])[0]
            self.task_embeddings_cache[cache_key] = embedding
            
            # Clean old cache entries
            if len(self.task_embeddings_cache) > 1000:
                self._clean_embedding_cache()
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to compute task embedding: {e}")
            return None
    
    def _clean_embedding_cache(self):
        """Clean old entries from embedding cache"""
        # Simple strategy: keep last 500 entries
        if len(self.task_embeddings_cache) > 500:
            # Keep the most recent 500 entries (this is a simple approach)
            # In production, you might want to use LRU cache or TTL
            keys_to_keep = list(self.task_embeddings_cache.keys())[-500:]
            self.task_embeddings_cache = {
                k: v for k, v in self.task_embeddings_cache.items() 
                if k in keys_to_keep
            }
    
    async def register_agent(self, agent_id: str, capabilities: List[str], 
                           agent_data: Optional[Dict[str, Any]] = None):
        """Register an agent with its capabilities and compute embeddings"""
        try:
            # Use the enhanced capability expansion
            expanded_capabilities = list(self.ontology.get_expanded_capabilities(capabilities))
            
            # Compute capability embeddings
            capability_embeddings = None
            if self.embedding_model and expanded_capabilities:
                try:
                    embeddings = self.embedding_model.encode(expanded_capabilities)
                    # Use mean embedding for the agent's overall capability profile
                    capability_embeddings = np.mean(embeddings, axis=0)
                except Exception as e:
                    logger.warning(f"Failed to compute capability embeddings for agent {agent_id}: {e}")
            
            # Create agent profile
            profile = AgentCapabilityProfile(
                agent_id=agent_id,
                capabilities=expanded_capabilities,
                capability_embeddings=capability_embeddings,
                last_updated=datetime.utcnow()
            )
            
            # Load performance data if provided
            if agent_data:
                profile.success_rate = agent_data.get("success_rate", 0.5)
                profile.avg_response_time = agent_data.get("avg_response_time", 1.0)
                profile.task_count = agent_data.get("task_count", 0)
                profile.performance_scores = agent_data.get("performance_scores", {})
            
            self.agent_profiles[agent_id] = profile
            logger.debug(f"Registered agent {agent_id} with {len(expanded_capabilities)} capabilities")
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            raise
    
    async def update_agent_performance(self, agent_id: str, task_type: str, 
                                     success: bool, response_time: float, 
                                     context: Dict[str, Any] = None):
        """Enhanced agent performance update with contextual learning"""
        if agent_id not in self.agent_profiles:
            logger.warning(f"Agent {agent_id} not found in profiles")
            return
        
        profile = self.agent_profiles[agent_id]
        profile.task_count += 1
        
        # Use the enhanced performance tracking
        profile.update_performance_with_context(task_type, success, response_time, context)
        
        # Update overall success rate (exponential moving average with adaptive learning rate)
        alpha = min(0.2, profile.learning_rate * (1.0 + profile.adaptation_score))
        if success:
            profile.success_rate = profile.success_rate * (1 - alpha) + alpha
        else:
            profile.success_rate = profile.success_rate * (1 - alpha)
            # Track failure patterns for learning
            self._track_failure_pattern(profile, task_type, context, response_time)
        
        # Update average response time with recency weighting
        profile.avg_response_time = (profile.avg_response_time * (1 - alpha) + 
                                   response_time * alpha)
        
        # Update task-specific performance scores
        if task_type not in profile.performance_scores:
            profile.performance_scores[task_type] = 0.5
        
        if success:
            profile.performance_scores[task_type] = (
                profile.performance_scores[task_type] * (1 - alpha) + alpha
            )
        else:
            profile.performance_scores[task_type] = (
                profile.performance_scores[task_type] * (1 - alpha)
            )
        
        # Update capability specialization scores
        self._update_capability_specialization(profile, task_type, success, alpha)
        
        # Update domain expertise
        self._update_domain_expertise(profile, task_type, success)
        
        profile.last_updated = datetime.utcnow()
        logger.debug(f"Updated performance for agent {agent_id}: success_rate={profile.success_rate:.3f}")
    
    def _calculate_capability_match_score(self, required_capabilities: List[str], 
                                        agent_capabilities: List[str]) -> Tuple[float, List[str], List[str]]:
        """Calculate how well agent capabilities match required capabilities"""
        if not required_capabilities:
            return 1.0, agent_capabilities, []
        
        matched_capabilities = []
        missing_capabilities = []
        total_score = 0.0
        
        for req_cap in required_capabilities:
            best_match_score = 0.0
            best_match_cap = None
            for agent_cap in agent_capabilities:
                similarity = self.ontology.calculate_enhanced_similarity(req_cap, agent_cap)
                if similarity > best_match_score:
                    best_match_score = similarity
                    best_match_cap = agent_cap
            
            if best_match_score >= 0.5:  # Threshold for considering a match
                matched_capabilities.append(best_match_cap)
                total_score += best_match_score
            else:
                missing_capabilities.append(req_cap)
        
        # Calculate overall match score
        if required_capabilities:
            capability_match_score = total_score / len(required_capabilities)
        else:
            capability_match_score = 1.0
        
        return capability_match_score, matched_capabilities, missing_capabilities
    
    def _calculate_performance_score(self, profile: AgentCapabilityProfile, 
                                   task_type: str = "") -> float:
        """Calculate performance score for an agent"""
        base_score = profile.success_rate
        
        # Adjust for response time (lower is better)
        time_penalty = min(profile.avg_response_time / 5.0, 1.0)  # Penalty for >5s response
        time_adjusted_score = base_score * (1 - time_penalty * 0.2)
        
        # Adjust for task experience
        experience_bonus = min(profile.task_count / 100.0, 0.2)  # Up to 20% bonus
        experience_adjusted_score = time_adjusted_score + experience_bonus
        
        # Task-specific performance if available
        if task_type and task_type in profile.performance_scores:
            task_specific_score = profile.performance_scores[task_type]
            # Weighted combination
            final_score = (experience_adjusted_score * 0.7 + task_specific_score * 0.3)
        else:
            final_score = experience_adjusted_score
        
        return min(final_score, 1.0)
    
    def _calculate_semantic_similarity(self, task_description: str, 
                                     agent_profile: AgentCapabilityProfile) -> float:
        """Calculate semantic similarity between task and agent capabilities"""
        if not self.embedding_model or agent_profile.capability_embeddings is None:
            return 0.5  # Fallback score when embeddings not available
        
        task_embedding = self._get_task_embedding(task_description)
        if task_embedding is None:
            return 0.5
        
        try:
            similarity = cosine_similarity(
                task_embedding.reshape(1, -1),
                agent_profile.capability_embeddings.reshape(1, -1)
            )[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.5
    
    async def find_matching_agents(self, task_description: str, 
                                 required_capabilities: List[str] = None,
                                 task_type: str = "", top_k: int = 3,
                                 min_score: float = 0.3) -> List[TaskMatchingResult]:
        """Find best matching agents for a task using semantic similarity and performance data"""
        if not self.agent_profiles:
            logger.warning("No agent profiles available for matching")
            return []
        
        required_capabilities = required_capabilities or []
        results = []
        
        for agent_id, profile in self.agent_profiles.items():
            try:
                # Calculate capability match score
                capability_score, matched_caps, missing_caps = self._calculate_capability_match_score(
                    required_capabilities, profile.capabilities
                )
                
                # Calculate semantic similarity
                semantic_score = self._calculate_semantic_similarity(task_description, profile)
                
                # Calculate performance score
                performance_score = self._calculate_performance_score(profile, task_type)
                
                # Combined scoring with weights
                weights = {
                    "capability": 0.4,
                    "semantic": 0.3, 
                    "performance": 0.3
                }
                
                combined_score = (
                    capability_score * weights["capability"] +
                    semantic_score * weights["semantic"] +
                    performance_score * weights["performance"] 
                )
                
                # Calculate confidence based on data quality
                confidence = min(
                    1.0,
                    (profile.task_count / 50.0) * 0.5 +  # Experience factor
                    (len(profile.capabilities) / 10.0) * 0.3 +  # Capability diversity
                    0.2  # Base confidence
                )
                
                # Generate reasoning
                reasoning_parts = []
                reasoning_parts.append(f"Capability match: {capability_score:.2f}")
                reasoning_parts.append(f"Semantic similarity: {semantic_score:.2f}")
                reasoning_parts.append(f"Performance: {performance_score:.2f}")
                reasoning_parts.append(f"Experience: {profile.task_count} tasks")
                
                reasoning = "; ".join(reasoning_parts)
                
                # Get agent name (we'll need to fetch this from database)
                agent_name = f"Agent-{agent_id[:8]}"  # Fallback name
                
                result = TaskMatchingResult(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    similarity_score=semantic_score,
                    capability_match_score=capability_score,
                    performance_score=performance_score,
                    combined_score=combined_score,
                    matched_capabilities=matched_caps,
                    missing_capabilities=missing_caps,
                    confidence=confidence,
                    reasoning=reasoning
                )
                
                if combined_score >= min_score:
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Error evaluating agent {agent_id}: {e}")
                continue
        
        # Sort by combined score (descending) and return top_k
        results.sort(key=lambda x: x.combined_score, reverse=True)
        return results[:top_k]
    
    async def sync_with_database(self, db: AsyncSession):
        """Synchronize agent profiles with database"""
        try:
            # Get all active agents from database
            agents, _ = await AgentRepository.list_agents(
                db=db,
                limit=1000,  # Get all agents
                offset=0
            )
            
            for agent in agents:
                # Check if we need to update the profile
                if (agent.id not in self.agent_profiles or 
                    self.agent_profiles[agent.id].last_updated < agent.updated_at):
                    
                    # Extract performance data from agent
                    performance_data = {
                        "success_rate": agent.performance_metrics.get("success_rate", 0.5),
                        "avg_response_time": agent.performance_metrics.get("avg_response_time", 1.0),
                        "task_count": agent.performance_metrics.get("task_count", 0),
                        "performance_scores": agent.performance_metrics.get("performance_scores", {})
                    }
                    
                    await self.register_agent(
                        agent_id=agent.id,
                        capabilities=agent.capabilities,
                        agent_data=performance_data
                    )
            
            logger.info(f"Synchronized {len(agents)} agent profiles with database")
            
        except Exception as e:
            logger.error(f"Failed to sync with database: {e}")
            raise

    def _track_failure_pattern(self, profile: AgentCapabilityProfile, task_type: str, 
                              context: Dict[str, Any], response_time: float):
        """Track failure patterns for learning improvement"""
        failure_info = {
            "task_type": task_type,
            "timestamp": datetime.utcnow(),
            "context": context or {},
            "response_time": response_time,
            "agent_state": {
                "success_rate": profile.success_rate,
                "task_count": profile.task_count,
                "adaptation_score": profile.adaptation_score
            }
        }
        
        profile.failure_patterns.append(failure_info)
        
        # Keep only recent failures (last 50)
        if len(profile.failure_patterns) > 50:
            profile.failure_patterns = profile.failure_patterns[-50:]
        
        # Analyze patterns for insights
        self._analyze_failure_patterns(profile)
    
    def _analyze_failure_patterns(self, profile: AgentCapabilityProfile):
        """Analyze failure patterns to identify improvement opportunities"""
        if len(profile.failure_patterns) < 5:
            return
        
        recent_failures = profile.failure_patterns[-10:]
        
        # Check for common failure contexts
        context_patterns = defaultdict(int)
        task_type_failures = defaultdict(int)
        
        for failure in recent_failures:
            task_type_failures[failure["task_type"]] += 1
            for key, value in failure["context"].items():
                context_patterns[f"{key}:{value}"] += 1
        
        # Identify problematic areas (adjust learning rate)
        for task_type, count in task_type_failures.items():
            if count >= 3:  # Multiple failures in same task type
                if task_type in profile.capability_confidence:
                    profile.capability_confidence[task_type] *= 0.8  # Reduce confidence
                profile.learning_rate = min(0.3, profile.learning_rate * 1.2)  # Increase learning rate
    
    def _update_capability_specialization(self, profile: AgentCapabilityProfile, 
                                        task_type: str, success: bool, alpha: float):
        """Update specialization scores for relevant capabilities"""
        relevant_capabilities = self._identify_relevant_capabilities(task_type)
        
        for capability in relevant_capabilities:
            if capability not in profile.specialization_scores:
                profile.specialization_scores[capability] = 0.5
            
            if success:
                profile.specialization_scores[capability] = (
                    profile.specialization_scores[capability] * (1 - alpha) + alpha
                )
            else:
                profile.specialization_scores[capability] = (
                    profile.specialization_scores[capability] * (1 - alpha)
                )
    
    def _update_domain_expertise(self, profile: AgentCapabilityProfile, 
                               task_type: str, success: bool):
        """Update domain expertise based on task performance"""
        # Identify task domain
        task_domain = self._identify_task_domain(task_type)
        if not task_domain:
            return
        
        if task_domain not in profile.domain_expertise:
            profile.domain_expertise[task_domain] = 0.5
        
        # Domain expertise grows slower but is more stable
        domain_alpha = 0.05
        if success:
            profile.domain_expertise[task_domain] = (
                profile.domain_expertise[task_domain] * (1 - domain_alpha) + domain_alpha
            )
        else:
            profile.domain_expertise[task_domain] = (
                profile.domain_expertise[task_domain] * (1 - domain_alpha)
            )
    
    def _identify_relevant_capabilities(self, task_type: str) -> List[str]:
        """Identify capabilities relevant to a task type"""
        relevant = []
        task_lower = task_type.lower()
        
        for capability in self.ontology.nodes.keys():
            if (capability in task_lower or 
                any(alias in task_lower for alias in self.ontology.nodes[capability].aliases) or
                task_lower in capability):
                relevant.append(capability)
        
        return relevant
    
    def _identify_task_domain(self, task_type: str) -> Optional[str]:
        """Identify the primary domain for a task type"""
        relevant_capabilities = self._identify_relevant_capabilities(task_type)
        
        domain_counts = defaultdict(int)
        for capability in relevant_capabilities:
            if capability in self.ontology.nodes:
                domain = self.ontology.nodes[capability].domain
                domain_counts[domain] += 1
        
        if domain_counts:
            return max(domain_counts.items(), key=lambda x: x[1])[0]
        return None


# Global semantic matcher instance
_semantic_matcher: Optional[SemanticAgentMatcher] = None


async def get_semantic_matcher() -> SemanticAgentMatcher:
    """Get the global semantic matcher instance"""
    global _semantic_matcher
    
    if _semantic_matcher is None:
        _semantic_matcher = SemanticAgentMatcher()
        
        # Initialize with database data
        try:
            async with get_db_session() as db:
                await _semantic_matcher.sync_with_database(db)
        except Exception as e:
            logger.warning(f"Failed to initialize semantic matcher with database: {e}")
    
    return _semantic_matcher


async def find_agents_semantic(task_description: str, 
                             required_capabilities: List[str] = None,
                             task_type: str = "", top_k: int = 3,
                             min_score: float = 0.3) -> List[TaskMatchingResult]:
    """Convenient function to find agents using semantic matching"""
    matcher = await get_semantic_matcher()
    return await matcher.find_matching_agents(
        task_description=task_description,
        required_capabilities=required_capabilities,
        task_type=task_type,
        top_k=top_k,
        min_score=min_score
    )


async def update_agent_performance_semantic(agent_id: str, task_type: str, 
                                          success: bool, response_time: float):
    """Update agent performance in semantic matcher"""
    matcher = await get_semantic_matcher()
    await matcher.update_agent_performance(agent_id, task_type, success, response_time)
