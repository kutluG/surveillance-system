import pytest
from datetime import datetime, time
from shared.models import CameraEvent, Detection, BoundingBox, EventType
from rulegen_service.rule_engine import evaluate_condition, evaluate_rule, get_triggered_actions

def sample_event():
    bbox = BoundingBox(x_min=0.1, y_min=0.2, x_max=0.5, y_max=0.8)
    detection = Detection(label="person", confidence=0.95, bounding_box=bbox)
    return CameraEvent(
        camera_id="restricted-area-01",
        event_type=EventType.DETECTION,
        detections=[detection],
        timestamp=datetime(2025, 5, 31, 2, 30, 0)  # 2:30 AM
    )

def test_evaluate_condition_equals():
    event = sample_event()
    condition = {"field": "camera_id", "operator": "equals", "value": "restricted-area-01"}
    assert evaluate_condition(condition, event) == True
    
    condition = {"field": "camera_id", "operator": "equals", "value": "other-camera"}
    assert evaluate_condition(condition, event) == False

def test_evaluate_condition_contains():
    event = sample_event()
    condition = {"field": "camera_id", "operator": "contains", "value": "restricted"}
    assert evaluate_condition(condition, event) == True

def test_evaluate_condition_detection_label():
    event = sample_event()
    condition = {"field": "detection_label", "operator": "contains", "value": "person"}
    assert evaluate_condition(condition, event) == True
    
    condition = {"field": "detection_label", "operator": "contains", "value": "vehicle"}
    assert evaluate_condition(condition, event) == False

def test_evaluate_condition_time_between():
    event = sample_event()  # 2:30 AM
    condition = {"field": "time_of_day", "operator": "between", "value": ["22:00", "06:00"]}
    assert evaluate_condition(condition, event) == True
    
    condition = {"field": "time_of_day", "operator": "between", "value": ["08:00", "18:00"]}
    assert evaluate_condition(condition, event) == False

def test_evaluate_rule_multiple_conditions():
    event = sample_event()
    conditions = [
        {"field": "detection_label", "operator": "contains", "value": "person"},
        {"field": "camera_id", "operator": "contains", "value": "restricted"},
        {"field": "time_of_day", "operator": "between", "value": ["22:00", "06:00"]}
    ]
    assert evaluate_rule(conditions, event) == True

def test_get_triggered_actions():
    event = sample_event()
    rules = [
        {
            "id": "rule1",
            "name": "After Hours Alert",
            "conditions": '[{"field": "detection_label", "operator": "contains", "value": "person"}]',
            "actions": '[{"type": "send_notification", "parameters": {"recipients": ["security@company.com"]}}]',
            "is_active": True
        }
    ]
    
    actions = get_triggered_actions(event, rules)
    assert len(actions) == 1
    assert actions[0]["type"] == "send_notification"
    assert actions[0]["rule_id"] == "rule1"