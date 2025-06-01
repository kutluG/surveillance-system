"""
Data migration script from v1.0 to v2.0 schema.
"""
import psycopg2
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataMigration:
    """Handle data migration between versions."""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connection = None
    
    def connect(self):
        """Connect to database."""
        try:
            self.connection = psycopg2.connect(self.db_url)
            self.connection.autocommit = False
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from database."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from database")
    
    def backup_tables(self, tables: List[str]) -> str:
        """Create backup of existing tables."""
        backup_suffix = datetime.now().strftime("_%Y%m%d_%H%M%S")
        
        with self.connection.cursor() as cursor:
            for table in tables:
                backup_table = f"{table}_backup{backup_suffix}"
                cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM {table}")
                logger.info(f"Created backup table: {backup_table}")
        
        self.connection.commit()
        return backup_suffix
    
    def create_new_schema(self):
        """Create new schema for v2.0."""
        with self.connection.cursor() as cursor:
            # Add new columns to events table
            cursor.execute("""
                ALTER TABLE events 
                ADD COLUMN IF NOT EXISTS confidence_score FLOAT,
                ADD COLUMN IF NOT EXISTS processing_duration FLOAT,
                ADD COLUMN IF NOT EXISTS model_version VARCHAR(50)
            """)
            
            # Create new alert_history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    event_id UUID REFERENCES events(id),
                    alert_text TEXT NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    acknowledged_by VARCHAR(100)
                )
            """)
            
            # Create new user_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(100) NOT NULL,
                    session_token VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_confidence ON events(confidence_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_event_id ON alert_history(event_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)")
            
        self.connection.commit()
        logger.info("Created new schema for v2.0")
    
    def migrate_events_data(self):
        """Migrate events table data."""
        with self.connection.cursor() as cursor:
            # Get all events that need migration
            cursor.execute("""
                SELECT id, detections, metadata 
                FROM events 
                WHERE confidence_score IS NULL
            """)
            
            events = cursor.fetchall()
            logger.info(f"Migrating {len(events)} events")
            
            for event_id, detections, metadata in events:
                confidence_score = self._extract_confidence_score(detections)
                processing_duration = self._extract_processing_duration(metadata)
                model_version = self._extract_model_version(metadata)
                
                cursor.execute("""
                    UPDATE events 
                    SET confidence_score = %s, 
                        processing_duration = %s, 
                        model_version = %s
                    WHERE id = %s
                """, (confidence_score, processing_duration, model_version, event_id))
        
        self.connection.commit()
        logger.info("Migrated events data")
    
    def _extract_confidence_score(self, detections: List[Dict]) -> float:
        """Extract average confidence score from detections."""
        if not detections:
            return 0.0
        
        confidences = [d.get('confidence', 0.0) for d in detections]
        return sum(confidences) / len(confidences)
    
    def _extract_processing_duration(self, metadata: Dict) -> float:
        """Extract processing duration from metadata."""
        return metadata.get('processing_duration', 0.0) if metadata else 0.0
    
    def _extract_model_version(self, metadata: Dict) -> str:
        """Extract model version from metadata."""
        return metadata.get('model_version', 'v1.0') if metadata else 'v1.0'
    
    def migrate_notification_logs(self):
        """Migrate notification logs to new format."""
        with self.connection.cursor() as cursor:
            # Add new columns if they don't exist
            cursor.execute("""
                ALTER TABLE notification_logs 
                ADD COLUMN IF NOT EXISTS delivery_attempts INTEGER DEFAULT 1,
                ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS response_data JSONB
            """)
            
            # Update existing records
            cursor.execute("""
                UPDATE notification_logs 
                SET last_attempt_at = sent_at,
                    delivery_attempts = CASE WHEN sent_at IS NOT NULL THEN 1 ELSE 0 END
                WHERE last_attempt_at IS NULL
            """)
        
        self.connection.commit()
        logger.info("Migrated notification logs")
    
    def migrate_policy_rules(self):
        """Migrate policy rules to new format."""
        with self.connection.cursor() as cursor:
            # Add new columns for enhanced rules
            cursor.execute("""
                ALTER TABLE policy_rules 
                ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 100,
                ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb,
                ADD COLUMN IF NOT EXISTS execution_count INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS last_executed_at TIMESTAMP
            """)
            
            # Set default priorities based on rule content
            cursor.execute("""
                UPDATE policy_rules 
                SET priority = CASE 
                    WHEN rule_text ILIKE '%critical%' OR rule_text ILIKE '%emergency%' THEN 50
                    WHEN rule_text ILIKE '%high%' OR rule_text ILIKE '%urgent%' THEN 75
                    ELSE 100
                END
                WHERE priority = 100
            """)
        
        self.connection.commit()
        logger.info("Migrated policy rules")
    
    def update_version_info(self):
        """Update version information."""
        with self.connection.cursor() as cursor:
            # Create version info table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_info (
                    key VARCHAR(50) PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Update version
            cursor.execute("""
                INSERT INTO system_info (key, value) 
                VALUES ('schema_version', '2.0')
                ON CONFLICT (key) 
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
            """)
            
            # Record migration timestamp
            cursor.execute("""
                INSERT INTO system_info (key, value) 
                VALUES ('last_migration', %s)
                ON CONFLICT (key) 
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
            """, (datetime.now().isoformat(),))
        
        self.connection.commit()
        logger.info("Updated version information")
    
    def verify_migration(self) -> bool:
        """Verify migration was successful."""
        with self.connection.cursor() as cursor:
            # Check if new columns exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'events' 
                AND column_name IN ('confidence_score', 'processing_duration', 'model_version')
            """)
            new_columns = cursor.fetchall()
            
            if len(new_columns) != 3:
                logger.error("Missing new columns in events table")
                return False
            
            # Check if new tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('alert_history', 'user_sessions', 'system_info')
            """)
            new_tables = cursor.fetchall()
            
            if len(new_tables) != 3:
                logger.error("Missing new tables")
                return False
            
            # Check version info
            cursor.execute("SELECT value FROM system_info WHERE key = 'schema_version'")
            version = cursor.fetchone()
            
            if not version or version[0] != '2.0':
                logger.error("Schema version not updated")
                return False
            
            logger.info("Migration verification passed")
            return True
    
    def run_migration(self):
        """Run the complete migration process."""
        try:
            self.connect()
            
            logger.info("Starting data migration from v1.0 to v2.0")
            
            # Backup existing data
            backup_suffix = self.backup_tables(['events', 'notification_logs', 'policy_rules'])
            logger.info(f"Backup created with suffix: {backup_suffix}")
            
            # Run migration steps
            self.create_new_schema()
            self.migrate_events_data()
            self.migrate_notification_logs()
            self.migrate_policy_rules()
            self.update_version_info()
            
            # Verify migration
            if self.verify_migration():
                logger.info("Migration completed successfully")
                return True
            else:
                logger.error("Migration verification failed")
                # Rollback logic could go here
                return False
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

def main():
    """Main migration function."""
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/events_db")
    
    migration = DataMigration(db_url)
    
    if migration.run_migration():
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed")
        exit(1)

if __name__ == "__main__":
    main()