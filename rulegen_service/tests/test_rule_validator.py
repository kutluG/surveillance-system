"""
Comprehensive tests for rule validation and conflict detection system.
"""

import pytest
import json
from datetime import datetime, time
from unittest.mock import Mock, patch

from rule_validator import (
    RuleValidator, RuleTestHarness, ValidationSeverity, ConflictType,
    ValidationIssue, RuleConflict, ValidationResult
)
from shared.models import CameraEvent, Detection, BoundingBox, EventType


class TestRuleValidator:
    """Test cases for RuleValidator"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = RuleValidator()
        
        # Sample valid rule
        self.valid_rule = {
            "name": "Person Detection Alert",
            "description": "Alert when person detected in restricted area",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"},
                {"field": "camera_id", "operator": "contains", "value": "restricted"},
                {"field": "confidence", "operator": "greater_than", "value": 0.8}
            ],
            "actions": [
                {"type": "send_notification", "parameters": {"recipients": ["security@company.com"]}},
                {"type": "create_alert", "parameters": {"priority": "high"}}
            ],
            "type": "detection",
            "priority": 1
        }
        
        # Sample existing rules for conflict testing
        self.existing_rules = [
            {
                "id": "rule-1",
                "name": "Existing Person Detection",
                "conditions": [
                    {"field": "detection_label", "operator": "equals", "value": "person"},
                    {"field": "camera_id", "operator": "contains", "value": "restricted"}
                ],
                "actions": [
                    {"type": "send_notification", "parameters": {"recipients": ["security@company.com"]}}
                ],
                "type": "detection",
                "priority": 1
            },
            {
                "id": "rule-2", 
                "name": "Night Time Restriction",
                "conditions": [
                    {"field": "time_of_day", "operator": "between", "value": ["22:00", "06:00"]}
                ],
                "actions": [
                    {"type": "suppress_alerts", "parameters": {}}
                ],
                "type": "automation",
                "priority": 2
            }
        ]
    
    @pytest.mark.asyncio
    async def test_valid_rule_validation(self):
        """Test validation of a valid rule"""
        result = await self.validator.validate_rule(self.valid_rule, check_conflicts=False)
        
        assert result.is_valid == True
        assert len([issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]) == 0
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test validation with missing required fields"""
        invalid_rule = {"description": "Rule without name or conditions"}
        
        result = await self.validator.validate_rule(invalid_rule, check_conflicts=False)
        
        assert result.is_valid == False
        errors = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 2  # Missing name and conditions
        
        error_messages = [error.message for error in errors]
        assert any("name" in msg.lower() for msg in error_messages)
        assert any("condition" in msg.lower() for msg in error_messages)
    
    @pytest.mark.asyncio
    async def test_invalid_condition_format(self):
        """Test validation with invalid condition format"""
        invalid_rule = {
            "name": "Invalid Condition Rule",
            "conditions": [
                {"field": "detection_label"},  # Missing operator and value
                {"operator": "equals", "value": "person"}  # Missing field
            ],
            "actions": [
                {"type": "send_notification", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(invalid_rule, check_conflicts=False)
        
        assert result.is_valid == False
        errors = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 2  # Each invalid condition should generate errors
    
    @pytest.mark.asyncio
    async def test_invalid_operator(self):
        """Test validation with invalid operators"""
        invalid_rule = {
            "name": "Invalid Operator Rule",
            "conditions": [
                {"field": "detection_label", "operator": "invalid_op", "value": "person"}
            ],
            "actions": [
                {"type": "send_notification", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(invalid_rule, check_conflicts=False)
        
        assert result.is_valid == False
        errors = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert any("invalid operator" in error.message.lower() for error in errors)
    
    @pytest.mark.asyncio
    async def test_time_validation(self):
        """Test time field validation"""
        # Valid time range
        valid_time_rule = {
            "name": "Valid Time Rule",
            "conditions": [
                {"field": "time_of_day", "operator": "between", "value": ["09:00", "17:00"]}
            ],
            "actions": [
                {"type": "log_event", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(valid_time_rule, check_conflicts=False)
        assert result.is_valid == True
        
        # Invalid time format
        invalid_time_rule = {
            "name": "Invalid Time Rule",
            "conditions": [
                {"field": "time_of_day", "operator": "between", "value": ["25:00", "invalid"]}
            ],
            "actions": [
                {"type": "log_event", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(invalid_time_rule, check_conflicts=False)
        assert result.is_valid == False
    
    @pytest.mark.asyncio
    async def test_confidence_validation(self):
        """Test confidence field validation"""
        # Valid confidence
        valid_confidence_rule = {
            "name": "Valid Confidence Rule",
            "conditions": [
                {"field": "confidence", "operator": "greater_than", "value": 0.8}
            ],
            "actions": [
                {"type": "log_event", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(valid_confidence_rule, check_conflicts=False)
        assert result.is_valid == True
        
        # Invalid confidence (out of range)
        invalid_confidence_rule = {
            "name": "Invalid Confidence Rule",
            "conditions": [
                {"field": "confidence", "operator": "greater_than", "value": 1.5}
            ],
            "actions": [
                {"type": "log_event", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(invalid_confidence_rule, check_conflicts=False)
        warnings = [issue for issue in result.issues if issue.severity == ValidationSeverity.WARNING]
        assert any("confidence" in warning.message.lower() for warning in warnings)
    
    @pytest.mark.asyncio
    async def test_internal_contradictions(self):
        """Test detection of contradictory conditions within same rule"""
        contradictory_rule = {
            "name": "Contradictory Rule",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"},
                {"field": "detection_label", "operator": "not_equals", "value": "person"}
            ],
            "actions": [
                {"type": "log_event", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(contradictory_rule, check_conflicts=False)
        
        assert result.is_valid == False
        errors = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert any("contradictory" in error.message.lower() for error in errors)
    
    @pytest.mark.asyncio
    async def test_redundant_rule_detection(self):
        """Test detection of redundant rules"""
        validator_with_existing = RuleValidator(self.existing_rules)
        
        # Create a rule very similar to existing rule-1
        redundant_rule = {
            "name": "Duplicate Person Detection",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"},
                {"field": "camera_id", "operator": "contains", "value": "restricted"}
            ],
            "actions": [
                {"type": "send_notification", "parameters": {"recipients": ["security@company.com"]}}
            ],
            "type": "detection",
            "priority": 1
        }
        
        result = await validator_with_existing.validate_rule(redundant_rule, check_conflicts=True)
        
        redundant_conflicts = [c for c in result.conflicts if c.conflict_type == ConflictType.REDUNDANT]
        assert len(redundant_conflicts) > 0
    
    @pytest.mark.asyncio
    async def test_contradictory_rule_detection(self):
        """Test detection of contradictory rules"""
        validator_with_existing = RuleValidator(self.existing_rules)
        
        # Create a rule that contradicts an existing rule
        contradictory_rule = {
            "name": "Contradictory Detection",
            "conditions": [
                {"field": "detection_label", "operator": "not_equals", "value": "person"},
                {"field": "camera_id", "operator": "contains", "value": "restricted"}
            ],
            "actions": [
                {"type": "create_alert", "parameters": {}}
            ],
            "type": "detection",
            "priority": 1
        }
        
        result = await validator_with_existing.validate_rule(contradictory_rule, check_conflicts=True)
        
        contradictory_conflicts = [c for c in result.conflicts if c.conflict_type == ConflictType.CONTRADICTORY]
        assert len(contradictory_conflicts) > 0
    
    @pytest.mark.asyncio
    async def test_performance_warnings(self):
        """Test detection of performance issues"""
        performance_heavy_rule = {
            "name": "Performance Heavy Rule",
            "conditions": [
                {"field": "description", "operator": "matches", "value": ".*complex.*regex.*pattern.*"},
                {"field": "tags", "operator": "contains", "value": ["tag1", "tag2", "tag3", "tag4", "tag5", 
                                                                   "tag6", "tag7", "tag8", "tag9", "tag10", "tag11"]},
                {"field": "metadata", "operator": "between", "value": [1, 1000]},
                {"field": "confidence", "operator": "greater_than", "value": 0.5},
                {"field": "detection_label", "operator": "equals", "value": "person"},
                {"field": "camera_id", "operator": "contains", "value": "test"}
            ],
            "actions": [
                {"type": "log_event", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(performance_heavy_rule, check_conflicts=False)
        
        assert len(result.performance_warnings) > 0
        assert any("regex" in warning.lower() or "expression" in warning.lower() 
                  for warning in result.performance_warnings)
    
    @pytest.mark.asyncio
    async def test_optimization_suggestions(self):
        """Test generation of optimization suggestions"""
        # Rule with few conditions (should suggest more specificity)
        simple_rule = {
            "name": "Simple Rule",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"}
            ],
            "actions": [
                {"type": "log_event", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(simple_rule, check_conflicts=False)
        
        assert len(result.optimization_suggestions) > 0
        assert any("more specific" in suggestion.lower() 
                  for suggestion in result.optimization_suggestions)
    
    @pytest.mark.asyncio
    async def test_action_validation(self):
        """Test action validation"""
        # Invalid action type
        invalid_action_rule = {
            "name": "Invalid Action Rule",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"}
            ],
            "actions": [
                {"type": "invalid_action_type", "parameters": {}}
            ]
        }
        
        result = await self.validator.validate_rule(invalid_action_rule, check_conflicts=False)
        
        warnings = [issue for issue in result.issues if issue.severity == ValidationSeverity.WARNING]
        assert any("unknown action type" in warning.message.lower() for warning in warnings)
        
        # Missing action parameters
        missing_params_rule = {
            "name": "Missing Params Rule",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"}
            ],
            "actions": [
                {"type": "send_notification", "parameters": {}}  # Missing recipients
            ]
        }
        
        result = await self.validator.validate_rule(missing_params_rule, check_conflicts=False)
        
        warnings = [issue for issue in result.issues if issue.severity == ValidationSeverity.WARNING]
        assert any("recipients" in warning.message.lower() for warning in warnings)


class TestRuleTestHarness:
    """Test cases for RuleTestHarness"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.rule_data = {
            "name": "Test Rule",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"},
                {"field": "confidence", "operator": "greater_than", "value": 0.8}
            ],
            "actions": [
                {"type": "send_notification", "parameters": {"recipients": ["test@example.com"]}}
            ]
        }
        
        self.test_harness = RuleTestHarness(self.rule_data)
    
    @pytest.mark.asyncio
    async def test_comprehensive_testing(self):
        """Test comprehensive rule testing"""
        with patch('rule_validator.evaluate_rule') as mock_evaluate:
            # Setup mock to return True for positive tests, False for negative tests
            def mock_rule_evaluation(conditions, event):
                # Simplified logic for testing
                return event.detections and event.detections[0].label == "person"
            
            mock_evaluate.side_effect = mock_rule_evaluation
            
            result = await self.test_harness.run_comprehensive_tests()
            
            assert result['total_tests'] > 0
            assert 'passed_tests' in result
            assert 'failed_tests' in result
            assert 'success_rate' in result
            assert 'coverage_score' in result
            assert 'test_details' in result
    
    def test_test_event_creation(self):
        """Test creation of test events"""
        event_data = {
            'camera_id': 'test-camera-01',
            'event_type': 'detection',
            'timestamp': '2025-06-06T10:00:00',
            'detections': [{'label': 'person', 'confidence': 0.95}],
            'metadata': {'zone': 'restricted'}
        }
        
        event = self.test_harness._create_test_event(event_data)
        
        assert isinstance(event, CameraEvent)
        assert event.camera_id == 'test-camera-01'
        assert len(event.detections) == 1
        assert event.detections[0].label == 'person'
        assert event.detections[0].confidence == 0.95


class TestValidationIntegration:
    """Integration tests for the complete validation system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation_workflow(self):
        """Test complete validation workflow"""
        # Create a rule that should pass validation
        good_rule = {
            "name": "End-to-End Test Rule",
            "description": "A well-formed rule for testing",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"},
                {"field": "camera_id", "operator": "contains", "value": "entrance"},
                {"field": "confidence", "operator": "greater_than", "value": 0.85},
                {"field": "time_of_day", "operator": "between", "value": ["09:00", "17:00"]}
            ],
            "actions": [
                {"type": "send_notification", "parameters": {"recipients": ["security@company.com"], "priority": "medium"}},
                {"type": "create_alert", "parameters": {"priority": "medium"}}
            ],
            "type": "detection",
            "priority": 2
        }
        
        # Validate the rule
        validator = RuleValidator()
        validation_result = await validator.validate_rule(good_rule, check_conflicts=False)
        
        # Should be valid with possibly some optimization suggestions
        assert validation_result.is_valid == True
        assert len([issue for issue in validation_result.issues 
                   if issue.severity == ValidationSeverity.ERROR]) == 0
        
        # Test the rule
        test_harness = RuleTestHarness(good_rule)
        with patch('rule_validator.evaluate_rule') as mock_evaluate:
            mock_evaluate.return_value = True  # Simplified for test
            test_result = await test_harness.run_comprehensive_tests()
            
            assert test_result['total_tests'] > 0
            assert test_result['coverage_score'] > 0.0
    
    @pytest.mark.asyncio
    async def test_conflict_detection_scenarios(self):
        """Test various conflict detection scenarios"""
        existing_rules = [
            {
                "id": "existing-1",
                "name": "Existing Alert Rule",
                "conditions": [
                    {"field": "detection_label", "operator": "equals", "value": "person"},
                    {"field": "time_of_day", "operator": "between", "value": ["18:00", "06:00"]}
                ],
                "actions": [
                    {"type": "send_alert", "parameters": {"priority": "high"}}
                ],
                "type": "detection",
                "priority": 1
            },
            {
                "id": "existing-2",
                "name": "Existing Suppression Rule", 
                "conditions": [
                    {"field": "time_of_day", "operator": "between", "value": ["22:00", "06:00"]}
                ],
                "actions": [
                    {"type": "suppress_alerts", "parameters": {}}
                ],
                "type": "automation",
                "priority": 2
            }
        ]
        
        validator = RuleValidator(existing_rules)
        
        # Test conflicting rule (person detection with alert suppression)
        conflicting_rule = {
            "name": "Conflicting Night Alert",
            "conditions": [
                {"field": "detection_label", "operator": "equals", "value": "person"},
                {"field": "time_of_day", "operator": "between", "value": ["23:00", "05:00"]}
            ],
            "actions": [
                {"type": "send_alert", "parameters": {"priority": "critical"}}
            ],
            "type": "detection",
            "priority": 1
        }
        
        result = await validator.validate_rule(conflicting_rule, check_conflicts=True)
        
        # Should detect potential conflicts
        assert len(result.conflicts) > 0 or len(result.issues) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
