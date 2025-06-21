# Agent Orchestrator Examples

This directory contains demonstration files and usage examples for the Agent Orchestrator Service.

## Available Examples

### Demo Files (moved from root)
- **Circuit Breaker Demos**: Examples of circuit breaker pattern usage
- **Load Balancing Demos**: Load balancing algorithm demonstrations  
- **Distributed Orchestrator Demo**: Distributed coordination examples
- **Enhanced Orchestrator Demo**: Advanced orchestration features
- **Semantic Matching Demo**: Agent capability matching examples

### Usage Examples

#### Basic Agent Registration
```python
import asyncio
import httpx

async def register_agent_example():
    agent_data = {
        "type": "rag_agent",
        "name": "Advanced RAG Agent",
        "endpoint": "http://rag-service:8000",
        "capabilities": ["document_analysis", "question_answering"],
        "metadata": {"version": "1.0"}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8006/api/v1/agents", 
            json=agent_data
        )
        print(f"Agent registered: {response.json()}")

asyncio.run(register_agent_example())
```

#### Task Creation and Execution
```python
import asyncio
import httpx

async def task_execution_example():
    task_data = {
        "type": "document_analysis",
        "description": "Analyze security document for threats",
        "input_data": {"document_url": "https://example.com/doc.pdf"},
        "required_capabilities": ["document_analysis"],
        "priority": 1
    }
    
    async with httpx.AsyncClient() as client:
        # Create task
        response = await client.post(
            "http://localhost:8006/api/v1/tasks",
            json=task_data
        )
        task_id = response.json()["task_id"]
        print(f"Task created: {task_id}")
        
        # Execute task
        response = await client.post(
            f"http://localhost:8006/api/v1/tasks/{task_id}/execute"
        )
        print(f"Task result: {response.json()}")

asyncio.run(task_execution_example())
```

## Running Examples

1. Ensure the Agent Orchestrator Service is running:
   ```bash
   python main_clean.py
   ```

2. Run individual example files:
   ```bash
   python examples/demo_basic_usage.py
   ```

## Note

These examples are for demonstration purposes and may require specific service configurations or dependencies to run successfully.
