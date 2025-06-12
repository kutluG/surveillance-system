"""
Comprehensive Rule Validation and Conflict Detection System

This module provides:
- Syntax validation for rule structure
- Semantic validation for rule logic
- Conflict detection between rules
- Performance impact analysis
- Testing harness for generated rules
"""

import json
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re

try:
    from shared.models import CameraEvent, Detection, BoundingBox, EventType
    from .rule_engine import evaluate_condition, evaluate_rule
except ImportError:
    # Mock classes for standalone testing
    class EventType:
        DETECTION = "detection"
    
    class BoundingBox:
        def __init__(self, x_min=0, y_min=0, x_max=1, y_max=1):
            self.x_min = x_min
            self.y_min = y_min
            self.x_max = x_max
            self.y_max = y_max
    
    class Detection:
        def __init__(self, label="unknown", confidence=0.5, bounding_box=None):
            self.label = label
            self.confidence = confidence
            self.bounding_box = bounding_box or BoundingBox()
    
    class CameraEvent:
        def __init__(self, camera_id="test", event_type=EventType.DETECTION, 
                     detections=None, timestamp=None, metadata=None):
            self.camera_id = camera_id
            self.event_type = event_type
            self.detections = detections or []
            self.timestamp = timestamp or datetime.now()
            self.metadata = metadata or {}
    
    def evaluate_condition(condition, event):
        """Mock evaluation function"""
        return True
    
    def evaluate_rule(conditions, event):
        """Mock evaluation function"""
        return True

logger = logging.getLogger(__name__)

class ConflictType(Enum):
    CONTRADICTORY = "contradictory"  # Rules that can never both be true
    REDUNDANT = "redundant"  # Rules that are duplicates or subsets
    PRIORITY_CONFLICT = "priority_conflict"  # Rules with conflicting priorities
    TEMPORAL_CONFLICT = "temporal_conflict"  # Time-based conflicts
    ACTION_CONFLICT = "action_conflict"  # Conflicting actions

class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    message: str
    rule_field: Optional[str] = None
    suggestion: Optional[str] = None

@dataclass
class RuleConflict:
    conflict_type: ConflictType
    conflicting_rule_id: str
    conflicting_rule_name: str
    description: str
    severity: ValidationSeverity
    resolution_suggestion: str

@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[ValidationIssue]
    conflicts: List[RuleConflict]
    performance_warnings: List[str]
    optimization_suggestions: List[str]
    test_coverage: Dict[str, Any]

class RuleValidator:
    """Comprehensive rule validation and conflict detection system"""
    
    def __init__(self, existing_rules: List[Dict] = None):
        self.existing_rules = existing_rules or []
        self.field_validators = self._init_field_validators()
        self.operator_validators = self._init_operator_validators()
    
    def _init_field_validators(self) -> Dict[str, callable]:
        """Initialize field-specific validators"""
        return {
            'event_type': self._validate_event_type,
            'camera_id': self._validate_camera_id,
            'detection_label': self._validate_detection_label,
            'time_of_day': self._validate_time_of_day,
            'confidence': self._validate_confidence,
            'zone': self._validate_zone,
            'duration': self._validate_duration,
            'count': self._validate_count
        }
    
    def _init_operator_validators(self) -> Dict[str, callable]:
        """Initialize operator-specific validators"""
        return {
            'equals': self._validate_equals_operator,
            'not_equals': self._validate_not_equals_operator,
            'contains': self._validate_contains_operator,
            'greater_than': self._validate_greater_than_operator,
            'less_than': self._validate_less_than_operator,
            'between': self._validate_between_operator,
            'in_range': self._validate_in_range_operator,
            'matches': self._validate_matches_operator
        }
    
    async def validate_rule(self, rule_data: Dict, check_conflicts: bool = True) -> ValidationResult:
        """Comprehensive rule validation"""
        issues = []
        conflicts = []
        performance_warnings = []
        optimization_suggestions = []
        
        # Basic structure validation
        issues.extend(self._validate_structure(rule_data))
        
        # Validate conditions
        issues.extend(self._validate_conditions(rule_data.get('conditions', [])))
        
        # Validate actions
        issues.extend(self._validate_actions(rule_data.get('actions', [])))
        
        # Semantic validation
        issues.extend(self._validate_semantics(rule_data))
        
        # Performance analysis
        performance_warnings.extend(self._analyze_performance(rule_data))
        
        # Optimization suggestions
        optimization_suggestions.extend(self._get_optimization_suggestions(rule_data))
        
        # Conflict detection
        if check_conflicts:
            conflicts = await self._detect_conflicts(rule_data)
        
        # Generate test coverage
        test_coverage = self._generate_test_coverage(rule_data)
        
        is_valid = not any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            conflicts=conflicts,
            performance_warnings=performance_warnings,
            optimization_suggestions=optimization_suggestions,
            test_coverage=test_coverage
        )
    
    def _validate_structure(self, rule_data: Dict) -> List[ValidationIssue]:
        """Validate basic rule structure"""
        issues = []
        
        # Required fields
        required_fields = ['name', 'conditions', 'actions']
        for field in required_fields:
            if not rule_data.get(field):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Required field '{field}' is missing",
                    rule_field=field,
                    suggestion=f"Add a {field} to the rule"
                ))
        
        # Name validation
        name = rule_data.get('name', '')
        if name:
            if len(name) < 3:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Rule name is too short",
                    rule_field='name',
                    suggestion="Use a more descriptive name (at least 3 characters)"
                ))
            
            if len(name) > 100:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Rule name is too long",
                    rule_field='name',
                    suggestion="Shorten the rule name to under 100 characters"
                ))
        
        # Type validation
        rule_type = rule_data.get('type')
        valid_types = ['detection', 'alert', 'automation', 'threshold', 'pattern']
        if rule_type and rule_type not in valid_types:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Invalid rule type '{rule_type}'",
                rule_field='type',
                suggestion=f"Use one of: {', '.join(valid_types)}"
            ))
        
        return issues
    
    def _validate_conditions(self, conditions: List[Dict]) -> List[ValidationIssue]:
        """Validate rule conditions"""
        issues = []
        
        if not conditions:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Rule must have at least one condition",
                rule_field='conditions',
                suggestion="Add conditions to define when the rule should trigger"
            ))
            return issues
        
        for i, condition in enumerate(conditions):
            condition_issues = self._validate_single_condition(condition, i)
            issues.extend(condition_issues)
        
        # Check for contradictory conditions within the same rule
        contradictions = self._find_internal_contradictions(conditions)
        for contradiction in contradictions:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Contradictory conditions: {contradiction}",
                rule_field='conditions',
                suggestion="Remove contradictory conditions or use separate rules"
            ))
        
        return issues
    
    def _validate_single_condition(self, condition: Dict, index: int) -> List[ValidationIssue]:
        """Validate a single condition"""
        issues = []
        
        # Required condition fields
        required_fields = ['field', 'operator', 'value']
        for field in required_fields:
            if field not in condition:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Condition {index + 1}: Missing '{field}'",
                    rule_field=f'conditions[{index}].{field}',
                    suggestion=f"Add {field} to condition {index + 1}"
                ))
        
        if all(field in condition for field in required_fields):
            field = condition['field']
            operator = condition['operator']
            value = condition['value']
            
            # Validate field
            if field in self.field_validators:
                field_issues = self.field_validators[field](value, operator, index)
                issues.extend(field_issues)
            else:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Condition {index + 1}: Unknown field '{field}'",
                    rule_field=f'conditions[{index}].field',
                    suggestion="Use a standard field or ensure this custom field exists"
                ))
            
            # Validate operator
            if operator in self.operator_validators:
                operator_issues = self.operator_validators[operator](field, value, index)
                issues.extend(operator_issues)
            else:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Condition {index + 1}: Invalid operator '{operator}'",
                    rule_field=f'conditions[{index}].operator',
                    suggestion="Use a valid operator: equals, contains, greater_than, etc."
                ))
        
        return issues
    
    def _validate_actions(self, actions: List[Dict]) -> List[ValidationIssue]:
        """Validate rule actions"""
        issues = []
        
        if not actions:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Rule must have at least one action",
                rule_field='actions',
                suggestion="Add actions to define what happens when the rule triggers"
            ))
            return issues
        
        valid_action_types = [
            'send_notification', 'create_alert', 'trigger_recording',
            'send_email', 'trigger_alarm', 'log_event', 'escalate'
        ]
        
        for i, action in enumerate(actions):
            if 'type' not in action:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Action {i + 1}: Missing 'type'",
                    rule_field=f'actions[{i}].type',
                    suggestion=f"Add type to action {i + 1}"
                ))
                continue
            
            action_type = action['type']
            if action_type not in valid_action_types:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Action {i + 1}: Unknown action type '{action_type}'",
                    rule_field=f'actions[{i}].type',
                    suggestion=f"Use a standard action type: {', '.join(valid_action_types)}"
                ))
            
            # Validate action parameters
            parameters = action.get('parameters', {})
            action_issues = self._validate_action_parameters(action_type, parameters, i)
            issues.extend(action_issues)
        
        return issues
    
    def _validate_semantics(self, rule_data: Dict) -> List[ValidationIssue]:
        """Validate rule semantics and logic"""
        issues = []
        
        conditions = rule_data.get('conditions', [])
        actions = rule_data.get('actions', [])
        
        # Check for logical inconsistencies
        
        # Example: "No person detected for 2 hours" + "nighttime = no alerts"
        has_absence_condition = any(
            'no' in str(c.get('value', '')).lower() or 
            c.get('operator') == 'not_equals'
            for c in conditions
        )
        
        has_time_restriction = any(
            c.get('field') == 'time_of_day' or
            'night' in str(c.get('value', '')).lower()
            for c in conditions
        )
        
        has_alert_action = any(
            'alert' in a.get('type', '') or
            'notification' in a.get('type', '')
            for a in actions
        )
        
        if has_absence_condition and has_time_restriction and has_alert_action:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Potential conflict: Absence detection with time restrictions may not work as expected",
                suggestion="Consider if absence detection should be active during restricted hours"
            ))
        
        # Check for unrealistic time ranges
        for condition in conditions:
            if condition.get('field') == 'duration' and condition.get('operator') == 'greater_than':
                duration = condition.get('value', 0)
                if isinstance(duration, (int, float)) and duration > 86400:  # > 24 hours
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="Duration condition exceeds 24 hours",
                        suggestion="Consider if such long durations are realistic for your use case"
                    ))
        
        return issues
    
    async def _detect_conflicts(self, rule_data: Dict) -> List[RuleConflict]:
        """Detect conflicts with existing rules"""
        conflicts = []
        
        for existing_rule in self.existing_rules:
            conflict = await self._check_rule_pair_conflict(rule_data, existing_rule)
            if conflict:
                conflicts.append(conflict)
        
        return conflicts
    
    async def _check_rule_pair_conflict(self, rule1: Dict, rule2: Dict) -> Optional[RuleConflict]:
        """Check for conflicts between two rules"""
        
        # Check for redundancy
        if self._are_rules_redundant(rule1, rule2):
            return RuleConflict(
                conflict_type=ConflictType.REDUNDANT,
                conflicting_rule_id=rule2.get('id', 'unknown'),
                conflicting_rule_name=rule2.get('name', 'Unknown Rule'),
                description="Rules have identical or very similar conditions and actions",
                severity=ValidationSeverity.WARNING,
                resolution_suggestion="Consider merging or removing one of the rules"
            )
        
        # Check for contradictory conditions with overlapping scope
        if self._are_rules_contradictory(rule1, rule2):
            return RuleConflict(
                conflict_type=ConflictType.CONTRADICTORY,
                conflicting_rule_id=rule2.get('id', 'unknown'),
                conflicting_rule_name=rule2.get('name', 'Unknown Rule'),
                description="Rules have contradictory conditions that cannot both be satisfied",
                severity=ValidationSeverity.ERROR,
                resolution_suggestion="Modify conditions to avoid contradiction or use different triggers"
            )
        
        # Check for temporal conflicts
        temporal_conflict = self._check_temporal_conflict(rule1, rule2)
        if temporal_conflict:
            return temporal_conflict
        
        # Check for action conflicts
        action_conflict = self._check_action_conflict(rule1, rule2)
        if action_conflict:
            return action_conflict
        
        return None
    
    def _are_rules_redundant(self, rule1: Dict, rule2: Dict) -> bool:
        """Check if rules are redundant"""
        conditions1 = rule1.get('conditions', [])
        conditions2 = rule2.get('conditions', [])
        actions1 = rule1.get('actions', [])
        actions2 = rule2.get('actions', [])
        
        # Simple redundancy check - exact match
        conditions1_normalized = [self._normalize_condition(c) for c in conditions1]
        conditions2_normalized = [self._normalize_condition(c) for c in conditions2]
        actions1_normalized = [self._normalize_action(a) for a in actions1]
        actions2_normalized = [self._normalize_action(a) for a in actions2]
        
        return (conditions1_normalized == conditions2_normalized and 
                actions1_normalized == actions2_normalized)
    
    def _are_rules_contradictory(self, rule1: Dict, rule2: Dict) -> bool:
        """Check if rules are contradictory"""
        conditions1 = rule1.get('conditions', [])
        conditions2 = rule2.get('conditions', [])
        
        # Look for direct contradictions
        for c1 in conditions1:
            for c2 in conditions2:
                if self._are_conditions_contradictory(c1, c2):
                    return True
        
        return False
    
    def _are_conditions_contradictory(self, condition1: Dict, condition2: Dict) -> bool:
        """Check if two conditions are contradictory"""
        if condition1.get('field') != condition2.get('field'):
            return False
        
        field = condition1.get('field')
        op1 = condition1.get('operator')
        op2 = condition2.get('operator')
        val1 = condition1.get('value')
        val2 = condition2.get('value')
        
        # Same field, contradictory operators/values
        if field and op1 and op2 and val1 is not None and val2 is not None:
            # equals vs not_equals with same value
            if ((op1 == 'equals' and op2 == 'not_equals' and val1 == val2) or
                (op1 == 'not_equals' and op2 == 'equals' and val1 == val2)):
                return True
            
            # contains vs not_contains with same value
            if ((op1 == 'contains' and op2 == 'not_contains' and val1 == val2) or
                (op1 == 'not_contains' and op2 == 'contains' and val1 == val2)):
                return True
        
        return False
    
    def _check_temporal_conflict(self, rule1: Dict, rule2: Dict) -> Optional[RuleConflict]:
        """Check for temporal conflicts between rules"""
        # Find time-based conditions
        time_conditions1 = [c for c in rule1.get('conditions', []) if c.get('field') == 'time_of_day']
        time_conditions2 = [c for c in rule2.get('conditions', []) if c.get('field') == 'time_of_day']
        
        if not (time_conditions1 and time_conditions2):
            return None
        
        # Check for conflicting time ranges
        for tc1 in time_conditions1:
            for tc2 in time_conditions2:
                if self._time_ranges_conflict(tc1, tc2):
                    return RuleConflict(
                        conflict_type=ConflictType.TEMPORAL_CONFLICT,
                        conflicting_rule_id=rule2.get('id', 'unknown'),
                        conflicting_rule_name=rule2.get('name', 'Unknown Rule'),
                        description="Rules have conflicting time restrictions",
                        severity=ValidationSeverity.WARNING,
                        resolution_suggestion="Adjust time ranges to avoid overlap or conflicts"
                    )
        
        return None
    
    def _check_action_conflict(self, rule1: Dict, rule2: Dict) -> Optional[RuleConflict]:
        """Check for conflicting actions"""
        actions1 = rule1.get('actions', [])
        actions2 = rule2.get('actions', [])
        
        # Look for conflicting action types
        conflicting_pairs = [
            ('trigger_alarm', 'disable_alarm'),
            ('send_alert', 'suppress_alerts'),
            ('start_recording', 'stop_recording')
        ]
        
        for a1 in actions1:
            for a2 in actions2:
                type1 = a1.get('type')
                type2 = a2.get('type')
                
                for conflict_pair in conflicting_pairs:
                    if (type1 == conflict_pair[0] and type2 == conflict_pair[1]) or \
                       (type1 == conflict_pair[1] and type2 == conflict_pair[0]):
                        return RuleConflict(
                            conflict_type=ConflictType.ACTION_CONFLICT,
                            conflicting_rule_id=rule2.get('id', 'unknown'),
                            conflicting_rule_name=rule2.get('name', 'Unknown Rule'),
                            description=f"Conflicting actions: {type1} vs {type2}",
                            severity=ValidationSeverity.WARNING,
                            resolution_suggestion="Ensure action types don't conflict or use rule priorities"
                        )
        
        return None
    
    def _analyze_performance(self, rule_data: Dict) -> List[str]:
        """Analyze rule performance impact"""
        warnings = []
        
        conditions = rule_data.get('conditions', [])
        
        # Check for expensive operations
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            
            # Regex operations are expensive
            if operator == 'matches':
                warnings.append("Regular expression matching may impact performance")
            
            # Complex range operations
            if operator == 'between' and field != 'time_of_day':
                warnings.append("Range operations on non-time fields may be expensive")
            
            # Large list operations
            if operator == 'contains' and isinstance(condition.get('value'), list):
                value_list = condition.get('value')
                if len(value_list) > 10:
                    warnings.append("Large list containment checks may impact performance")
        
        # Too many conditions
        if len(conditions) > 5:
            warnings.append("Rules with many conditions may be slow to evaluate")
        
        return warnings
    
    def _get_optimization_suggestions(self, rule_data: Dict) -> List[str]:
        """Get optimization suggestions for the rule"""
        suggestions = []
        
        conditions = rule_data.get('conditions', [])
        actions = rule_data.get('actions', [])
        
        # Condition optimization suggestions
        if len(conditions) < 2:
            suggestions.append("Consider adding more specific conditions to reduce false positives")
        
        if len(conditions) > 5:
            suggestions.append("Consider splitting complex rules into multiple simpler rules")
        
        # Check for missing priority
        if not rule_data.get('priority'):
            suggestions.append("Set a priority level for better rule execution order")
        
        # Check for missing description
        if not rule_data.get('description'):
            suggestions.append("Add a description to document the rule's purpose")
        
        # Action optimization
        if len(actions) > 3:
            suggestions.append("Consider consolidating multiple actions into fewer, more comprehensive actions")
        
        # Suggest using templates for common patterns
        if any(c.get('field') == 'detection_label' and c.get('value') == 'person' for c in conditions):
            suggestions.append("Consider using a person detection template for better optimization")
        
        return suggestions
    
    def _generate_test_coverage(self, rule_data: Dict) -> Dict[str, Any]:
        """Generate test coverage analysis for the rule"""
        conditions = rule_data.get('conditions', [])
        
        # Generate test scenarios
        test_scenarios = []
        
        # Positive test case (should trigger)
        positive_scenario = self._generate_positive_test_case(conditions)
        if positive_scenario:
            test_scenarios.append({
                'type': 'positive',
                'description': 'Should trigger the rule',
                'event': positive_scenario
            })
        
        # Negative test cases (should not trigger)
        negative_scenarios = self._generate_negative_test_cases(conditions)
        test_scenarios.extend(negative_scenarios)
        
        # Edge cases
        edge_cases = self._generate_edge_case_tests(conditions)
        test_scenarios.extend(edge_cases)
        
        return {
            'total_scenarios': len(test_scenarios),
            'scenarios': test_scenarios,
            'coverage_score': self._calculate_coverage_score(conditions, test_scenarios)
        }
    
    def _generate_positive_test_case(self, conditions: List[Dict]) -> Optional[Dict]:
        """Generate a test case that should trigger the rule"""
        if not conditions:
            return None
        
        # Create an event that satisfies all conditions
        test_event = {
            'camera_id': 'test-camera-01',
            'event_type': 'detection',
            'timestamp': datetime.now().isoformat(),
            'detections': [{'label': 'person', 'confidence': 0.95}],
            'metadata': {}
        }
        
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if field == 'camera_id' and operator == 'equals':
                test_event['camera_id'] = value
            elif field == 'detection_label' and operator == 'contains':
                test_event['detections'] = [{'label': value, 'confidence': 0.95}]
            elif field == 'time_of_day' and operator == 'between':
                # Set time to be within the range
                if isinstance(value, list) and len(value) == 2:
                    start_time = time.fromisoformat(value[0])
                    test_time = datetime.now().replace(
                        hour=start_time.hour,
                        minute=start_time.minute
                    )
                    test_event['timestamp'] = test_time.isoformat()
        
        return test_event
    
    def _generate_negative_test_cases(self, conditions: List[Dict]) -> List[Dict]:
        """Generate test cases that should not trigger the rule"""
        test_cases = []
        
        # For each condition, generate a case that violates it
        for i, condition in enumerate(conditions):
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            negative_event = {
                'camera_id': 'test-camera-01',
                'event_type': 'detection',
                'timestamp': datetime.now().isoformat(),
                'detections': [{'label': 'person', 'confidence': 0.95}],
                'metadata': {}
            }
            
            # Violate this specific condition
            if field == 'camera_id' and operator == 'equals':
                negative_event['camera_id'] = 'different-camera'
            elif field == 'detection_label' and operator == 'contains':
                negative_event['detections'] = [{'label': 'vehicle', 'confidence': 0.95}]
            elif field == 'confidence' and operator == 'greater_than':
                negative_event['detections'] = [{'label': 'person', 'confidence': value - 0.1}]
            
            test_cases.append({
                'type': 'negative',
                'description': f'Should not trigger (violates condition {i + 1})',
                'event': negative_event
            })
        
        return test_cases
    
    def _generate_edge_case_tests(self, conditions: List[Dict]) -> List[Dict]:
        """Generate edge case test scenarios"""
        edge_cases = []
        
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if operator == 'greater_than' and isinstance(value, (int, float)):
                # Boundary value test
                edge_event = {
                    'camera_id': 'test-camera-01',
                    'event_type': 'detection',
                    'timestamp': datetime.now().isoformat(),
                    'detections': [{'label': 'person', 'confidence': value}],  # Exact boundary
                    'metadata': {}
                }
                
                edge_cases.append({
                    'type': 'edge_case',
                    'description': f'Boundary value test for {field} = {value}',
                    'event': edge_event
                })
        
        return edge_cases
    
    def _calculate_coverage_score(self, conditions: List[Dict], test_scenarios: List[Dict]) -> float:
        """Calculate test coverage score"""
        if not conditions:
            return 0.0
        
        # Basic coverage: positive + negative for each condition + edge cases
        expected_scenarios = 1 + len(conditions) + len([c for c in conditions if c.get('operator') in ['greater_than', 'less_than']])
        actual_scenarios = len(test_scenarios)
        
        return min(1.0, actual_scenarios / expected_scenarios)
    
    # Field validators
    def _validate_event_type(self, value: Any, operator: str, index: int) -> List[ValidationIssue]:
        issues = []
        valid_types = ['detection', 'motion', 'alert', 'system']
        
        if operator == 'equals' and value not in valid_types:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Condition {index + 1}: Unknown event type '{value}'",
                suggestion=f"Use one of: {', '.join(valid_types)}"
            ))
        
        return issues
    
    def _validate_camera_id(self, value: Any, operator: str, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, str):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: Camera ID must be a string",
                suggestion="Use a string value for camera_id"
            ))
        
        return issues
    
    def _validate_detection_label(self, value: Any, operator: str, index: int) -> List[ValidationIssue]:
        issues = []
        common_labels = ['person', 'vehicle', 'face', 'animal', 'package']
        
        if operator == 'equals' and isinstance(value, str) and value not in common_labels:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                message=f"Condition {index + 1}: Uncommon detection label '{value}'",
                suggestion="Ensure this detection label is supported by your detection system"
            ))
        
        return issues
    
    def _validate_time_of_day(self, value: Any, operator: str, index: int) -> List[ValidationIssue]:
        issues = []
        
        if operator == 'between':
            if not isinstance(value, list) or len(value) != 2:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Condition {index + 1}: time_of_day 'between' requires array of 2 time strings",
                    suggestion="Use format: ['HH:MM', 'HH:MM']"
                ))
            else:
                for i, time_str in enumerate(value):
                    try:
                        time.fromisoformat(time_str)
                    except ValueError:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            message=f"Condition {index + 1}: Invalid time format '{time_str}'",
                            suggestion="Use HH:MM format (e.g., '09:30')"
                        ))
        
        return issues
    
    def _validate_confidence(self, value: Any, operator: str, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, (int, float)):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: Confidence must be a number",
                suggestion="Use a decimal value between 0.0 and 1.0"
            ))
        elif not (0.0 <= value <= 1.0):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Condition {index + 1}: Confidence should be between 0.0 and 1.0",
                suggestion="Use a value between 0.0 and 1.0"
            ))
        
        return issues
    
    def _validate_zone(self, value: Any, operator: str, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, str):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: Zone must be a string",
                suggestion="Use a string value for zone identifier"
            ))
        
        return issues
    
    def _validate_duration(self, value: Any, operator: str, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, (int, float)):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: Duration must be a number",
                suggestion="Use number of seconds as integer or float"
            ))
        elif value < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: Duration cannot be negative",
                suggestion="Use a positive number for duration"
            ))
        
        return issues
    
    def _validate_count(self, value: Any, operator: str, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, int):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: Count must be an integer",
                suggestion="Use a whole number for count"
            ))
        elif value < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: Count cannot be negative",
                suggestion="Use a positive integer for count"
            ))
        
        return issues
    
    # Operator validators
    def _validate_equals_operator(self, field: str, value: Any, index: int) -> List[ValidationIssue]:
        return []  # Basic validation only
    
    def _validate_not_equals_operator(self, field: str, value: Any, index: int) -> List[ValidationIssue]:
        return []  # Basic validation only
    
    def _validate_contains_operator(self, field: str, value: Any, index: int) -> List[ValidationIssue]:
        issues = []
        
        if field in ['confidence', 'count', 'duration'] and not isinstance(value, str):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Condition {index + 1}: 'contains' operator unusual for numeric field {field}",
                suggestion="Consider using 'equals', 'greater_than', or 'less_than' for numeric fields"
            ))
        
        return issues
    
    def _validate_greater_than_operator(self, field: str, value: Any, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, (int, float)):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: 'greater_than' requires numeric value",
                suggestion="Use a number for greater_than comparisons"
            ))
        
        return issues
    
    def _validate_less_than_operator(self, field: str, value: Any, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, (int, float)):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: 'less_than' requires numeric value",
                suggestion="Use a number for less_than comparisons"
            ))
        
        return issues
    
    def _validate_between_operator(self, field: str, value: Any, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, list) or len(value) != 2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: 'between' requires array of 2 values",
                suggestion="Use format: [min_value, max_value]"
            ))
        
        return issues
    
    def _validate_in_range_operator(self, field: str, value: Any, index: int) -> List[ValidationIssue]:
        return self._validate_between_operator(field, value, index)
    
    def _validate_matches_operator(self, field: str, value: Any, index: int) -> List[ValidationIssue]:
        issues = []
        
        if not isinstance(value, str):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Condition {index + 1}: 'matches' requires string pattern",
                suggestion="Use a string regular expression pattern"
            ))
        else:
            try:
                re.compile(value)
            except re.error as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Condition {index + 1}: Invalid regex pattern: {e}",
                    suggestion="Fix the regular expression syntax"
                ))
        
        return issues
    
    def _validate_action_parameters(self, action_type: str, parameters: Dict, index: int) -> List[ValidationIssue]:
        """Validate action parameters"""
        issues = []
        
        if action_type == 'send_notification':
            if 'recipients' not in parameters:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Action {index + 1}: send_notification should have recipients",
                    suggestion="Add recipients parameter with email addresses or user IDs"
                ))
        
        elif action_type == 'trigger_recording':
            if 'duration' in parameters:
                duration = parameters['duration']
                if not isinstance(duration, (int, float)) or duration <= 0:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Action {index + 1}: Invalid recording duration",
                        suggestion="Use a positive number for recording duration in seconds"
                    ))
        
        elif action_type == 'create_alert':
            if 'priority' in parameters:
                priority = parameters['priority']
                valid_priorities = ['low', 'medium', 'high', 'critical']
                if priority not in valid_priorities:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Action {index + 1}: Unknown priority level '{priority}'",
                        suggestion=f"Use one of: {', '.join(valid_priorities)}"
                    ))
        
        return issues
    
    # Helper methods
    def _normalize_condition(self, condition: Dict) -> tuple:
        """Normalize condition for comparison"""
        return (condition.get('field'), condition.get('operator'), str(condition.get('value')))
    
    def _normalize_action(self, action: Dict) -> tuple:
        """Normalize action for comparison"""
        return (action.get('type'), json.dumps(action.get('parameters', {}), sort_keys=True))
    
    def _find_internal_contradictions(self, conditions: List[Dict]) -> List[str]:
        """Find contradictions within the same rule"""
        contradictions = []
        
        for i, condition1 in enumerate(conditions):
            for j, condition2 in enumerate(conditions[i+1:], i+1):
                if self._are_conditions_contradictory(condition1, condition2):
                    contradictions.append(f"Condition {i+1} contradicts condition {j+1}")
        
        return contradictions
    
    def _time_ranges_conflict(self, tc1: Dict, tc2: Dict) -> bool:
        """Check if two time conditions conflict"""
        # This is a simplified implementation
        # You could expand this to handle complex time range logic
        return False


# Testing harness for generated rules
class RuleTestHarness:
    """Test harness for validating generated rules"""
    
    def __init__(self, rule_data: Dict):
        self.rule_data = rule_data
        self.test_results = []
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests on the rule"""
        validator = RuleValidator()
        test_coverage = validator._generate_test_coverage(self.rule_data)
        
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': [],
            'coverage_score': test_coverage.get('coverage_score', 0.0)
        }
          # Run each test scenario
        for scenario in test_coverage.get('scenarios', []):
            test_result = await self._run_single_test(scenario)
            results['test_details'].append(test_result)
            results['total_tests'] += 1
            
            if test_result['passed']:
                results['passed_tests'] += 1
            else:
                results['failed_tests'] += 1
        
        results['success_rate'] = (results['passed_tests'] / results['total_tests']) if results['total_tests'] > 0 else 0.0
        
        return results
    
    async def _run_single_test(self, scenario: Dict) -> Dict[str, Any]:
        """Run a single test scenario"""
        try:
            from .rule_engine import evaluate_rule
        except ImportError:
            # Use the mock version
            evaluate_rule = globals().get('evaluate_rule', lambda conditions, event: True)
        
        scenario_type = scenario.get('type')
        description = scenario.get('description')
        test_event_data = scenario.get('event')
        
        try:
            # Convert test event data to CameraEvent object
            test_event = self._create_test_event(test_event_data)
            
            # Evaluate rule against test event
            conditions = self.rule_data.get('conditions', [])
            rule_triggered = evaluate_rule(conditions, test_event)
            
            # Determine if test passed
            expected_trigger = scenario_type == 'positive'
            test_passed = rule_triggered == expected_trigger
            
            return {
                'scenario_type': scenario_type,
                'description': description,
                'expected_trigger': expected_trigger,
                'actual_trigger': rule_triggered,
                'passed': test_passed,
                'event_data': test_event_data
            }
            
        except Exception as e:
            return {
                'scenario_type': scenario_type,
                'description': description,
                'expected_trigger': scenario_type == 'positive',
                'actual_trigger': False,
                'passed': False,
                'error': str(e),
                'event_data': test_event_data
            }
    
    def _create_test_event(self, event_data: Dict) -> CameraEvent:
        """Create a CameraEvent object from test data"""
        detections = []
        for det_data in event_data.get('detections', []):
            bbox = BoundingBox(x_min=0.1, y_min=0.1, x_max=0.5, y_max=0.5)
            detection = Detection(
                label=det_data.get('label', 'unknown'),
                confidence=det_data.get('confidence', 0.5),
                bounding_box=bbox
            )
            detections.append(detection)
        
        return CameraEvent(
            camera_id=event_data.get('camera_id', 'test-camera'),
            event_type=EventType.DETECTION,
            detections=detections,
            timestamp=datetime.fromisoformat(event_data.get('timestamp', datetime.now().isoformat())),
            metadata=event_data.get('metadata', {})
        )
