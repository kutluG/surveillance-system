"""
API Routers Package

Contains all FastAPI routers for different endpoints.
"""

from .dashboard import router as dashboard_router

__all__ = ["dashboard_router"]
