"""
AI Dashboard Service Entry Point

This file provides backward compatibility while the service has been modularized.
The actual application logic is now in the app/ package.
"""

from app import app

if __name__ == "__main__":
    import uvicorn
    from config.config import settings
    uvicorn.run(
        "app:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=True
    )
