"""
LLM client for generating policy rules from natural language descriptions.
"""
import os
import json
import openai
from typing import Dict, Any

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

openai.api_key = OPENAI_API_KEY

SYSTEM_PROMPT = """You are a security policy expert. Given a natural language description of a security policy rule, generate a JSON object with:

- conditions: array of condition objects, each with:
  - field: the field to check (e.g., "event_type", "camera_id", "time_of_day", "detection_label")
  - operator: comparison operator ("equals", "contains", "greater_than", "less_than", "between")
  - value: the value(s) to compare against
  
- actions: array of action objects, each with:
  - type: action type ("send_notification", "create_alert", "trigger_recording")
  - parameters: object with action-specific parameters

Examples:
Input: "Alert security team when person detected in restricted area between 10 PM and 6 AM"
Output: {
  "conditions": [
    {"field": "detection_label", "operator": "equals", "value": "person"},
    {"field": "camera_id", "operator": "contains", "value": "restricted"},
    {"field": "time_of_day", "operator": "between", "value": ["22:00", "06:00"]}
  ],
  "actions": [
    {"type": "send_notification", "parameters": {"recipients": ["security@company.com"], "priority": "high"}}
  ]
}

Output ONLY valid JSON."""

def generate_rule_structure(description: str) -> Dict[str, Any]:
    """
    Call OpenAI to generate structured rule conditions and actions from description.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": description}
    ]
    
    resp = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=512,
    )
    
    text = resp.choices[0].message.content
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM output as JSON: {e}\nOutput was:\n{text}")