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

from shared.logging import get_logger
from shared.metrics import instrument_app
from shared.auth import get_current_user, TokenData
from shared.models import CameraEvent

from rulegen_service.database import SessionLocal, engine
from rulegen_service.models import Base, PolicyRule
from rulegen_service.llm_client import generate_rule_structure
from rulegen_service.rule_engine import get_triggered_actions

LOGGER = get_logger("rulegen_service")
app = FastAPI(title="Rule Generation Service")
instrument_app(app, service_name="rulegen_service")

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

@app.on_event("startup")
def startup_event():
    LOGGER.info("Starting Rule Generation Service")
    Base.metadata.create_all(bind=engine)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/rules", response_model=RuleResponse)
async def create_rule(
    req: RuleCreateRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new policy rule from natural language description.
    """
    LOGGER.info("Creating rule", name=req.name, user=current_user.sub)
    
    try:
        # Generate structured rule from natural language
        rule_structure = generate_rule_structure(req.rule_text)
        
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
        
        LOGGER.info("Rule created", rule_id=str(rule.id))
        
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
        
    except Exception as e:
        LOGGER.error("Failed to create rule", error=str(e))
        raise HTTPException(status_code=500, detail="Rule generation failed")

@app.get("/rules", response_model=List[RuleResponse])
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

@app.put("/rules/{rule_id}/toggle")
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
    
    LOGGER.info("Rule toggled", rule_id=rule_id, active=rule.is_active, user=current_user.sub)
    return {"id": rule_id, "is_active": rule.is_active}

@app.post("/evaluate", response_model=EvaluateResponse)
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
        
        LOGGER.info("Event evaluated", event_id=str(event.id), triggered_count=len(triggered_actions))
        
        return EvaluateResponse(triggered_actions=triggered_actions)
        
    except Exception as e:
        LOGGER.error("Event evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Evaluation failed")

@app.delete("/rules/{rule_id}")
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
    
    LOGGER.info("Rule deleted", rule_id=rule_id, user=current_user.sub)
    return {"message": "Rule deleted"}