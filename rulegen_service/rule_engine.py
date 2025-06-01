"""
Rule evaluation engine that checks events against stored policy rules.
"""
import json
from datetime import datetime, time
from typing import List, Dict, Any
from shared.models import CameraEvent

def evaluate_condition(condition: Dict[str, Any], event: CameraEvent) -> bool:
    """
    Evaluate a single condition against a camera event.
    """
    field = condition["field"]
    operator = condition["operator"]
    value = condition["value"]
    
    # Extract field value from event
    if field == "event_type":
        event_value = event.event_type.value
    elif field == "camera_id":
        event_value = event.camera_id
    elif field == "detection_label":
        if not event.detections:
            return False
        event_value = [d.label for d in event.detections]
    elif field == "time_of_day":
        event_value = event.timestamp.time()
    else:
        # Check metadata for custom fields
        event_value = event.metadata.get(field) if event.metadata else None
    
    # Apply operator
    if operator == "equals":
        return event_value == value
    elif operator == "contains":
        if isinstance(event_value, list):
            return value in event_value
        return value in str(event_value)
    elif operator == "greater_than":
        return event_value > value
    elif operator == "less_than":
        return event_value < value
    elif operator == "between" and field == "time_of_day":
        start_time = time.fromisoformat(value[0])
        end_time = time.fromisoformat(value[1])
        if start_time <= end_time:
            return start_time <= event_value <= end_time
        else:  # Crosses midnight
            return event_value >= start_time or event_value <= end_time
    
    return False

def evaluate_rule(rule_conditions: List[Dict[str, Any]], event: CameraEvent) -> bool:
    """
    Evaluate all conditions in a rule against an event (AND logic).
    """
    return all(evaluate_condition(condition, event) for condition in rule_conditions)

def get_triggered_actions(event: CameraEvent, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get all actions that should be triggered for an event based on active rules.
    """
    triggered_actions = []
    
    for rule in rules:
        if not rule.get("is_active", True):
            continue
            
        conditions = json.loads(rule["conditions"])
        actions = json.loads(rule["actions"])
        
        if evaluate_rule(conditions, event):
            for action in actions:
                action["rule_id"] = rule["id"]
                action["rule_name"] = rule["name"]
                triggered_actions.append(action)
    
    return triggered_actions