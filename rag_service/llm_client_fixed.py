"""
LLM client wrapper using OpenAI for generating alert text.
"""
import os
import json
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are a security camera analyst. "
    "Given a user query and a list of past CameraEvent contexts, "
    "generate a JSON object with keys:\n"
    " - alert_text: a concise human-readable alert message;\n"
    " - severity: one of 'low', 'medium', 'high', or 'critical';\n"
    " - evidence_ids: list of event_id strings from context that support the alert.\n"
    "Output ONLY valid JSON."
)

def generate_alert(query: str, contexts: list[dict]) -> dict:
    """
    Call OpenAI ChatCompletion to generate an alert based on query and contexts.
    Returns a dict parsed from the model's JSON output.
    """
    # Build the user message with contexts
    ctx_lines = []
    for idx, ctx in enumerate(contexts, start=1):
        ctx_lines.append(
            f"{idx}. id={ctx.get('event_id')}, "
            f"time={ctx.get('timestamp')}, "
            f"cam={ctx.get('camera_id')}, "
            f"type={ctx.get('event_type')}"
        )
    
    user_content = (
        f"User Query: {query}\n\n"
        f"Relevant Context Events:\n" + "\n".join(ctx_lines)
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=256,
    )
    text = resp.choices[0].message.content
    
    # Parse JSON output
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM output as JSON: {e}\nOutput was:\n{text}")
