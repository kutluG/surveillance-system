"""
Interactive Rule Builder Service

This service provides an enhanced, interactive rule creation experience with:
- Step-by-step guided rule creation
- Intelligent suggestions and auto-completion
- Rule validation and conflict detection
- Template library with customization options
- Performance analytics and optimization recommendations
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import re

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import redis.asyncio as redis
import httpx
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = AsyncOpenAI(
    api_key="your-openai-api-key"  # Replace with actual key
)

# Enums
class RuleType(str, Enum):
    DETECTION = "detection"
    ALERT = "alert"
    AUTOMATION = "automation"
    THRESHOLD = "threshold"
    PATTERN = "pattern"

class ConditionOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    MATCHES = "matches"
    IN_RANGE = "in_range"

class RuleStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"

# Data Models
@dataclass
class RuleCondition:
    field: str
    operator: ConditionOperator
    value: Any
    description: str = ""

@dataclass
class RuleAction:
    type: str
    parameters: Dict[str, Any]
    description: str = ""

@dataclass
class Rule:
    id: str
    name: str
    description: str
    type: RuleType
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    status: RuleStatus
    priority: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    tags: List[str]
    performance_metrics: Dict[str, Any]

@dataclass
class RuleTemplate:
    id: str
    name: str
    description: str
    category: str
    type: RuleType
    template_conditions: List[Dict]
    template_actions: List[Dict]
    customizable_fields: List[str]
    use_count: int = 0

# Request/Response Models
class BuildStepRequest(BaseModel):
    session_id: str
    step: str
    user_input: str
    context: dict = {}

class RuleValidationRequest(BaseModel):
    rule_data: dict
    check_conflicts: bool = True

class TemplateCustomizationRequest(BaseModel):
    template_id: str
    customizations: dict
    session_id: str

class RuleSuggestionRequest(BaseModel):
    partial_rule: dict
    context: dict = {}

# Global state
redis_client: Optional[redis.Redis] = None

async def get_redis_client():
    """Get Redis client"""
    global redis_client
    if not redis_client:
        redis_client = redis.from_url("redis://localhost:6379/6")
    return redis_client

# Rule Templates Database
RULE_TEMPLATES = {
    "motion_detection": RuleTemplate(
        id="motion_detection",
        name="Motion Detection Alert",
        description="Detect motion in specified areas and send alerts",
        category="Security",
        type=RuleType.DETECTION,
        template_conditions=[
            {"field": "event_type", "operator": "equals", "value": "motion_detected"},
            {"field": "location", "operator": "in_range", "value": "{customizable}"},
            {"field": "confidence", "operator": "greater_than", "value": "{customizable}"}
        ],
        template_actions=[
            {"type": "send_alert", "parameters": {"channel": "{customizable}", "priority": "medium"}},
            {"type": "record_clip", "parameters": {"duration": 30}}
        ],
        customizable_fields=["location", "confidence", "alert_channel"]
    ),
    "unauthorized_access": RuleTemplate(
        id="unauthorized_access",
        name="Unauthorized Access Detection",
        description="Detect unauthorized personnel in restricted areas",
        category="Access Control",
        type=RuleType.DETECTION,
        template_conditions=[
            {"field": "person_detected", "operator": "equals", "value": True},
            {"field": "area_type", "operator": "equals", "value": "restricted"},
            {"field": "authorized_personnel", "operator": "not_equals", "value": True}
        ],
        template_actions=[
            {"type": "send_alert", "parameters": {"priority": "high", "escalate": True}},
            {"type": "trigger_alarm", "parameters": {"type": "security_breach"}}
        ],
        customizable_fields=["area_type", "escalation_rules"]
    ),
    "vehicle_counting": RuleTemplate(
        id="vehicle_counting",
        name="Vehicle Counting Rule",
        description="Count vehicles in designated areas with threshold alerts",
        category="Traffic",
        type=RuleType.THRESHOLD,
        template_conditions=[
            {"field": "object_type", "operator": "equals", "value": "vehicle"},
            {"field": "zone", "operator": "equals", "value": "{customizable}"},
            {"field": "count", "operator": "greater_than", "value": "{customizable}"}
        ],
        template_actions=[
            {"type": "log_event", "parameters": {"category": "traffic"}},
            {"type": "send_notification", "parameters": {"type": "threshold_exceeded"}}
        ],
        customizable_fields=["zone", "threshold_count", "notification_type"]
    )
}

# Rule Builder Engine
class RuleBuilderEngine:
    def __init__(self):
        self.build_sessions = {}
    
    async def start_build_session(self, user_id: str) -> str:
        """Start a new rule building session"""
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "current_step": "intent",
            "rule_data": {},
            "context": {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        redis_client = await get_redis_client()
        await redis_client.setex(
            f"rule_session:{session_id}",
            3600,  # 1 hour expiry
            json.dumps(session_data, default=str)
        )
        
        return session_id
    
    async def get_session(self, session_id: str) -> Dict:
        """Get session data"""
        redis_client = await get_redis_client()
        session_data = await redis_client.get(f"rule_session:{session_id}")
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        return json.loads(session_data)
    
    async def update_session(self, session_id: str, updates: Dict):
        """Update session data"""
        session_data = await self.get_session(session_id)
        session_data.update(updates)
        
        redis_client = await get_redis_client()
        await redis_client.setex(
            f"rule_session:{session_id}",
            3600,
            json.dumps(session_data, default=str)
        )
    
    async def process_build_step(self, request: BuildStepRequest) -> Dict:
        """Process a step in the rule building process"""
        session_data = await self.get_session(request.session_id)
        current_step = session_data["current_step"]
        
        if current_step == "intent":
            return await self._process_intent_step(request, session_data)
        elif current_step == "conditions":
            return await self._process_conditions_step(request, session_data)
        elif current_step == "actions":
            return await self._process_actions_step(request, session_data)
        elif current_step == "review":
            return await self._process_review_step(request, session_data)
        else:
            raise HTTPException(status_code=400, detail="Invalid step")
    
    async def _process_intent_step(self, request: BuildStepRequest, session_data: Dict) -> Dict:
        """Process intent understanding step"""
        user_input = request.user_input
        
        # Use LLM to understand user intent
        intent_prompt = f"""
        Analyze the following user input for rule creation intent:
        
        User Input: "{user_input}"
        
        Determine:
        1. Rule type (detection, alert, automation, threshold, pattern)
        2. What they want to monitor/detect
        3. What actions they want to take
        4. Any specific conditions mentioned
        
        Respond in JSON format:
        {{
            "rule_type": "detection|alert|automation|threshold|pattern",
            "intent_summary": "brief description",
            "suggested_name": "suggested rule name",
            "detected_conditions": ["list", "of", "conditions"],
            "detected_actions": ["list", "of", "actions"],
            "confidence": 0.8,
            "next_questions": ["clarifying", "questions"]
        }}
        """
        
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": intent_prompt}],
                temperature=0.3
            )
            
            intent_analysis = json.loads(response.choices[0].message.content)
            
            # Update session
            session_data["rule_data"].update({
                "type": intent_analysis.get("rule_type"),
                "name": intent_analysis.get("suggested_name"),
                "description": intent_analysis.get("intent_summary")
            })
            session_data["context"]["intent_analysis"] = intent_analysis
            session_data["current_step"] = "conditions"
            
            await self.update_session(request.session_id, session_data)
            
            return {
                "step": "conditions",
                "message": f"I understand you want to create a {intent_analysis.get('rule_type')} rule for: {intent_analysis.get('intent_summary')}",
                "suggested_name": intent_analysis.get("suggested_name"),
                "next_questions": intent_analysis.get("next_questions", []),
                "suggestions": await self._get_condition_suggestions(intent_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error processing intent: {e}")
            return {
                "step": "intent",
                "message": "I had trouble understanding your request. Could you please describe what you want to monitor and what actions to take?",
                "error": "intent_analysis_failed"
            }
    
    async def _process_conditions_step(self, request: BuildStepRequest, session_data: Dict) -> Dict:
        """Process conditions definition step"""
        user_input = request.user_input
        existing_conditions = session_data["rule_data"].get("conditions", [])
        
        # Parse condition from user input
        condition_prompt = f"""
        Parse the following condition for a surveillance rule:
        
        User Input: "{user_input}"
        Existing Conditions: {existing_conditions}
        
        Extract:
        1. Field being checked (e.g., event_type, location, confidence, object_type)
        2. Operator (equals, not_equals, greater_than, less_than, contains, matches, in_range)
        3. Value to compare against
        
        Respond in JSON format:
        {{
            "condition": {{
                "field": "field_name",
                "operator": "operator",
                "value": "value",
                "description": "human readable description"
            }},
            "is_valid": true,
            "suggestions": ["alternative", "conditions"],
            "next_step": "add_more_conditions|proceed_to_actions"
        }}
        """
        
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": condition_prompt}],
                temperature=0.3
            )
            
            condition_analysis = json.loads(response.choices[0].message.content)
            
            if condition_analysis.get("is_valid"):
                # Add condition to rule
                if "conditions" not in session_data["rule_data"]:
                    session_data["rule_data"]["conditions"] = []
                
                session_data["rule_data"]["conditions"].append(condition_analysis["condition"])
                
                if condition_analysis.get("next_step") == "proceed_to_actions":
                    session_data["current_step"] = "actions"
                    message = "Great! Now let's define what actions to take when these conditions are met."
                else:
                    message = f"Added condition: {condition_analysis['condition']['description']}. Add another condition or say 'proceed to actions'."
            else:
                message = "I couldn't understand that condition. Please try again with a clearer description."
            
            await self.update_session(request.session_id, session_data)
            
            return {
                "step": session_data["current_step"],
                "message": message,
                "current_conditions": session_data["rule_data"].get("conditions", []),
                "suggestions": condition_analysis.get("suggestions", [])
            }
            
        except Exception as e:
            logger.error(f"Error processing condition: {e}")
            return {
                "step": "conditions",
                "message": "I had trouble parsing that condition. Please describe what you want to check (e.g., 'motion detected in parking lot').",
                "error": "condition_parse_failed"
            }
    
    async def _process_actions_step(self, request: BuildStepRequest, session_data: Dict) -> Dict:
        """Process actions definition step"""
        user_input = request.user_input
        existing_actions = session_data["rule_data"].get("actions", [])
        
        # Parse action from user input
        action_prompt = f"""
        Parse the following action for a surveillance rule:
        
        User Input: "{user_input}"
        Existing Actions: {existing_actions}
        
        Extract:
        1. Action type (send_alert, record_clip, trigger_alarm, send_notification, log_event)
        2. Parameters for the action
        
        Respond in JSON format:
        {{
            "action": {{
                "type": "action_type",
                "parameters": {{"param1": "value1"}},
                "description": "human readable description"
            }},
            "is_valid": true,
            "suggestions": ["alternative", "actions"],
            "next_step": "add_more_actions|proceed_to_review"
        }}
        """
        
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": action_prompt}],
                temperature=0.3
            )
            
            action_analysis = json.loads(response.choices[0].message.content)
            
            if action_analysis.get("is_valid"):
                # Add action to rule
                if "actions" not in session_data["rule_data"]:
                    session_data["rule_data"]["actions"] = []
                
                session_data["rule_data"]["actions"].append(action_analysis["action"])
                
                if action_analysis.get("next_step") == "proceed_to_review":
                    session_data["current_step"] = "review"
                    message = "Perfect! Let's review your rule before finalizing."
                else:
                    message = f"Added action: {action_analysis['action']['description']}. Add another action or say 'review rule'."
            else:
                message = "I couldn't understand that action. Please try again."
            
            await self.update_session(request.session_id, session_data)
            
            return {
                "step": session_data["current_step"],
                "message": message,
                "current_actions": session_data["rule_data"].get("actions", []),
                "suggestions": action_analysis.get("suggestions", [])
            }
            
        except Exception as e:
            logger.error(f"Error processing action: {e}")
            return {
                "step": "actions",
                "message": "I had trouble parsing that action. Please describe what should happen (e.g., 'send high priority alert').",
                "error": "action_parse_failed"
            }
    
    async def _process_review_step(self, request: BuildStepRequest, session_data: Dict) -> Dict:
        """Process rule review and finalization step"""
        user_input = request.user_input.lower()
        
        if "approve" in user_input or "looks good" in user_input or "create" in user_input:
            # Finalize the rule
            rule_data = session_data["rule_data"]
            rule_id = str(uuid.uuid4())
            
            # Create complete rule
            rule = {
                "id": rule_id,
                "name": rule_data.get("name", "Untitled Rule"),
                "description": rule_data.get("description", ""),
                "type": rule_data.get("type", "detection"),
                "conditions": rule_data.get("conditions", []),
                "actions": rule_data.get("actions", []),
                "status": "draft",
                "priority": 1,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": session_data["user_id"],
                "tags": []
            }
            
            # Store rule
            redis_client = await get_redis_client()
            await redis_client.hset("rules", rule_id, json.dumps(rule))
            
            return {
                "step": "completed",
                "message": f"Rule '{rule['name']}' has been created successfully!",
                "rule_id": rule_id,
                "rule": rule
            }
        else:
            # Show rule summary for review
            rule_data = session_data["rule_data"]
            return {
                "step": "review",
                "message": "Please review your rule. Say 'approve' to create it or suggest changes.",
                "rule_summary": {
                    "name": rule_data.get("name"),
                    "description": rule_data.get("description"),
                    "conditions": rule_data.get("conditions", []),
                    "actions": rule_data.get("actions", [])
                }
            }
    
    async def _get_condition_suggestions(self, intent_analysis: Dict) -> List[str]:
        """Get condition suggestions based on intent analysis"""
        rule_type = intent_analysis.get("rule_type")
        
        suggestions = []
        if rule_type == "detection":
            suggestions = [
                "event_type equals motion_detected",
                "confidence greater_than 0.8",
                "location contains parking_lot",
                "time_of_day in_range 18:00-06:00"
            ]
        elif rule_type == "threshold":
            suggestions = [
                "count greater_than 10",
                "duration greater_than 30",
                "frequency greater_than 5"
            ]
        
        return suggestions

# Rule Validator
class RuleValidator:
    @staticmethod
    async def validate_rule(rule_data: Dict, check_conflicts: bool = True) -> Dict:
        """Validate rule and check for conflicts"""
        issues = []
        warnings = []
        
        # Basic validation
        if not rule_data.get("name"):
            issues.append("Rule name is required")
        
        if not rule_data.get("conditions"):
            issues.append("At least one condition is required")
        
        if not rule_data.get("actions"):
            issues.append("At least one action is required")
        
        # Validate conditions
        for condition in rule_data.get("conditions", []):
            if not all(key in condition for key in ["field", "operator", "value"]):
                issues.append("Invalid condition format")
        
        # Check for conflicts if requested
        conflicts = []
        if check_conflicts:
            conflicts = await RuleValidator._check_rule_conflicts(rule_data)
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "conflicts": conflicts,
            "suggestions": await RuleValidator._get_optimization_suggestions(rule_data)
        }
    
    @staticmethod
    async def _check_rule_conflicts(rule_data: Dict) -> List[Dict]:
        """Check for conflicts with existing rules"""
        # This would check against existing rules in the database
        # For now, return empty list
        return []
    
    @staticmethod
    async def _get_optimization_suggestions(rule_data: Dict) -> List[str]:
        """Get optimization suggestions for the rule"""
        suggestions = []
        
        # Check for overly broad conditions
        conditions = rule_data.get("conditions", [])
        if len(conditions) < 2:
            suggestions.append("Consider adding more specific conditions to reduce false positives")
        
        # Check for missing priority
        if not rule_data.get("priority"):
            suggestions.append("Set a priority level for better rule execution order")
        
        return suggestions

# Initialize rule builder
rule_builder = RuleBuilderEngine()

# FastAPI App
app = FastAPI(
    title="Interactive Rule Builder",
    description="Enhanced rule creation with guided assistance",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.post("/build/start")
async def start_rule_building(user_id: str):
    """Start a new rule building session"""
    try:
        session_id = await rule_builder.start_build_session(user_id)
        return {
            "session_id": session_id,
            "message": "Let's create a new rule! What would you like to monitor or detect?",
            "step": "intent"
        }
    except Exception as e:
        logger.error(f"Error starting build session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/build/step")
async def process_build_step(request: BuildStepRequest):
    """Process a step in the rule building process"""
    try:
        result = await rule_builder.process_build_step(request)
        return result
    except Exception as e:
        logger.error(f"Error processing build step: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/build/session/{session_id}")
async def get_build_session(session_id: str):
    """Get current session state"""
    try:
        session_data = await rule_builder.get_session(session_id)
        return session_data
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates")
async def list_templates(category: Optional[str] = None):
    """List available rule templates"""
    templates = []
    for template in RULE_TEMPLATES.values():
        if category and template.category.lower() != category.lower():
            continue
        templates.append(asdict(template))
    
    return {"templates": templates}

@app.post("/templates/{template_id}/customize")
async def customize_template(template_id: str, request: TemplateCustomizationRequest):
    """Customize a rule template"""
    if template_id not in RULE_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = RULE_TEMPLATES[template_id]
    
    # Apply customizations
    customized_rule = {
        "name": request.customizations.get("name", template.name),
        "description": template.description,
        "type": template.type,
        "conditions": [],
        "actions": []
    }
    
    # Process template conditions with customizations
    for condition_template in template.template_conditions:
        condition = condition_template.copy()
        if condition["value"] == "{customizable}":
            field_name = condition["field"]
            if field_name in request.customizations:
                condition["value"] = request.customizations[field_name]
        customized_rule["conditions"].append(condition)
    
    # Process template actions with customizations
    for action_template in template.template_actions:
        action = action_template.copy()
        for param_key, param_value in action["parameters"].items():
            if param_value == "{customizable}":
                if param_key in request.customizations:
                    action["parameters"][param_key] = request.customizations[param_key]
        customized_rule["actions"].append(action)
    
    return {
        "customized_rule": customized_rule,
        "session_id": request.session_id
    }

@app.post("/validate")
async def validate_rule(request: RuleValidationRequest):
    """Validate a rule"""
    try:
        validation_result = await RuleValidator.validate_rule(
            request.rule_data, 
            request.check_conflicts
        )
        return validation_result
    except Exception as e:
        logger.error(f"Error validating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/suggestions")
async def get_rule_suggestions(request: RuleSuggestionRequest):
    """Get intelligent suggestions for rule completion"""
    try:
        suggestion_prompt = f"""
        Analyze this partial rule and provide intelligent suggestions:
        
        Partial Rule: {json.dumps(request.partial_rule, indent=2)}
        Context: {json.dumps(request.context, indent=2)}
        
        Provide suggestions for:
        1. Missing conditions
        2. Recommended actions
        3. Optimization opportunities
        4. Similar rule templates
        
        Respond in JSON format:
        {{
            "missing_conditions": ["list of suggested conditions"],
            "recommended_actions": ["list of suggested actions"],
            "optimizations": ["list of optimization suggestions"],
            "similar_templates": ["list of template IDs"]
        }}
        """
        
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": suggestion_prompt}],
            temperature=0.3
        )
        
        suggestions = json.loads(response.choices[0].message.content)
        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
