#!/usr/bin/env python3
"""
Demo script to test the comprehensive rule validation system.
"""

from datetime import datetime
from rule_validator import RuleValidator, RuleTestHarness, ValidationSeverity, ConflictType

def test_rule_validation():
    """Test comprehensive rule validation with various scenarios."""
    
    # Initialize validator
    validator = RuleValidator()
    test_harness = RuleTestHarness()
    
    print("🔍 Testing Comprehensive Rule Validation System")
    print("=" * 60)
    
    # Test 1: Valid rule
    print("\n1️⃣ Testing Valid Rule")
    valid_rule = {
        "id": "rule_001",
        "name": "Person Detection Alert",
        "description": "Alert when person detected in office",
        "conditions": {
            "event_type": "detection",
            "detection_label": "person",
            "camera_id": ["cam_001", "cam_002"],
            "confidence": {"operator": "greater_than", "value": 0.8},
            "time_of_day": {"operator": "between", "value": ["09:00", "17:00"]}
        },
        "actions": {
            "send_notification": True,
            "alert_level": "medium"
        },
        "is_active": True
    }
    
    result = validator.validate_rule(valid_rule)
    print(f"✅ Valid rule - Issues: {len(result.issues)}, Warnings: {len([i for i in result.issues if i.severity == ValidationSeverity.WARNING])}")
    
    # Test 2: Rule with syntax errors
    print("\n2️⃣ Testing Rule with Syntax Errors")
    invalid_rule = {
        "id": "rule_002",
        "name": "",  # Missing name
        "conditions": {
            "event_type": "invalid_type",  # Invalid event type
            "confidence": {"operator": "invalid_op", "value": "not_a_number"}  # Invalid operator and value
        },
        "actions": {},  # Empty actions
        "is_active": "not_boolean"  # Invalid boolean
    }
    
    result = validator.validate_rule(invalid_rule)
    print(f"❌ Invalid rule - Issues: {len(result.issues)}")
    for issue in result.issues[:3]:  # Show first 3 issues
        print(f"   - {issue.severity.value}: {issue.message}")
    
    # Test 3: Conflicting rules
    print("\n3️⃣ Testing Rule Conflicts")
    existing_rules = [
        {
            "id": "rule_003a",
            "name": "No Alerts at Night",
            "conditions": {
                "time_of_day": {"operator": "between", "value": ["22:00", "06:00"]}
            },
            "actions": {"disable_alerts": True}
        }
    ]
    
    conflicting_rule = {
        "id": "rule_003b",
        "name": "Night Security Alert",
        "conditions": {
            "event_type": "detection",
            "time_of_day": {"operator": "between", "value": ["23:00", "05:00"]}
        },
        "actions": {"send_notification": True, "alert_level": "high"}
    }
    
    conflicts = validator.detect_conflicts(conflicting_rule, existing_rules)
    print(f"⚠️  Found {len(conflicts)} conflict(s)")
    for conflict in conflicts:
        print(f"   - {conflict.type.value}: {conflict.description}")
    
    # Test 4: Rule testing harness
    print("\n4️⃣ Testing Rule Testing Harness")
    test_rule = {
        "id": "rule_004",
        "name": "Vehicle Detection Test",
        "conditions": {
            "event_type": "detection",
            "detection_label": "car",
            "confidence": {"operator": "greater_than", "value": 0.7}
        },
        "actions": {"send_notification": True}
    }
    
    test_results = test_harness.run_comprehensive_test(test_rule)
    print(f"🧪 Test Results - Coverage: {test_results.coverage_score:.1%}")
    print(f"   - Passed: {test_results.passed_tests}, Failed: {test_results.failed_tests}")
    print(f"   - Total scenarios: {len(test_results.test_scenarios)}")
    
    # Test 5: Performance analysis
    print("\n5️⃣ Testing Performance Analysis")
    complex_rule = {
        "id": "rule_005",
        "name": "Complex Multi-Condition Rule",
        "conditions": {
            "event_type": "detection",
            "detection_label": ["person", "car", "bicycle", "motorcycle"],
            "camera_id": [f"cam_{i:03d}" for i in range(1, 21)],  # 20 cameras
            "confidence": {"operator": "greater_than", "value": 0.8},
            "time_of_day": {"operator": "between", "value": ["08:00", "20:00"]},
            "custom_field": {"operator": "matches", "value": r"^[A-Z]{2}\d{4}$"}
        },
        "actions": {"send_notification": True, "save_clip": True}
    }
    
    result = validator.validate_rule(complex_rule)
    performance_issues = [i for i in result.issues if "performance" in i.message.lower()]
    print(f"⚡ Performance analysis - Issues: {len(performance_issues)}")
    for issue in performance_issues:
        print(f"   - {issue.message}")
    
    print("\n" + "=" * 60)
    print("✅ Rule validation system test completed successfully!")

if __name__ == "__main__":
    test_rule_validation()
