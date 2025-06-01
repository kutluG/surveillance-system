"""
Database engine and session setup for Event Ingest Service.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@postgres:5432/events_db"
)

# Create SQLAlchemy engine and session factory
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)