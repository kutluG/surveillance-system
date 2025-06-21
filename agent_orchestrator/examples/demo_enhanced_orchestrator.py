"""
Example Application: Enhanced Agent Orchestrator with All Features

This example demonstrates how to use the enhanced agent orchestrator service
with database persistence, authentication, and Kafka event streaming.

Run this example to see:
1. Database connection and table creation
2. API key generation and authentication
3. Agent registration with events
4. Task creation and assignment
5. Event consumption and processing
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Enhanced modules
from database import init_database, get_db_session
from auth import APIKeyManager, APIKeyInfo
from kafka_integration import (
    init_kafka, shutdown_kafka, event_publisher, 
    consumer_manager, EventType, OrchestrationEvent
)
from db_service import AgentRepository, TaskRepository, create_agent_with_transaction
from models import AgentTypeEnum, TaskStatusEnum, TaskPriorityEnum
from migrate_db import run_migration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedOrchestratorExample:
    """Example usage of enhanced agent orchestrator."""
    
    def __init__(self):
        self.api_key_manager = APIKeyManager()
        self.demo_api_key = None
        self.demo_key_info = None
    
    async def initialize_system(self):
        """Initialize all system components."""
        logger.info("🚀 Initializing Enhanced Agent Orchestrator System")
        
        # 1. Initialize database
        logger.info("📊 Setting up database...")
        await init_database()
        await run_migration()
        logger.info("✅ Database initialized")
        
        # 2. Initialize Kafka
        logger.info("📡 Setting up Kafka integration...")
        kafka_success = await init_kafka()
        if kafka_success:
            logger.info("✅ Kafka initialized successfully")
        else:
            logger.warning("⚠️ Kafka initialization failed (continuing anyway)")
        
        # 3. Set up authentication
        logger.info("🔐 Setting up authentication...")
        self.demo_api_key, self.demo_key_info = self.api_key_manager.create_key(
            name="demo_key",
            permissions=["*"],  # All permissions for demo
            rate_limit=1000
        )
        logger.info(f"✅ API key created: {self.demo_key_info.key_id}")
        
        # 4. Register event handlers
        self._register_event_handlers()
        logger.info("✅ Event handlers registered")
        
        logger.info("🎉 System initialization complete!")
    
    def _register_event_handlers(self):
        """Register Kafka event handlers."""
        
        async def handle_agent_registered(event: OrchestrationEvent):
            agent_id = event.data.get('agent_id')
            agent_name = event.data.get('name')
            logger.info(f"🤖 Event: Agent '{agent_name}' registered with ID: {agent_id}")
        
        async def handle_task_assigned(event: OrchestrationEvent):
            task_id = event.data.get('task_id')
            agent_id = event.data.get('agent_id')
            logger.info(f"📋 Event: Task {task_id} assigned to agent {agent_id}")
        
        async def handle_system_health(event: OrchestrationEvent):
            status = event.data.get('status')
            logger.info(f"❤️ Event: System health check - Status: {status}")
        
        # Register handlers
        consumer_manager.register_handler(EventType.AGENT_REGISTERED, handle_agent_registered)
        consumer_manager.register_handler(EventType.TASK_ASSIGNED, handle_task_assigned)
        consumer_manager.register_handler(EventType.SYSTEM_HEALTH, handle_system_health)
    
    async def demonstrate_agent_registration(self):
        """Demonstrate agent registration with authentication and events."""
        logger.info("\n🤖 Demonstrating Agent Registration")
        
        # Simulate authenticated agent registration
        async with get_db_session() as db:
            agent_data = {
                "type": AgentTypeEnum.SURVEILLANCE.value,
                "name": "Demo Camera Agent",
                "endpoint": "http://demo-agent:8080",
                "capabilities": ["motion_detection", "face_recognition", "night_vision"],
                "metadata": {
                    "demo": True,
                    "location": "entrance",
                    "camera_model": "DemoCAM-2000"
                }
            }
            
            # Create agent with transaction
            logger.info("Creating agent with database transaction...")
            agent = await create_agent_with_transaction(agent_data)
            logger.info(f"✅ Agent created: {agent.id} - {agent.name}")
            
            # Publish registration event
            logger.info("Publishing agent registration event...")
            await event_publisher.publish_agent_registered(
                agent_id=str(agent.id),
                agent_data=agent_data,
                metadata={
                    "api_key_id": self.demo_key_info.key_id,
                    "demo": True,
                    "source": "demo_script"
                }
            )
            logger.info("✅ Agent registration event published")
            
            return agent
    
    async def demonstrate_task_operations(self, agent):
        """Demonstrate task creation and assignment."""
        logger.info("\n📋 Demonstrating Task Operations")
        
        async with get_db_session() as db:
            # Create a task
            task_data = {
                "type": "surveillance_monitoring",
                "name": "Monitor Entrance Area",
                "description": "Continuous monitoring of the main entrance for security",
                "priority": TaskPriorityEnum.HIGH.value,
                "required_capabilities": ["motion_detection"],
                "input_data": {
                    "camera_zone": "entrance",
                    "monitoring_duration": "24h",
                    "alert_threshold": "high"
                },
                "metadata": {
                    "demo": True,
                    "created_by": "demo_script"
                }
            }
            
            logger.info("Creating task...")
            task = await TaskRepository.create_task(task_data, db)
            await db.commit()
            logger.info(f"✅ Task created: {task.id} - {task.name}")
            
            # Assign task to agent
            logger.info(f"Assigning task to agent {agent.id}...")
            await TaskRepository.assign_task_to_agent(
                task_id=str(task.id),
                agent_id=str(agent.id),
                db=db
            )
            await db.commit()
            logger.info("✅ Task assigned to agent")
            
            # Publish task assignment event
            await event_publisher.publish_task_assigned(
                task_id=str(task.id),
                agent_id=str(agent.id),
                task_data={
                    "type": task.type,
                    "name": task.name,
                    "priority": task.priority
                },
                metadata={
                    "api_key_id": self.demo_key_info.key_id,
                    "demo": True
                }
            )
            logger.info("✅ Task assignment event published")
            
            return task
    
    async def demonstrate_authentication(self):
        """Demonstrate authentication features."""
        logger.info("\n🔐 Demonstrating Authentication")
        
        # Test API key validation
        logger.info("Testing API key validation...")
        validated_key = self.api_key_manager.validate_key(self.demo_api_key)
        if validated_key:
            logger.info(f"✅ API key valid - Key ID: {validated_key.key_id}")
            logger.info(f"   Permissions: {validated_key.permissions}")
            logger.info(f"   Rate limit: {validated_key.rate_limit} req/min")
        else:
            logger.error("❌ API key validation failed")
        
        # Test permission checking
        logger.info("Testing permission validation...")
        try:
            # This would be done automatically by the require_permission dependency
            if "*" in validated_key.permissions or "agent:register" in validated_key.permissions:
                logger.info("✅ Permission 'agent:register' granted")
            else:
                logger.warning("⚠️ Permission 'agent:register' denied")
        except Exception as e:
            logger.error(f"❌ Permission check failed: {e}")
    
    async def demonstrate_database_features(self):
        """Demonstrate database features."""
        logger.info("\n📊 Demonstrating Database Features")
        
        async with get_db_session() as db:
            # Get agent statistics
            logger.info("Fetching agent statistics...")
            stats = await AgentRepository.get_agent_statistics(db)
            logger.info(f"✅ Agent Statistics:")
            for key, value in stats.items():
                logger.info(f"   {key}: {value}")
            
            # List agents with filtering
            logger.info("Listing agents...")
            agents, total = await AgentRepository.list_agents(
                db=db,
                agent_type=AgentTypeEnum.SURVEILLANCE,
                limit=10,
                offset=0
            )
            logger.info(f"✅ Found {total} agents, showing {len(agents)}")
            for agent in agents:
                logger.info(f"   - {agent.name} ({agent.type}) - Status: {agent.status}")
    
    async def demonstrate_health_checks(self):
        """Demonstrate health check features."""
        logger.info("\n❤️ Demonstrating Health Checks")
        
        # Database health
        async with get_db_session() as db:
            try:
                result = await db.execute("SELECT 1 as health_check")
                health = result.scalar()
                if health == 1:
                    logger.info("✅ Database health check passed")
                else:
                    logger.warning("⚠️ Database health check failed")
            except Exception as e:
                logger.error(f"❌ Database health check error: {e}")
        
        # Kafka health (publish test event)
        try:
            success = await event_publisher.publish_system_health(
                status="healthy",
                metrics={
                    "timestamp": datetime.now().isoformat(),
                    "demo": True,
                    "test": "health_check"
                },
                metadata={"demo": True}
            )
            
            if success:
                logger.info("✅ Kafka health check passed")
            else:
                logger.warning("⚠️ Kafka health check failed")
                
        except Exception as e:
            logger.warning(f"⚠️ Kafka health check error: {e}")
    
    async def run_complete_demo(self):
        """Run the complete demonstration."""
        try:
            # Initialize system
            await self.initialize_system()
            
            # Wait a moment for initialization
            await asyncio.sleep(1)
            
            # Run demonstrations
            agent = await self.demonstrate_agent_registration()
            await self.demonstrate_task_operations(agent)
            await self.demonstrate_authentication()
            await self.demonstrate_database_features()
            await self.demonstrate_health_checks()
            
            logger.info("\n🎉 Demo completed successfully!")
            logger.info("📋 Summary:")
            logger.info("   ✅ Database persistence with transactions")
            logger.info("   ✅ API key authentication with permissions")
            logger.info("   ✅ Kafka event streaming")
            logger.info("   ✅ Agent registration and task assignment")
            logger.info("   ✅ Health monitoring")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise
        finally:
            # Cleanup
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("\n🧹 Cleaning up resources...")
        await shutdown_kafka()
        logger.info("✅ Cleanup completed")


async def main():
    """Run the enhanced orchestrator example."""
    logger.info("🚀 Starting Enhanced Agent Orchestrator Demo")
    
    demo = EnhancedOrchestratorExample()
    
    try:
        await demo.run_complete_demo()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        return 1
    
    logger.info("👋 Demo finished")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
