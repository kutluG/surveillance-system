"""
Distributed Orchestrator Demonstration Script

This script demonstrates the key features of the distributed orchestrator including:
- State synchronization across multiple instances
- Leader election for coordinated actions
- Shard-based agent orchestration
- Event-driven coordination via Kafka
- Distributed task assignment with locking
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any

from distributed_orchestrator import (
    DistributedOrchestrator,
    CapabilityDomain,
    TaskPriority,
    OrchestratorRole,
    DistributedTask,
    AgentInfo
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DistributedOrchestratorDemo:
    """Demonstration of distributed orchestrator capabilities"""
    
    def __init__(self):
        self.orchestrators: List[DistributedOrchestrator] = []
        self.demo_agents: List[Dict[str, Any]] = []
        self.demo_tasks: List[Dict[str, Any]] = []
    
    async def setup_demo_environment(self):
        """Set up demonstration environment with multiple orchestrator instances"""
        logger.info("🚀 Setting up distributed orchestrator demonstration environment")
        
        # Create multiple orchestrator instances
        for i in range(3):
            orchestrator = DistributedOrchestrator(instance_id=f"orchestrator-{i+1}")
            orchestrator.hostname = f"host-{i+1}"
            orchestrator.port = 8000 + i
            self.orchestrators.append(orchestrator)
        
        # Initialize all orchestrator instances
        logger.info("Initializing orchestrator instances...")
        for i, orchestrator in enumerate(self.orchestrators):
            try:
                await orchestrator.initialize()
                logger.info(f"✅ Orchestrator {i+1} ({orchestrator.instance_id}) initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize orchestrator {i+1}: {e}")
        
        # Wait for leader election to settle
        logger.info("Waiting for leader election to complete...")
        await asyncio.sleep(5)
        
        # Check leader election results
        await self._show_leader_election_status()
    
    async def _show_leader_election_status(self):
        """Display current leader election status"""
        logger.info("\n📊 Leader Election Status:")
        logger.info("=" * 50)
        
        for i, orchestrator in enumerate(self.orchestrators):
            role = "🟢 LEADER" if orchestrator.leader_election.is_leader else "🔵 FOLLOWER"
            logger.info(f"Instance {i+1} ({orchestrator.instance_id}): {role}")
        
        # Get current leader from Redis
        if self.orchestrators:
            current_leader = await self.orchestrators[0].leader_election.get_current_leader()
            logger.info(f"Current cluster leader: {current_leader}")
    
    async def demonstrate_agent_registration(self):
        """Demonstrate distributed agent registration"""
        logger.info("\n🤖 Demonstrating Distributed Agent Registration")
        logger.info("=" * 50)
        
        # Define demo agents with different capabilities
        self.demo_agents = [
            {
                'agent_id': 'rag-agent-001',
                'capability_domain': CapabilityDomain.RAG_ANALYSIS.value,
                'endpoint': 'http://rag-service:8004/analyze',
                'load_score': 0.2,
                'status': 'active'
            },
            {
                'agent_id': 'rule-agent-001',
                'capability_domain': CapabilityDomain.RULE_GENERATION.value,
                'endpoint': 'http://rulegen-service:8006/generate',
                'load_score': 0.1,
                'status': 'active'
            },
            {
                'agent_id': 'notification-agent-001',
                'capability_domain': CapabilityDomain.NOTIFICATION.value,
                'endpoint': 'http://notifier:8007/send',
                'load_score': 0.3,
                'status': 'active'
            },
            {
                'agent_id': 'vms-agent-001',
                'capability_domain': CapabilityDomain.VMS_INTEGRATION.value,
                'endpoint': 'http://vms-service:8008/process',
                'load_score': 0.15,
                'status': 'active'
            }
        ]
        
        # Register agents across different orchestrator instances
        for i, agent_spec in enumerate(self.demo_agents):
            orchestrator = self.orchestrators[i % len(self.orchestrators)]
            
            try:
                success = await orchestrator.register_agent(agent_spec)
                if success:
                    logger.info(f"✅ Registered {agent_spec['agent_id']} on instance {orchestrator.instance_id}")
                else:
                    logger.error(f"❌ Failed to register {agent_spec['agent_id']}")
            except Exception as e:
                logger.error(f"❌ Error registering {agent_spec['agent_id']}: {e}")
        
        await asyncio.sleep(2)  # Allow propagation
        
        # Show agent distribution across instances
        await self._show_agent_distribution()
    
    async def _show_agent_distribution(self):
        """Display agent distribution across orchestrator instances"""
        logger.info("\n📋 Agent Distribution Across Instances:")
        logger.info("-" * 40)
        
        for orchestrator in self.orchestrators:
            agent_count = len(orchestrator.registered_agents)
            logger.info(f"Instance {orchestrator.instance_id}: {agent_count} agents")
            
            for agent_id, agent_info in orchestrator.registered_agents.items():
                logger.info(f"  - {agent_id} ({agent_info.capability_domain.value})")
    
    async def demonstrate_distributed_task_assignment(self):
        """Demonstrate distributed task assignment with locking"""
        logger.info("\n📋 Demonstrating Distributed Task Assignment")
        logger.info("=" * 50)
        
        # Define demo tasks with different capability requirements
        self.demo_tasks = [
            {
                'task_type': 'analyze_event',
                'capability_domain': CapabilityDomain.RAG_ANALYSIS.value,
                'priority': TaskPriority.HIGH.value,
                'payload': {
                    'camera_id': 'cam_001',
                    'event_type': 'person_detected',
                    'timestamp': datetime.utcnow().isoformat(),
                    'confidence': 0.95
                }
            },
            {
                'task_type': 'generate_rule',
                'capability_domain': CapabilityDomain.RULE_GENERATION.value,
                'priority': TaskPriority.NORMAL.value,
                'payload': {
                    'rule_description': 'Alert on person detection after hours',
                    'conditions': ['person_detected', 'after_hours'],
                    'actions': ['send_alert']
                }
            },
            {
                'task_type': 'send_notification',
                'capability_domain': CapabilityDomain.NOTIFICATION.value,
                'priority': TaskPriority.CRITICAL.value,
                'payload': {
                    'alert_type': 'security_breach',
                    'message': 'Unauthorized person detected in restricted area',
                    'recipients': ['security@company.com']
                }
            }
        ]
        
        # Assign tasks through different orchestrator instances
        assigned_tasks = []
        for i, task_spec in enumerate(self.demo_tasks):
            orchestrator = self.orchestrators[i % len(self.orchestrators)]
            
            try:
                logger.info(f"Assigning task {task_spec['task_type']} via instance {orchestrator.instance_id}")
                task_id = await orchestrator.assign_task(task_spec)
                assigned_tasks.append((task_id, orchestrator.instance_id))
                logger.info(f"✅ Task assigned with ID: {task_id}")
            except Exception as e:
                logger.error(f"❌ Error assigning task: {e}")
        
        await asyncio.sleep(2)  # Allow propagation
        
        # Show task assignment status
        await self._show_task_assignments(assigned_tasks)
    
    async def _show_task_assignments(self, assigned_tasks: List[tuple]):
        """Display task assignment status"""
        logger.info("\n📊 Task Assignment Status:")
        logger.info("-" * 40)
        
        for task_id, assigning_instance in assigned_tasks:
            # Check task status across all instances
            for orchestrator in self.orchestrators:
                if task_id in orchestrator.active_tasks:
                    task = orchestrator.active_tasks[task_id]
                    logger.info(f"Task {task_id[:8]}... ({task.task_type}):")
                    logger.info(f"  - Assigned to: {task.assigned_to}")
                    logger.info(f"  - Status: {task.status}")
                    logger.info(f"  - Priority: {task.priority.value}")
                    logger.info(f"  - Instance: {assigning_instance}")
                    break
    
    async def demonstrate_leader_failover(self):
        """Demonstrate leader failover scenario"""
        logger.info("\n🔄 Demonstrating Leader Failover")
        logger.info("=" * 50)
        
        # Find current leader
        current_leader = None
        leader_orchestrator = None
        
        for orchestrator in self.orchestrators:
            if orchestrator.leader_election.is_leader:
                current_leader = orchestrator.instance_id
                leader_orchestrator = orchestrator
                break
        
        if not current_leader:
            logger.warning("⚠️ No current leader found!")
            return
        
        logger.info(f"Current leader: {current_leader}")
        
        # Simulate leader failure by stopping its election process
        logger.info("Simulating leader failure...")
        await leader_orchestrator.leader_election.stop_election()
        
        # Wait for new election
        logger.info("Waiting for new leader election...")
        await asyncio.sleep(10)
        
        # Check new leader
        await self._show_leader_election_status()
        
        # Restart the failed leader
        logger.info("Restarting failed leader...")
        await leader_orchestrator.leader_election.start_election()
        await asyncio.sleep(5)
        
        # Final status
        logger.info("Final leader election status:")
        await self._show_leader_election_status()
    
    async def demonstrate_cluster_coordination(self):
        """Demonstrate cluster-wide coordination via Kafka events"""
        logger.info("\n🌐 Demonstrating Cluster Coordination")
        logger.info("=" * 50)
        
        # Get cluster status from different instances
        for i, orchestrator in enumerate(self.orchestrators):
            try:
                status = await orchestrator.get_cluster_status()
                logger.info(f"\nCluster status from instance {i+1}:")
                logger.info(f"  - Total instances: {status['total_instances']}")
                logger.info(f"  - Current leader: {status['current_leader']}")
                logger.info(f"  - Total active tasks: {status['total_active_tasks']}")
                logger.info(f"  - Agent capabilities: {status['agent_capabilities']}")
            except Exception as e:
                logger.error(f"❌ Error getting cluster status from instance {i+1}: {e}")
    
    async def demonstrate_distributed_locking(self):
        """Demonstrate distributed locking mechanism"""
        logger.info("\n🔒 Demonstrating Distributed Locking")
        logger.info("=" * 50)
        
        # Simulate concurrent task assignment attempts
        lock_resource = "critical_resource_001"
        
        async def attempt_lock(orchestrator, attempt_id):
            try:
                logger.info(f"Attempt {attempt_id} trying to acquire lock on {orchestrator.instance_id}")
                async with orchestrator.distributed_lock(lock_resource, timeout=5):
                    logger.info(f"✅ Attempt {attempt_id} acquired lock on {orchestrator.instance_id}")
                    await asyncio.sleep(2)  # Simulate work
                    logger.info(f"🔓 Attempt {attempt_id} releasing lock on {orchestrator.instance_id}")
            except Exception as e:
                logger.error(f"❌ Attempt {attempt_id} failed to acquire lock: {e}")
        
        # Create concurrent lock attempts
        tasks = []
        for i, orchestrator in enumerate(self.orchestrators):
            task = asyncio.create_task(attempt_lock(orchestrator, i+1))
            tasks.append(task)
        
        # Wait for all attempts to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def cleanup_demo_environment(self):
        """Clean up demonstration environment"""
        logger.info("\n🧹 Cleaning up demonstration environment")
        logger.info("=" * 50)
        
        for i, orchestrator in enumerate(self.orchestrators):
            try:
                await orchestrator.shutdown()
                logger.info(f"✅ Orchestrator {i+1} shutdown complete")
            except Exception as e:
                logger.error(f"❌ Error shutting down orchestrator {i+1}: {e}")
    
    async def run_complete_demonstration(self):
        """Run the complete distributed orchestrator demonstration"""
        try:
            logger.info("🎯 Starting Distributed Orchestrator Demonstration")
            logger.info("=" * 60)
            
            # Setup
            await self.setup_demo_environment()
            
            # Demonstrate key features
            await self.demonstrate_agent_registration()
            await self.demonstrate_distributed_task_assignment()
            await self.demonstrate_cluster_coordination()
            await self.demonstrate_distributed_locking()
            await self.demonstrate_leader_failover()
            
            logger.info("\n🎉 Demonstration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Demonstration failed: {e}")
        finally:
            # Cleanup
            await self.cleanup_demo_environment()

async def main():
    """Main demonstration function"""
    demo = DistributedOrchestratorDemo()
    await demo.run_complete_demonstration()

if __name__ == "__main__":
    asyncio.run(main())
