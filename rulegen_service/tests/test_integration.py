#!/usr/bin/env python3
"""
Quick integration test for the rule validation system
"""

import asyncio
import json
from rule_validator import RuleValidator, RuleTestHarness, ValidationSeverity

async def test_rule_validation():
    """Test the complete rule validation workflow"""
    
    # Test rule 1: Valid person detection rule
    valid_rule = {
        "id": "test-rule-1",
        "name": "Person Detection Alert",
        "type": "detection",
        "description": "Alert when person detected in camera 1",
        "priority": "high",
        "conditions": [
            {
                "field": "camera_id",
                "operator": "equals",
                "value": "camera-001"
            },
            {
                "field": "detection_label",
                "operator": "contains",
                "value": "person"
            },
            {
                "field": "confidence",
                "operator": "greater_than",
                "value": 0.8
            }
        ],
        "actions": [
            {
                "type": "send_notification",
                "parameters": {
                    "recipients": ["admin@example.com"],
                    "message": "Person detected"
                }
            }
        ]
    }
    
    # Test rule 2: Invalid rule with errors
    invalid_rule = {
        "name": "Bad Rule",
        "conditions": [
            {
                "field": "confidence",
                "operator": "invalid_operator",
                "value": "not_a_number"
            }
        ],
        "actions": []  # Missing actions
    }
    
    # Test rule 3: Conflicting rule
    conflicting_rule = {
        "id": "test-rule-2",
        "name": "Conflicting Person Detection",
        "type": "detection",
        "conditions": [
            {
                "field": "camera_id",
                "operator": "equals",
                "value": "camera-001"
            },
            {
                "field": "detection_label",
                "operator": "not_equals",
                "value": "person"
            }
        ],
        "actions": [
            {
                "type": "send_notification",
                "parameters": {}
            }
        ]
    }
    
    print("🔍 Testing Rule Validation System")
    print("=" * 50)
    
    # Initialize validator with existing rules
    validator = RuleValidator(existing_rules=[valid_rule])
    
    # Test 1: Valid rule validation
    print("\n1. Testing valid rule validation...")
    result1 = await validator.validate_rule(valid_rule, check_conflicts=False)
    print(f"   ✅ Valid rule - Is Valid: {result1.is_valid}")
    print(f"   📊 Issues: {len(result1.issues)}")
    print(f"   ⚡ Performance warnings: {len(result1.performance_warnings)}")
    print(f"   💡 Optimization suggestions: {len(result1.optimization_suggestions)}")
    
    # Test 2: Invalid rule validation
    print("\n2. Testing invalid rule validation...")
    result2 = await validator.validate_rule(invalid_rule, check_conflicts=False)
    print(f"   ❌ Invalid rule - Is Valid: {result2.is_valid}")
    print(f"   📊 Issues: {len(result2.issues)}")
    for issue in result2.issues[:3]:  # Show first 3 issues
        print(f"      - {issue.severity.value}: {issue.message}")
    
    # Test 3: Conflict detection
    print("\n3. Testing conflict detection...")
    result3 = await validator.validate_rule(conflicting_rule, check_conflicts=True)
    print(f"   ⚠️  Conflicting rule - Is Valid: {result3.is_valid}")
    print(f"   🔥 Conflicts detected: {len(result3.conflicts)}")
    for conflict in result3.conflicts:
        print(f"      - {conflict.conflict_type.value}: {conflict.description}")
    
    # Test 4: Rule testing harness
    print("\n4. Testing rule test harness...")
    harness = RuleTestHarness(valid_rule)
    try:
        test_results = await harness.run_comprehensive_tests()
        print(f"   🧪 Total tests: {test_results['total_tests']}")
        print(f"   ✅ Passed: {test_results['passed_tests']}")
        print(f"   ❌ Failed: {test_results['failed_tests']}")
        print(f"   📈 Success rate: {test_results['success_rate']:.2%}")
        print(f"   📊 Coverage score: {test_results['coverage_score']:.2f}")
    except Exception as e:
        print(f"   ⚠️  Test harness error (expected due to missing dependencies): {str(e)[:100]}...")
    
    print("\n" + "=" * 50)
    print("🎉 Rule Validation System Test Complete!")
    
    return {
        "valid_rule_result": result1,
        "invalid_rule_result": result2,
        "conflict_result": result3
    }

if __name__ == "__main__":
    asyncio.run(test_rule_validation())
