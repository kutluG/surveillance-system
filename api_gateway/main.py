"""
Enhanced API Gateway for Surveillance System
Routes requests to appropriate microservices including new AI-enhanced services
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import asyncio
import logging
from typing import Dict, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enhanced Surveillance System API Gateway",
    description="Central API gateway routing requests to all surveillance system services",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service registry with all services including enhanced ones
SERVICE_REGISTRY = {
    # Core Services
    "edge": "http://edge_service:8000",
    "mqtt": "http://mqtt_kafka_bridge:8000", 
    "ingest": "http://ingest_service:8000",
    "rag": "http://rag_service:8000",
    "prompt": "http://prompt_service:8000",
    "rulegen": "http://rulegen_service:8000",
    "notifier": "http://notifier:8000",
    "vms": "http://vms_service:8000",
    
    # Enhanced AI Services
    "enhanced-prompt": "http://enhanced_prompt_service:8000",
    "websocket": "http://websocket_service:8000",
    "agent-orchestrator": "http://agent_orchestrator:8000",
    "rule-builder": "http://rule_builder_service:8000",
    "advanced-rag": "http://advanced_rag_service:8000",
    "ai-dashboard": "http://ai_dashboard_service:8000",
    "voice": "http://voice_interface_service:8000"
}

# Service health status cache
service_health_cache = {}

async def check_service_health(service_name: str, service_url: str) -> bool:
    """Check if a service is healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url}/health")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Health check failed for {service_name}: {str(e)}")
        return False

async def proxy_request(service_url: str, path: str, method: str, 
                       body: bytes = None, headers: Dict = None, 
                       params: Dict = None) -> tuple:
    """Proxy request to target service"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            full_url = f"{service_url}{path}"
            
            # Prepare headers (exclude host header)
            proxy_headers = {}
            if headers:
                for key, value in headers.items():
                    if key.lower() not in ['host', 'content-length']:
                        proxy_headers[key] = value
            
            # Make request
            if method.upper() == "GET":
                response = await client.get(full_url, headers=proxy_headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(full_url, content=body, headers=proxy_headers, params=params)
            elif method.upper() == "PUT":
                response = await client.put(full_url, content=body, headers=proxy_headers, params=params)
            elif method.upper() == "DELETE":
                response = await client.delete(full_url, headers=proxy_headers, params=params)
            elif method.upper() == "PATCH":
                response = await client.patch(full_url, content=body, headers=proxy_headers, params=params)
            else:
                return 405, {"error": "Method not allowed"}, {}
            
            return response.status_code, response.content, dict(response.headers)
            
    except httpx.TimeoutException:
        logger.error(f"Timeout when proxying to {service_url}{path}")
        return 504, {"error": "Gateway timeout"}, {}
    except Exception as e:
        logger.error(f"Error proxying to {service_url}{path}: {str(e)}")
        return 502, {"error": "Bad gateway"}, {}

@app.get("/health")
async def gateway_health():
    """Gateway health check"""
    return {"status": "healthy", "gateway": "enhanced-surveillance-api-gateway"}

@app.get("/services/status")
async def services_status():
    """Get status of all services"""
    status = {}
    
    for service_name, service_url in SERVICE_REGISTRY.items():
        is_healthy = await check_service_health(service_name, service_url)
        status[service_name] = {
            "url": service_url,
            "healthy": is_healthy,
            "status": "online" if is_healthy else "offline"
        }
        service_health_cache[service_name] = is_healthy
    
    return {
        "gateway": "healthy",
        "services": status,
        "total_services": len(SERVICE_REGISTRY),
        "healthy_services": sum(1 for s in status.values() if s["healthy"])
    }

# Core service routes
@app.api_route("/api/edge/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_edge(request: Request, path: str):
    """Proxy requests to Edge Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["edge"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.api_route("/api/rag/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_rag(request: Request, path: str):
    """Proxy requests to RAG Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["rag"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.api_route("/api/prompt/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_prompt(request: Request, path: str):
    """Proxy requests to Prompt Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["prompt"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

# Enhanced AI service routes
@app.api_route("/api/enhanced-prompt/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_enhanced_prompt(request: Request, path: str):
    """Proxy requests to Enhanced Prompt Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["enhanced-prompt"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.api_route("/api/agent-orchestrator/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_agent_orchestrator(request: Request, path: str):
    """Proxy requests to Agent Orchestrator"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["agent-orchestrator"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.api_route("/api/rule-builder/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_rule_builder(request: Request, path: str):
    """Proxy requests to Rule Builder Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["rule-builder"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.api_route("/api/advanced-rag/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_advanced_rag(request: Request, path: str):
    """Proxy requests to Advanced RAG Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["advanced-rag"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.api_route("/api/ai-dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_ai_dashboard(request: Request, path: str):
    """Proxy requests to AI Dashboard Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["ai-dashboard"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.api_route("/api/voice/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_voice(request: Request, path: str):
    """Proxy requests to Voice Interface Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["voice"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.api_route("/api/vms/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_vms(request: Request, path: str):
    """Proxy requests to VMS Service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["vms"], f"/{path}",
        request.method, body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

# WebSocket proxy for real-time features
@app.websocket("/ws/{client_id}")
async def websocket_proxy(websocket: WebSocket, client_id: str):
    """WebSocket proxy to WebSocket service"""
    await websocket.accept()
    
    try:
        # Connect to websocket service
        websocket_url = SERVICE_REGISTRY["websocket"].replace("http://", "ws://")
        
        import websockets
        async with websockets.connect(f"{websocket_url}/ws/{client_id}") as backend_ws:
            # Relay messages between client and backend
            async def relay_to_backend():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await backend_ws.send(data)
                except Exception as e:
                    logger.error(f"Error relaying to backend: {e}")
            
            async def relay_to_client():
                try:
                    while True:
                        data = await backend_ws.recv()
                        await websocket.send_text(data)
                except Exception as e:
                    logger.error(f"Error relaying to client: {e}")
            
            # Run both relay tasks
            await asyncio.gather(
                relay_to_backend(),
                relay_to_client(),
                return_exceptions=True
            )
            
    except Exception as e:
        logger.error(f"WebSocket proxy error: {e}")
        await websocket.close(code=1000)

# Unified API endpoints for common operations
@app.post("/api/chat")
async def unified_chat(request: Request):
    """Unified chat endpoint that routes to enhanced prompt service"""
    body = await request.body()
    status_code, content, headers = await proxy_request(
        SERVICE_REGISTRY["enhanced-prompt"], "/conversation/query",
        "POST", body, dict(request.headers), dict(request.query_params)
    )
    return JSONResponse(content=content, status_code=status_code, headers=headers)

@app.get("/api/analytics/overview")
async def analytics_overview():
    """Get comprehensive analytics overview from AI dashboard"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get data from AI dashboard service
            response = await client.get(f"{SERVICE_REGISTRY['ai-dashboard']}/analytics/overview")
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Analytics service unavailable")
                
    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        raise HTTPException(status_code=503, detail="Analytics service error")

@app.get("/api/system/status")
async def system_status():
    """Get comprehensive system status"""
    # Get service statuses
    services_data = await services_status()
    
    # Get analytics overview if available
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            analytics_response = await client.get(f"{SERVICE_REGISTRY['ai-dashboard']}/analytics/system-health")
            analytics_data = analytics_response.json() if analytics_response.status_code == 200 else {}
    except:
        analytics_data = {}
    
    return {
        "timestamp": asyncio.get_event_loop().time(),
        "services": services_data,
        "analytics": analytics_data,
        "gateway": {
            "version": "2.0.0",
            "status": "healthy"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
