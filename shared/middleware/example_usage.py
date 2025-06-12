"""
Example usage of the rate limiting middleware in FastAPI microservices.

This file demonstrates how to integrate the rate limiting middleware
into your FastAPI applications.
"""

from fastapi import FastAPI, Request
from shared.middleware import add_rate_limiting, limiter

# Create FastAPI app
app = FastAPI(title="Example Service", version="1.0.0")

# Add rate limiting to the application
add_rate_limiting(app, service_name="example-service")

# Example endpoints with default rate limiting (100 requests/minute)
@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    """Health check endpoint (exempt from rate limiting)"""
    return {"status": "healthy"}

# Example endpoint with custom rate limiting
@app.get("/api/v1/contact")
@limiter.limit("10/minute")  # Custom limit: 10 requests per minute
async def contact_endpoint(request: Request):
    """Contact endpoint with custom rate limit"""
    return {"message": "Contact endpoint - limited to 10 requests/minute"}

@app.get("/api/v1/alerts") 
@limiter.limit("50/minute")  # Custom limit: 50 requests per minute
async def alerts_endpoint(request: Request):
    """Alerts endpoint with custom rate limit"""
    return {"message": "Alerts endpoint - limited to 50 requests/minute"}

# Example endpoint using default rate limiting
@app.get("/api/v1/data")
async def data_endpoint():
    """Data endpoint using default rate limit (100 requests/minute)"""
    return {"message": "Data endpoint with default rate limiting"}

# Example of accessing rate limit statistics
@app.get("/api/v1/rate-limit-stats")
async def get_rate_limit_statistics():
    """Get current rate limiting configuration and stats"""
    from shared.middleware import get_rate_limit_stats
    return get_rate_limit_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
