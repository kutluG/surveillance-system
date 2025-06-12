"""
Rule Generation Service: manages policy rules and evaluates events against them.
"""
import json
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.auth import get_current_user, TokenData
from shared.models import CameraEvent
from shared.middleware import add_rate_limiting

from database import SessionLocal, engine
from models import Base, PolicyRule
from llm_client import generate_rule_structure
from rule_engine import get_triggered_actions
from rule_validator import RuleValidator, RuleTestHarness, ValidationResult

# Configure logging first
logger = configure_logging("rulegen_service")

app = FastAPI(
    title="Rule Generation Service",
    openapi_prefix="/api/v1"
)

# Add audit middleware
add_audit_middleware(app, service_name="rulegen_service")
instrument_app(app, service_name="rulegen_service")

# Add rate limiting middleware
add_rate_limiting(app, service_name="rulegen_service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RuleCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    rule_text: str  # Natural language description

class RuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    rule_text: str
    conditions: str
    actions: str
    is_active: bool
    created_at: str
    created_by: Optional[str]

class EvaluateRequest(BaseModel):
    event: dict  # CameraEvent as dict

class EvaluateResponse(BaseModel):
    triggered_actions: List[dict]

class RuleValidateRequest(BaseModel):
    rule_data: dict
    check_conflicts: bool = True

class RuleValidateResponse(BaseModel):
    is_valid: bool
    issues: List[dict]
    conflicts: List[dict]
    performance_warnings: List[str]
    optimization_suggestions: List[str]
    test_coverage: dict

class RuleTestRequest(BaseModel):
    rule_data: dict

class RuleTestResponse(BaseModel):
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    test_details: List[dict]
    coverage_score: float

@app.on_event("startup")
def startup_event():
    logger.info("Starting Rule Generation Service")
    Base.metadata.create_all(bind=engine)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/rules", response_model=RuleResponse)
async def create_rule(
    req: RuleCreateRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new policy rule from natural language description.
    Includes comprehensive validation and conflict detection.
    """
    logger.info("Creating rule", name=req.name, user=current_user.sub)
    
    try:
        # Generate structured rule from natural language
        rule_structure = generate_rule_structure(req.rule_text)
        
        # Prepare rule data for validation
        rule_data = {
            "name": req.name,
            "description": req.description,
            "rule_text": req.rule_text,
            "conditions": rule_structure["conditions"],
            "actions": rule_structure["actions"],
            "type": "detection",  # Default type
            "priority": 1
        }
        
        # Get existing rules for conflict detection
        existing_rules = db.query(PolicyRule).all()
        existing_rule_dicts = []
        for rule in existing_rules:
            existing_rule_dicts.append({
                "id": str(rule.id),
                "name": rule.name,
                "conditions": json.loads(rule.conditions),
                "actions": json.loads(rule.actions),
                "type": getattr(rule, 'type', 'detection'),
                "priority": getattr(rule, 'priority', 1)
            })
        
        # Comprehensive validation
        validator = RuleValidator(existing_rule_dicts)
        validation_result = await validator.validate_rule(rule_data, check_conflicts=True)
        
        # Check for critical errors
        if not validation_result.is_valid:
            error_messages = [issue.message for issue in validation_result.issues 
                            if issue.severity.value == "error"]
            logger.warning("Rule validation failed", errors=error_messages)
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "Rule validation failed",
                    "errors": error_messages,
                    "validation_result": {
                        "issues": [{"severity": issue.severity.value, "message": issue.message, 
                                  "suggestion": issue.suggestion} for issue in validation_result.issues],
                        "conflicts": [{"type": conflict.conflict_type.value, 
                                     "description": conflict.description,
                                     "suggestion": conflict.resolution_suggestion} 
                                    for conflict in validation_result.conflicts]
                    }
                }
            )
        
        # Log warnings but continue with creation
        if validation_result.conflicts or validation_result.performance_warnings:
            logger.warning("Rule has warnings", 
                         conflicts=len(validation_result.conflicts),
                         performance_warnings=len(validation_result.performance_warnings))
        
        # Create database record
        rule = PolicyRule(
            name=req.name,
            description=req.description,
            rule_text=req.rule_text,
            conditions=json.dumps(rule_structure["conditions"]),
            actions=json.dumps(rule_structure["actions"]),
            created_by=current_user.sub,
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        logger.info("Rule created successfully", 
                   rule_id=str(rule.id),
                   validation_warnings=len(validation_result.issues))
        
        return RuleResponse(
            id=str(rule.id),
            name=rule.name,
            description=rule.description,
            rule_text=rule.rule_text,
            conditions=rule.conditions,
            actions=rule.actions,
            is_active=rule.is_active,
            created_at=rule.created_at.isoformat(),
            created_by=rule.created_by,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create rule", error=str(e))
        raise HTTPException(status_code=500, detail="Rule generation failed")

@app.get("/api/v1/rules", response_model=List[RuleResponse])
async def list_rules(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all policy rules.
    """
    query = db.query(PolicyRule)
    if active_only:
        query = query.filter(PolicyRule.is_active == True)
    
    rules = query.all()
    
    return [
        RuleResponse(
            id=str(rule.id),
            name=rule.name,
            description=rule.description,
            rule_text=rule.rule_text,
            conditions=rule.conditions,
            actions=rule.actions,
            is_active=rule.is_active,
            created_at=rule.created_at.isoformat(),
            created_by=rule.created_by,
        )
        for rule in rules
    ]

@app.put("/api/v1/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate or deactivate a rule.
    """
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule.is_active = not rule.is_active
    db.commit()
    
    logger.info("Rule toggled", rule_id=rule_id, active=rule.is_active, user=current_user.sub)
    return {"id": rule_id, "is_active": rule.is_active}

@app.post("/api/v1/evaluate", response_model=EvaluateResponse)
async def evaluate_event(
    req: EvaluateRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate a camera event against all active rules.
    """
    try:
        # Parse event
        event = CameraEvent.parse_obj(req.event)
        
        # Get active rules
        rules = db.query(PolicyRule).filter(PolicyRule.is_active == True).all()
        rule_dicts = [
            {
                "id": str(rule.id),
                "name": rule.name,
                "conditions": rule.conditions,
                "actions": rule.actions,
                "is_active": rule.is_active,
            }
            for rule in rules
        ]
        
        # Evaluate rules
        triggered_actions = get_triggered_actions(event, rule_dicts)
        
        logger.info("Event evaluated", event_id=str(event.id), triggered_count=len(triggered_actions))
        
        return EvaluateResponse(triggered_actions=triggered_actions)
        
    except Exception as e:
        logger.error("Event evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Evaluation failed")

@app.delete("/api/v1/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a policy rule.
    """
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    
    logger.info("Rule deleted", rule_id=rule_id, user=current_user.sub)
    return {"message": "Rule deleted"}

@app.post("/api/v1/rules/validate", response_model=RuleValidateResponse)
async def validate_rule(
    req: RuleValidateRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a rule without creating it.
    Performs comprehensive validation including conflict detection.
    """
    logger.info("Validating rule", rule_name=req.rule_data.get("name", "unnamed"))
    
    try:
        # Get existing rules for conflict detection
        existing_rules = []
        if req.check_conflicts:
            existing_rule_records = db.query(PolicyRule).all()
            for rule in existing_rule_records:
                existing_rules.append({
                    "id": str(rule.id),
                    "name": rule.name,
                    "conditions": json.loads(rule.conditions),
                    "actions": json.loads(rule.actions),
                    "type": getattr(rule, 'type', 'detection'),
                    "priority": getattr(rule, 'priority', 1)
                })
        
        # Perform validation
        validator = RuleValidator(existing_rules)
        validation_result = await validator.validate_rule(req.rule_data, req.check_conflicts)
        
        logger.info("Rule validation completed", 
                   is_valid=validation_result.is_valid,
                   issues_count=len(validation_result.issues),
                   conflicts_count=len(validation_result.conflicts))
        
        return RuleValidateResponse(
            is_valid=validation_result.is_valid,
            issues=[{
                "severity": issue.severity.value,
                "message": issue.message,
                "rule_field": issue.rule_field,
                "suggestion": issue.suggestion
            } for issue in validation_result.issues],
            conflicts=[{
                "conflict_type": conflict.conflict_type.value,
                "conflicting_rule_id": conflict.conflicting_rule_id,
                "conflicting_rule_name": conflict.conflicting_rule_name,
                "description": conflict.description,
                "severity": conflict.severity.value,
                "resolution_suggestion": conflict.resolution_suggestion
            } for conflict in validation_result.conflicts],
            performance_warnings=validation_result.performance_warnings,
            optimization_suggestions=validation_result.optimization_suggestions,
            test_coverage=validation_result.test_coverage
        )
        
    except Exception as e:
        logger.error("Rule validation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Validation failed")

@app.post("/api/v1/rules/test", response_model=RuleTestResponse)
async def test_rule(req: RuleTestRequest):
    """
    Run comprehensive tests on a rule.
    Generates and executes test scenarios to verify rule behavior.
    """
    logger.info("Testing rule", rule_name=req.rule_data.get("name", "unnamed"))
    
    try:
        # Create test harness
        test_harness = RuleTestHarness(req.rule_data)
        
        # Run comprehensive tests
        test_results = await test_harness.run_comprehensive_tests()
        
        logger.info("Rule testing completed",
                   total_tests=test_results['total_tests'],
                   passed_tests=test_results['passed_tests'],
                   success_rate=test_results['success_rate'])
        
        return RuleTestResponse(
            total_tests=test_results['total_tests'],
            passed_tests=test_results['passed_tests'],
            failed_tests=test_results['failed_tests'],
            success_rate=test_results['success_rate'],
            test_details=test_results['test_details'],
            coverage_score=test_results['coverage_score']
        )
        
    except Exception as e:
        logger.error("Rule testing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Testing failed")

@app.get("/api/v1/rules/{rule_id}/conflicts")
async def check_rule_conflicts(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """
    Check for conflicts with a specific existing rule.
    """
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Convert rule to dict format
    rule_data = {
        "id": str(rule.id),
        "name": rule.name,
        "conditions": json.loads(rule.conditions),
        "actions": json.loads(rule.actions),
        "type": getattr(rule, 'type', 'detection'),
        "priority": getattr(rule, 'priority', 1)
    }
    
    # Get other rules for conflict detection
    other_rules = db.query(PolicyRule).filter(PolicyRule.id != rule_id).all()
    other_rule_dicts = []
    for other_rule in other_rules:
        other_rule_dicts.append({
            "id": str(other_rule.id),
            "name": other_rule.name,
            "conditions": json.loads(other_rule.conditions),
            "actions": json.loads(other_rule.actions),
            "type": getattr(other_rule, 'type', 'detection'),
            "priority": getattr(other_rule, 'priority', 1)
        })
    
    # Check for conflicts
    validator = RuleValidator(other_rule_dicts)
    validation_result = await validator.validate_rule(rule_data, check_conflicts=True)
    
    return {
        "rule_id": rule_id,
        "rule_name": rule.name,
        "conflicts": [{
            "conflict_type": conflict.conflict_type.value,
            "conflicting_rule_id": conflict.conflicting_rule_id,
            "conflicting_rule_name": conflict.conflicting_rule_name,
            "description": conflict.description,
            "severity": conflict.severity.value,
            "resolution_suggestion": conflict.resolution_suggestion
        } for conflict in validation_result.conflicts],
        "conflict_count": len(validation_result.conflicts)
    }

@app.get("/api/v1/rules/analytics/conflicts")
async def analyze_all_conflicts(db: Session = Depends(get_db)):
    """
    Analyze conflicts across all rules in the system.
    """
    logger.info("Analyzing system-wide rule conflicts")
    
    all_rules = db.query(PolicyRule).all()
    if len(all_rules) < 2:
        return {"message": "Not enough rules to analyze conflicts", "conflicts": []}
    
    # Convert all rules to dict format
    rule_dicts = []
    for rule in all_rules:
        rule_dicts.append({
            "id": str(rule.id),
            "name": rule.name,
            "conditions": json.loads(rule.conditions),
            "actions": json.loads(rule.actions),
            "type": getattr(rule, 'type', 'detection'),
            "priority": getattr(rule, 'priority', 1),
            "is_active": rule.is_active
        })
    
    # Find all conflicts
    all_conflicts = []
    validator = RuleValidator()
    
    for i, rule1 in enumerate(rule_dicts):
        for rule2 in rule_dicts[i+1:]:
            conflict = await validator._check_rule_pair_conflict(rule1, rule2)
            if conflict:
                all_conflicts.append({
                    "rule1_id": rule1["id"],
                    "rule1_name": rule1["name"],
                    "rule2_id": rule2["id"],
                    "rule2_name": rule2["name"],
                    "conflict_type": conflict.conflict_type.value,
                    "description": conflict.description,
                    "severity": conflict.severity.value,
                    "resolution_suggestion": conflict.resolution_suggestion
                })
    
    # Categorize conflicts by type
    conflict_summary = {}
    for conflict in all_conflicts:
        conflict_type = conflict["conflict_type"]
        if conflict_type not in conflict_summary:
            conflict_summary[conflict_type] = 0
        conflict_summary[conflict_type] += 1
    
    logger.info("Conflict analysis completed", total_conflicts=len(all_conflicts))
    
    return {
        "total_rules": len(rule_dicts),
        "total_conflicts": len(all_conflicts),
        "conflict_summary": conflict_summary,
        "conflicts": all_conflicts
    }
