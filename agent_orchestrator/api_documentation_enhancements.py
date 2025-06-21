"""
Enhanced OpenAPI Documentation Models and Examples

This module provides comprehensive API documentation enhancements including:
- Detailed request/response examples for all endpoints
- Error response schemas and examples
- OpenAPI metadata and descriptions
- Response status code documentation
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

# Enhanced Request Examples
AGENT_REGISTRATION_EXAMPLES = [
    {
        "summary": "Register Object Detection Agent",
        "description": "Example of registering a specialized object detection agent for surveillance cameras",
        "value": {
            "name": "Camera-001-ObjectDetector",
            "type": "DETECTOR",
            "endpoint": "https://detector-service.example.com/api/v1/detect",
            "capabilities": [
                "person_detection",
                "vehicle_detection", 
                "object_classification",
                "motion_detection"
            ],
            "metadata": {
                "camera_location": "Main Entrance",
                "camera_id": "CAM-001",
                "detection_confidence_threshold": 0.85,
                "processing_resolution": "1920x1080",
                "max_concurrent_streams": 4
            },
            "tags": ["entrance", "high_priority", "24x7"],
            "health_check_interval": 30,
            "timeout": 15.0
        }
    },
    {
        "summary": "Register Analytics Agent",
        "description": "Example of registering an analytics agent for video analysis and pattern recognition",
        "value": {
            "name": "VideoAnalytics-Engine-001",
            "type": "ANALYZER", 
            "endpoint": "https://analytics-service.example.com/api/v1/analyze",
            "capabilities": [
                "video_analysis",
                "pattern_recognition",
                "behavior_analysis",
                "crowd_detection",
                "anomaly_detection"
            ],
            "metadata": {
                "analysis_types": ["behavioral", "statistical", "temporal"],
                "max_video_duration": 3600,
                "supported_formats": ["mp4", "avi", "webm"],
                "gpu_acceleration": True,
                "model_version": "v2.1.0"
            },
            "tags": ["analytics", "gpu_enabled", "ml_inference"],
            "health_check_interval": 60,
            "timeout": 120.0
        }
    },
    {
        "summary": "Register Notification Agent",
        "description": "Example of registering a notification agent for alert dispatch and escalation",
        "value": {
            "name": "AlertDispatcher-001",
            "type": "NOTIFIER",
            "endpoint": "https://notifications.example.com/api/v1/dispatch",
            "capabilities": [
                "email_alerts",
                "sms_alerts", 
                "webhook_notifications",
                "push_notifications",
                "escalation_management"
            ],
            "metadata": {
                "supported_channels": ["email", "sms", "slack", "teams", "webhook"],
                "max_recipients_per_alert": 100,
                "escalation_levels": 3,
                "rate_limit_per_minute": 1000,
                "template_engine": "jinja2"
            },
            "tags": ["notifications", "high_availability", "escalation"],
            "health_check_interval": 15,
            "timeout": 10.0
        }
    }
]

TASK_CREATION_EXAMPLES = [
    {
        "summary": "Security Incident Analysis Task",
        "description": "High-priority task for analyzing a security incident with multiple cameras",
        "value": {
            "type": "ANALYSIS",
            "priority": "CRITICAL",
            "description": "Analyze security incident at main entrance - unauthorized access attempt",
            "data": {
                "incident_id": "INC-2024-001547",
                "camera_feeds": [
                    {
                        "camera_id": "CAM-001",
                        "feed_url": "rtsp://camera001.example.com/stream",
                        "timestamp_start": "2024-01-15T14:25:00Z",
                        "timestamp_end": "2024-01-15T14:35:00Z"
                    },
                    {
                        "camera_id": "CAM-002", 
                        "feed_url": "rtsp://camera002.example.com/stream",
                        "timestamp_start": "2024-01-15T14:25:00Z",
                        "timestamp_end": "2024-01-15T14:35:00Z"
                    }
                ],
                "initial_detection": {
                    "type": "person_detection",
                    "confidence": 0.94,
                    "location": "main_entrance_zone_a",
                    "person_count": 2
                },
                "analysis_requirements": [
                    "person_identification",
                    "behavioral_analysis", 
                    "access_pattern_check",
                    "risk_assessment"
                ]
            },
            "required_capabilities": [
                "video_analysis",
                "person_detection",
                "behavioral_analysis"
            ],
            "metadata": {
                "location": "Building A - Main Entrance",
                "security_level": "high",
                "escalation_required": True,
                "notification_channels": ["email", "sms", "dashboard"]
            },
            "timeout": 300,
            "retry_count": 2
        }
    },
    {
        "summary": "Scheduled Video Analysis Task",
        "description": "Routine analysis task for daily surveillance footage review",
        "value": {
            "type": "ANALYSIS",
            "priority": "NORMAL",
            "description": "Daily surveillance footage analysis for zone B parking area",
            "data": {
                "analysis_type": "daily_review",
                "date_range": {
                    "start": "2024-01-14T00:00:00Z",
                    "end": "2024-01-15T00:00:00Z"
                },
                "cameras": ["CAM-005", "CAM-006", "CAM-007"],
                "focus_areas": [
                    "vehicle_counting",
                    "parking_violations",
                    "unusual_activity_detection"
                ],
                "output_format": "summary_report",
                "include_snapshots": True
            },
            "required_capabilities": [
                "video_analysis", 
                "vehicle_detection",
                "pattern_recognition"
            ],
            "metadata": {
                "scheduled_task": True,
                "report_delivery": ["email", "dashboard"],
                "retention_period": "30_days"
            },
            "timeout": 1800,
            "retry_count": 1
        }
    },
    {
        "summary": "Real-time Alert Generation",
        "description": "Immediate alert generation task for critical security events",
        "value": {
            "type": "ALERT",
            "priority": "EMERGENCY",
            "description": "Generate immediate alerts for fire detection in server room",
            "data": {
                "alert_type": "fire_detection",
                "location": "Server Room B-101",
                "sensors": [
                    {
                        "sensor_id": "SMOKE-001",
                        "reading": 0.95,
                        "threshold": 0.80,
                        "status": "alarm"
                    },
                    {
                        "sensor_id": "TEMP-001", 
                        "reading": 85.2,
                        "threshold": 75.0,
                        "status": "warning"
                    }
                ],
                "camera_verification": {
                    "camera_id": "CAM-SERVER-001",
                    "visual_confirmation_required": True
                },
                "escalation_chain": [
                    "security_team",
                    "fire_department", 
                    "building_management"
                ]
            },
            "required_capabilities": [
                "alert_generation",
                "escalation_management",
                "emergency_protocols"
            ],
            "metadata": {
                "emergency_level": "critical",
                "auto_escalate": True,
                "response_time_target": 60
            },
            "timeout": 30,
            "retry_count": 3
        }
    }
]

ORCHESTRATION_REQUEST_EXAMPLES = [
    {
        "summary": "Security Incident Orchestration",
        "description": "Complete orchestration workflow for a detected security incident",
        "value": {
            "event_data": {
                "incident_id": "SEC-2024-001234",
                "camera_id": "CAM-001",
                "timestamp": "2024-01-15T14:30:45Z",
                "event_type": "unauthorized_access",
                "location": {
                    "zone": "restricted_area_alpha",
                    "coordinates": {"x": 150, "y": 200},
                    "floor": 2,
                    "building": "HQ-Main"
                },
                "detection_details": {
                    "confidence": 0.92,
                    "person_count": 1,
                    "access_method": "badge_clone_suspected",
                    "duration": 45
                },
                "context": {
                    "previous_incidents": 2,
                    "risk_level": "high",
                    "business_hours": False
                }
            },
            "query": "Analyze unauthorized access in restricted area - determine threat level and response actions",
            "notification_channels": ["email", "sms", "dashboard", "mobile_app"],
            "recipients": [
                "security@company.com",
                "cso@company.com", 
                "+1-555-123-4567"
            ],
            "priority": "high",
            "response_timeout": 60,
            "escalation_enabled": True
        }
    },
    {
        "summary": "Routine Monitoring Orchestration", 
        "description": "Standard monitoring workflow for regular surveillance activities",
        "value": {
            "event_data": {
                "monitoring_session": "MON-2024-DAILY-001",
                "camera_group": "perimeter_cameras",
                "timestamp": "2024-01-15T09:00:00Z",
                "session_type": "scheduled_monitoring",
                "duration": 3600,
                "cameras": ["CAM-001", "CAM-002", "CAM-003", "CAM-004"],
                "monitoring_parameters": {
                    "detection_sensitivity": 0.75,
                    "motion_threshold": 0.80,
                    "analysis_interval": 300
                }
            },
            "query": "Perform routine perimeter monitoring and generate activity summary",
            "notification_channels": ["dashboard"],
            "recipients": ["operations@company.com"],
            "priority": "normal",
            "response_timeout": 300,
            "escalation_enabled": False
        }
    }
]

# Enhanced Response Examples
CIRCUIT_BREAKER_HEALTH_EXAMPLES = {
    "healthy_system": {
        "summary": "All services healthy",
        "description": "Example response when all circuit breakers are closed and services are operating normally",
        "value": {
            "orchestrator_status": "healthy",
            "redis_connected": True,
            "http_client_ready": True,
            "background_task_running": True,
            "circuit_breakers": {
                "services": {
                    "rag_service": {
                        "service_name": "rag_service", 
                        "service_type": "rag_service",
                        "circuit_breaker_state": "closed",
                        "fail_counter": 0,
                        "last_failure_time": None,
                        "last_success_time": "2024-01-15T14:30:45Z",
                        "configuration": {
                            "fail_max": 5,
                            "recovery_timeout": 60,
                            "timeout": 30.0,
                            "fallback_enabled": True,
                            "priority": 1
                        },
                        "performance_metrics": {
                            "success_rate": 0.998,
                            "average_response_time": 0.342,
                            "p95_response_time": 0.578,
                            "requests_per_minute": 45
                        }
                    },
                    "rulegen_service": {
                        "service_name": "rulegen_service",
                        "service_type": "rulegen_service", 
                        "circuit_breaker_state": "closed",
                        "fail_counter": 0,
                        "last_failure_time": None,
                        "last_success_time": "2024-01-15T14:30:42Z",
                        "configuration": {
                            "fail_max": 3,
                            "recovery_timeout": 45,
                            "timeout": 20.0,
                            "fallback_enabled": True,
                            "priority": 2
                        },
                        "performance_metrics": {
                            "success_rate": 0.995,
                            "average_response_time": 0.158,
                            "p95_response_time": 0.289,
                            "requests_per_minute": 32
                        }
                    },
                    "notifier_service": {
                        "service_name": "notifier_service",
                        "service_type": "notifier_service",
                        "circuit_breaker_state": "closed", 
                        "fail_counter": 0,
                        "last_failure_time": None,
                        "last_success_time": "2024-01-15T14:30:40Z",
                        "configuration": {
                            "fail_max": 4,
                            "recovery_timeout": 30,
                            "timeout": 15.0,
                            "fallback_enabled": True,
                            "priority": 1
                        },
                        "performance_metrics": {
                            "success_rate": 0.992,
                            "average_response_time": 0.089,
                            "p95_response_time": 0.156,
                            "requests_per_minute": 18
                        }
                    }
                },
                "total_services": 3,
                "timestamp": "2024-01-15T14:30:45Z"
            },
            "timestamp": "2024-01-15T14:30:45Z"
        }
    },
    "degraded_system": {
        "summary": "Some services experiencing issues",
        "description": "Example response when some circuit breakers are open due to service failures",
        "value": {
            "orchestrator_status": "degraded",
            "redis_connected": True,
            "http_client_ready": True,
            "background_task_running": True,
            "circuit_breakers": {
                "services": {
                    "rag_service": {
                        "service_name": "rag_service",
                        "service_type": "rag_service",
                        "circuit_breaker_state": "open",
                        "fail_counter": 7,
                        "last_failure_time": "2024-01-15T14:29:30Z",
                        "last_success_time": "2024-01-15T14:25:15Z",
                        "configuration": {
                            "fail_max": 5,
                            "recovery_timeout": 60,
                            "timeout": 30.0,
                            "fallback_enabled": True,
                            "priority": 1
                        },
                        "performance_metrics": {
                            "success_rate": 0.845,
                            "average_response_time": 1.205,
                            "p95_response_time": 2.340,
                            "requests_per_minute": 0
                        },
                        "failure_details": {
                            "error_type": "TimeoutError",
                            "error_message": "Service response timeout after 30 seconds",
                            "consecutive_failures": 7
                        }
                    },
                    "rulegen_service": {
                        "service_name": "rulegen_service",
                        "service_type": "rulegen_service",
                        "circuit_breaker_state": "half_open",
                        "fail_counter": 3,
                        "last_failure_time": "2024-01-15T14:28:45Z", 
                        "last_success_time": "2024-01-15T14:30:35Z",
                        "configuration": {
                            "fail_max": 3,
                            "recovery_timeout": 45,
                            "timeout": 20.0,
                            "fallback_enabled": True,
                            "priority": 2
                        },
                        "performance_metrics": {
                            "success_rate": 0.915,
                            "average_response_time": 0.295,
                            "p95_response_time": 0.468,
                            "requests_per_minute": 15
                        }
                    },
                    "notifier_service": {
                        "service_name": "notifier_service",
                        "service_type": "notifier_service",
                        "circuit_breaker_state": "closed",
                        "fail_counter": 1,
                        "last_failure_time": "2024-01-15T14:27:20Z",
                        "last_success_time": "2024-01-15T14:30:40Z",
                        "configuration": {
                            "fail_max": 4,
                            "recovery_timeout": 30,
                            "timeout": 15.0,
                            "fallback_enabled": True,
                            "priority": 1
                        },
                        "performance_metrics": {
                            "success_rate": 0.978,
                            "average_response_time": 0.112,
                            "p95_response_time": 0.198,
                            "requests_per_minute": 18
                        }
                    }
                },
                "total_services": 3,
                "timestamp": "2024-01-15T14:30:45Z"
            },
            "timestamp": "2024-01-15T14:30:45Z"
        }
    }
}

# Error Response Examples
ERROR_RESPONSE_EXAMPLES = {
    "validation_error": {
        "summary": "Request validation failed",
        "description": "Example of validation error response with detailed field-level errors",
        "value": {
            "status": "validation_error",
            "message": "Request validation failed",
            "errors": [
                {
                    "field": "event_data.camera_id",
                    "message": "Camera ID must be a valid format (CAM-XXX)",
                    "input_value": "invalid_camera",
                    "error_type": "format_error"
                },
                {
                    "field": "recipients",
                    "message": "At least one recipient must be provided for notifications",
                    "input_value": [],
                    "error_type": "value_error"
                }
            ],
            "request_id": "req_550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2024-01-15T14:30:45Z"
        }
    },
    "security_error": {
        "summary": "Security validation failed",
        "description": "Example of security error when suspicious content is detected",
        "value": {
            "status": "security_error",
            "message": "Suspicious content detected in request",
            "details": {
                "violation_type": "sql_injection_attempt",
                "blocked_field": "query",
                "client_ip": "192.168.1.100",
                "action_taken": "request_blocked"
            },
            "request_id": "req_550e8400-e29b-41d4-a716-446655440001",
            "timestamp": "2024-01-15T14:30:45Z"
        }
    },
    "rate_limit_error": {
        "summary": "Rate limit exceeded",
        "description": "Example of rate limiting error response",
        "value": {
            "status": "rate_limit_exceeded",
            "message": "Too many requests - rate limit exceeded",
            "details": {
                "limit": 100,
                "window": "1 minute",
                "current_count": 101,
                "reset_time": "2024-01-15T14:31:00Z"
            },
            "request_id": "req_550e8400-e29b-41d4-a716-446655440002",
            "timestamp": "2024-01-15T14:30:45Z"
        }
    }
}

# Response Status Documentation
HTTP_STATUS_DOCUMENTATION = {
    200: "Request completed successfully with all services responding normally",
    201: "Resource created successfully with validation and persistence completed",
    202: "Request accepted but processing is asynchronous or using fallback mechanisms",
    400: "Bad request - validation failed or malformed input data",
    401: "Unauthorized - authentication required or invalid credentials",
    403: "Forbidden - insufficient permissions for requested operation", 
    404: "Resource not found - requested item does not exist",
    409: "Conflict - resource already exists or state conflict",
    422: "Unprocessable entity - request syntax is correct but semantically invalid",
    429: "Too many requests - rate limit exceeded",
    500: "Internal server error - unexpected system failure",
    502: "Bad gateway - upstream service communication failure", 
    503: "Service unavailable - system overloaded or in maintenance mode",
    504: "Gateway timeout - upstream service response timeout"
}

# OpenAPI Tag Definitions
OPENAPI_TAGS = [
    {
        "name": "Agent Management",
        "description": "Operations for registering, listing, and managing AI agents in the surveillance network. Includes agent health monitoring, capability management, and lifecycle operations.",
        "externalDocs": {
            "description": "Agent Management Guide",
            "url": "https://docs.surveillance-system.example.com/agents",
        },
    },
    {
        "name": "Task Operations", 
        "description": "Task creation, assignment, monitoring, and lifecycle management operations. Supports various task types including analysis, detection, classification, and alerting with priority-based processing.",
        "externalDocs": {
            "description": "Task Management Documentation",
            "url": "https://docs.surveillance-system.example.com/tasks",
        },
    },
    {
        "name": "Workflow Orchestration",
        "description": "Complex workflow creation and execution with multi-agent coordination. Enables design and execution of sophisticated surveillance workflows with dependency management and parallel processing.",
        "externalDocs": {
            "description": "Workflow Design Patterns",
            "url": "https://docs.surveillance-system.example.com/workflows",
        },
    },
    {
        "name": "Enhanced Orchestration",
        "description": "Advanced orchestration features with circuit breaker protection and intelligent service coordination. Provides resilient multi-service workflows with automatic failover and fallback mechanisms.",
        "externalDocs": {
            "description": "Advanced Orchestration Guide",
            "url": "https://docs.surveillance-system.example.com/advanced-orchestration",
        },
    },
    {
        "name": "System Monitoring",
        "description": "Health checks, metrics, and system status monitoring endpoints. Comprehensive observability features for monitoring system health, performance metrics, and operational status.",
        "externalDocs": {
            "description": "Monitoring and Observability",
            "url": "https://docs.surveillance-system.example.com/monitoring",
        },
    },
    {
        "name": "Circuit Breaker Management",
        "description": "Circuit breaker status monitoring and administrative control operations. Advanced resilience features for managing service failures and maintaining system stability during outages.",
        "externalDocs": {
            "description": "Circuit Breaker Patterns",
            "url": "https://docs.surveillance-system.example.com/circuit-breakers",
        },
    },
]
