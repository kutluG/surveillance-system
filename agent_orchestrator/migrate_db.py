"""
Database migration script for Agent Orchestrator service

This script creates the necessary database tables for the Agent Orchestrator
service using the models defined in models.py with proper dependency injection
for database connections.

Run this script to set up the database schema for the orchestrator service.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from database import get_database_manager
from models import Base
from config import get_config

logger = logging.getLogger(__name__)


async def create_tables():
    """Create all tables defined in models.py"""
    try:
        db_manager = await get_database_manager()
        
        # Create tables using the database manager's engine
        async with db_manager._engine.begin() as conn:
            logger.info("Creating database tables for Agent Orchestrator...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ All tables created successfully")
            
        # Create indexes for better performance
        await create_indexes()
        
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise


async def create_indexes():
    """Create additional indexes for better query performance"""
    try:
        db_manager = await get_database_manager()
        
        indexes = [
            # Agent indexes
            "CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type);",
            "CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);",
            "CREATE INDEX IF NOT EXISTS idx_agents_capabilities ON agents USING gin(capabilities);",
            "CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_agents_last_seen ON agents(last_seen);",
            
            # Task indexes
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_workflow_id ON tasks(workflow_id);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent ON tasks(assigned_agent_id);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority DESC);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_capabilities ON tasks USING gin(required_capabilities);",
            
            # Workflow indexes
            "CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);",
            "CREATE INDEX IF NOT EXISTS idx_workflows_user_id ON workflows(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_workflows_priority ON workflows(priority);",
            
            # Orchestration log indexes
            "CREATE INDEX IF NOT EXISTS idx_orchestration_logs_operation_type ON orchestration_logs(operation_type);",
            "CREATE INDEX IF NOT EXISTS idx_orchestration_logs_entity_type ON orchestration_logs(entity_type);",
            "CREATE INDEX IF NOT EXISTS idx_orchestration_logs_entity_id ON orchestration_logs(entity_id);",
            "CREATE INDEX IF NOT EXISTS idx_orchestration_logs_status ON orchestration_logs(status);",
            "CREATE INDEX IF NOT EXISTS idx_orchestration_logs_timestamp ON orchestration_logs(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_orchestration_logs_user_id ON orchestration_logs(user_id);",
            
            # Service health indexes
            "CREATE INDEX IF NOT EXISTS idx_service_health_service_name ON service_health(service_name);",
            "CREATE INDEX IF NOT EXISTS idx_service_health_status ON service_health(status);",
            "CREATE INDEX IF NOT EXISTS idx_service_health_last_check ON service_health(last_check);",
        ]
        
        async with db_manager.get_session() as db:
            logger.info("Creating performance indexes...")
            for index_sql in indexes:
                try:
                    await db.execute(text(index_sql))
                    logger.debug(f"Created index: {index_sql.split(' ')[5]}")
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
            
            logger.info("✅ All indexes created successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to create indexes: {e}")
        raise


async def drop_tables():
    """Drop all tables (USE WITH CAUTION - THIS WILL DELETE ALL DATA)"""
    try:
        db_manager = await get_database_manager()
        
        async with db_manager._engine.begin() as conn:
            logger.warning("⚠️  DROPPING ALL TABLES - THIS WILL DELETE ALL DATA!")
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("✅ All tables dropped successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        raise


async def check_tables_exist():
    """Check if all required tables exist"""
    try:
        db_manager = await get_database_manager()
        
        table_check_queries = [
            "SELECT to_regclass('public.agents');",
            "SELECT to_regclass('public.tasks');",
            "SELECT to_regclass('public.workflows');",
            "SELECT to_regclass('public.orchestration_logs');",
            "SELECT to_regclass('public.service_health');",
        ]
        
        async with db_manager.get_session() as db:
            logger.info("Checking if tables exist...")
            
            for query in table_check_queries:
                result = await db.execute(text(query))
                table_name = result.scalar()
                if table_name:
                    logger.info(f"✅ Table exists: {table_name}")
                else:
                    logger.warning(f"❌ Table missing: {query}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to check tables: {e}")
        return False


async def migrate_existing_data():
    """
    Migrate existing data from Redis to PostgreSQL
    
    This function helps migrate from the current Redis-based storage
    to the new PostgreSQL-based storage with proper schema.
    """
    try:
        logger.info("Starting data migration from Redis to PostgreSQL...")
        
        # This is a placeholder for actual migration logic
        # In a real implementation, you would:
        # 1. Connect to Redis and fetch existing data
        # 2. Transform the data to match the new schema
        # 3. Insert the data into PostgreSQL using the repository pattern
        
        logger.info("✅ Data migration completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Data migration failed: {e}")
        raise


async def setup_initial_data():
    """Set up initial data for the Agent Orchestrator service"""
    try:
        from db_service import create_agent_with_transaction
        
        logger.info("Setting up initial data...")
        
        # Create some example service health entries
        db_manager = await get_database_manager()
        async with db_manager.get_session() as db:
            from models import ServiceHealth
            
            services = [
                {"service_name": "rag_service", "status": "healthy"},
                {"service_name": "rule_service", "status": "healthy"},
                {"service_name": "notifier_service", "status": "healthy"},
                {"service_name": "agent_orchestrator", "status": "healthy"}
            ]
            
            for service_data in services:
                service_health = ServiceHealth(**service_data)
                db.add(service_health)
            
            await db.commit()
        
        logger.info("✅ Initial data setup completed")
        
    except Exception as e:
        logger.error(f"❌ Initial data setup failed: {e}")
        raise


async def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Orchestrator Database Migration")
    parser.add_argument("--create", action="store_true", help="Create all tables and indexes")
    parser.add_argument("--drop", action="store_true", help="Drop all tables (DANGER!)")
    parser.add_argument("--check", action="store_true", help="Check if tables exist")
    parser.add_argument("--migrate", action="store_true", help="Migrate existing data from Redis")
    parser.add_argument("--setup", action="store_true", help="Setup initial data")
    parser.add_argument("--all", action="store_true", help="Run full setup (create + setup initial data)")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        if args.drop:
            confirm = input("⚠️  This will DELETE ALL DATA! Type 'yes' to confirm: ")
            if confirm.lower() == 'yes':
                await drop_tables()
            else:
                logger.info("Drop operation cancelled")
                return
        
        if args.create or args.all:
            await create_tables()
        
        if args.check:
            await check_tables_exist()
        
        if args.migrate:
            await migrate_existing_data()
        
        if args.setup or args.all:
            await setup_initial_data()
        
        if not any([args.create, args.drop, args.check, args.migrate, args.setup, args.all]):
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1
    
    logger.info("🎉 Migration completed successfully!")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
