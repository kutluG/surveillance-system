import pytest
from rulegen_service.llm_client import generate_rule_structure
import json

def test_generate_rule_structure_mock(monkeypatch):
    # Mock OpenAI response
    class MockResponse:
        def __init__(self):
            self.choices = [type('Choice', (), {
                'message': type('Message', (), {
                    'content': json.dumps({
                        "conditions": [
                            {"field": "detection_label", "operator": "equals", "value": "person"}
                        ],
                        "actions": [
                            {"type": "send_notification", "parameters": {"recipients": ["admin@company.com"]}}
                        ]
                    })
                })
            })]
    
    def mock_create(**kwargs):
        return MockResponse()
    
    import openai
    monkeypatch.setattr(openai.ChatCompletion, "create", mock_create)
    
    result = generate_rule_structure("Alert when person detected")
    assert "conditions" in result
    assert "actions" in result
    assert len(result["conditions"]) == 1
    assert result["conditions"][0]["field"] == "detection_label"