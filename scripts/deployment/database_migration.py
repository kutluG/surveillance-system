#!/usr/bin/env python3
"""
Database migration script for surveillance system production deployment.
Handles schema updates, data migrations, and backup/restore operations.
"""

import os
import sys
import subprocess
import psycopg2
from datetime import datetime
import json
import shutil
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Database migration manager for production deployments."""
    
    def __init__(self, connection_params: Dict[str, str], migration_dir: str = "scripts/migrations"):
        self.connection_params = connection_params
        self.migration_dir = migration_dir
        self.backup_dir = f"/backups/db_migrations/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ensure directories exist
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.migration_dir, exist_ok=True)
    
    def get_connection(self):
        """Get database connection."""
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def backup_database(self, backup_name: Optional[str] = None) -> str:
        """Create full database backup before migration."""
        if not backup_name:
            backup_name = f"pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        logger.info(f"🗄️ Creating database backup: {backup_path}")
        
        # Create backup using pg_dump
        cmd = [
            'pg_dump',
            f"--host={self.connection_params.get('host', 'localhost')}",
            f"--port={self.connection_params.get('port', '5432')}",
            f"--username={self.connection_params['user']}",
            f"--dbname={self.connection_params['database']}",
            '--format=custom',
            '--no-password',
            '--verbose',
            f'--file={backup_path}.custom'
        ]
        
        # Set password via environment
        env = os.environ.copy()
        env['PGPASSWORD'] = self.connection_params['password']
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Also create SQL backup for manual inspection
            cmd_sql = cmd.copy()
            cmd_sql[-1] = backup_path  # Remove .custom
            cmd_sql.remove('--format=custom')
            
            subprocess.run(cmd_sql, env=env, check=True)
            
            logger.info(f"✅ Database backup completed: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ Database backup failed: {e}")
            raise
    
    def get_current_schema_version(self) -> int:
        """Get current database schema version."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Create migrations table if it doesn't exist
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        migration_name TEXT,
                        checksum TEXT
                    )
                """)
                conn.commit()
                
                # Get latest version
                cur.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
                return cur.fetchone()[0]
    
    def get_available_migrations(self) -> List[Dict]:
        """Get list of available migration files."""
        migrations = []
        
        if not os.path.exists(self.migration_dir):
            logger.warning(f"Migration directory not found: {self.migration_dir}")
            return migrations
        
        for filename in sorted(os.listdir(self.migration_dir)):
            if filename.endswith('.sql') and filename[0].isdigit():
                version = int(filename.split('_')[0])
                migrations.append({
                    'version': version,
                    'filename': filename,
                    'path': os.path.join(self.migration_dir, filename)
                })
        
        return sorted(migrations, key=lambda x: x['version'])
    
    def validate_migration(self, migration_path: str) -> bool:
        """Validate migration file syntax and structure."""
        try:
            with open(migration_path, 'r') as f:
                content = f.read()
            
            # Basic validation checks
            if not content.strip():
                logger.error(f"Empty migration file: {migration_path}")
                return False
            
            # Check for dangerous operations in production
            dangerous_operations = [
                'DROP TABLE',
                'DROP DATABASE',
                'TRUNCATE',
                'DELETE FROM',
                'ALTER TABLE ... DROP COLUMN'
            ]
            
            for operation in dangerous_operations:
                if operation in content.upper():
                    logger.warning(f"⚠️ Dangerous operation detected in {migration_path}: {operation}")
                    # Don't fail, but warn
            
            logger.info(f"✅ Migration validation passed: {migration_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration validation failed: {e}")
            return False
    
    def apply_migration(self, migration: Dict) -> bool:
        """Apply a single migration."""
        logger.info(f"📈 Applying migration {migration['version']}: {migration['filename']}")
        
        if not self.validate_migration(migration['path']):
            return False
        
        try:
            with open(migration['path'], 'r') as f:
                migration_sql = f.read()
            
            # Calculate checksum
            import hashlib
            checksum = hashlib.md5(migration_sql.encode()).hexdigest()
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Execute migration
                    cur.execute(migration_sql)
                    
                    # Record migration
                    cur.execute("""
                        INSERT INTO schema_migrations (version, migration_name, checksum)
                        VALUES (%s, %s, %s)
                    """, (migration['version'], migration['filename'], checksum))
                    
                    conn.commit()
            
            logger.info(f"✅ Migration {migration['version']} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration {migration['version']} failed: {e}")
            return False
    
    def rollback_migration(self, target_version: int) -> bool:
        """Rollback to a specific schema version."""
        logger.info(f"🔄 Rolling back to version {target_version}")
        
        current_version = self.get_current_schema_version()
        if target_version >= current_version:
            logger.warning(f"Target version {target_version} is not less than current {current_version}")
            return True
        
        # For safety, we'll restore from backup rather than run rollback scripts
        logger.warning("⚠️ Rollback requires manual intervention and backup restoration")
        logger.info("Use restore_backup() method with appropriate backup file")
        return False
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup."""
        logger.info(f"🔄 Restoring database from backup: {backup_path}")
        
        # Use custom format backup if available
        custom_backup = backup_path + '.custom'
        if os.path.exists(custom_backup):
            backup_path = custom_backup
            format_arg = '--format=custom'
        else:
            format_arg = '--format=plain'
        
        cmd = [
            'pg_restore',
            f"--host={self.connection_params.get('host', 'localhost')}",
            f"--port={self.connection_params.get('port', '5432')}",
            f"--username={self.connection_params['user']}",
            f"--dbname={self.connection_params['database']}",
            '--clean',
            '--if-exists',
            '--no-password',
            '--verbose'
        ]
        
        if format_arg == '--format=custom':
            cmd.append(backup_path)
        else:
            # For SQL files, use psql
            cmd = [
                'psql',
                f"--host={self.connection_params.get('host', 'localhost')}",
                f"--port={self.connection_params.get('port', '5432')}",
                f"--username={self.connection_params['user']}",
                f"--dbname={self.connection_params['database']}",
                '--file', backup_path
            ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.connection_params['password']
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Restore failed: {result.stderr}")
            
            logger.info("✅ Database restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database restore failed: {e}")
            return False
    
    def run_migrations(self, dry_run: bool = False) -> bool:
        """Run all pending migrations."""
        logger.info("🚀 Starting database migration process")
        
        current_version = self.get_current_schema_version()
        available_migrations = self.get_available_migrations()
        
        pending_migrations = [
            m for m in available_migrations 
            if m['version'] > current_version
        ]
        
        if not pending_migrations:
            logger.info("✅ No pending migrations")
            return True
        
        logger.info(f"📊 Found {len(pending_migrations)} pending migrations")
        
        if dry_run:
            logger.info("🔍 DRY RUN - No changes will be applied")
            for migration in pending_migrations:
                logger.info(f"Would apply: {migration['filename']}")
            return True
        
        # Create backup before migration
        backup_path = self.backup_database()
        
        # Apply migrations
        for migration in pending_migrations:
            if not self.apply_migration(migration):
                logger.error(f"❌ Migration failed: {migration['filename']}")
                logger.info(f"Backup available at: {backup_path}")
                return False
        
        logger.info("🎉 All migrations applied successfully")
        return True
    
    def health_check(self) -> Dict:
        """Perform database health check."""
        health_info = {
            'status': 'unknown',
            'schema_version': 0,
            'connection': False,
            'tables': [],
            'indexes': [],
            'size': '0 MB'
        }
        
        try:
            with self.get_connection() as conn:
                health_info['connection'] = True
                
                with conn.cursor() as cur:
                    # Schema version
                    health_info['schema_version'] = self.get_current_schema_version()
                    
                    # Table count
                    cur.execute("""
                        SELECT tablename FROM pg_tables 
                        WHERE schemaname = 'public'
                    """)
                    health_info['tables'] = [row[0] for row in cur.fetchall()]
                    
                    # Index count
                    cur.execute("""
                        SELECT indexname FROM pg_indexes 
                        WHERE schemaname = 'public'
                    """)
                    health_info['indexes'] = [row[0] for row in cur.fetchall()]
                    
                    # Database size
                    cur.execute("""
                        SELECT pg_size_pretty(pg_database_size(current_database()))
                    """)
                    health_info['size'] = cur.fetchone()[0]
                    
                    health_info['status'] = 'healthy'
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_info['status'] = 'unhealthy'
            health_info['error'] = str(e)
        
        return health_info


def create_sample_migrations():
    """Create sample migration files for surveillance system."""
    migration_dir = "scripts/migrations"
    os.makedirs(migration_dir, exist_ok=True)
    
    migrations = [
        {
            'version': '001',
            'name': 'initial_schema',
            'content': '''
-- Initial surveillance system schema
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    camera_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    description TEXT,
    confidence FLOAT,
    metadata JSONB,
    image_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cameras (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    url VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_camera_id ON events(camera_id);
CREATE INDEX idx_events_type ON events(event_type);
'''
        },
        {
            'version': '002',
            'name': 'add_user_management',
            'content': '''
-- Add user management tables
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
'''
        },
        {
            'version': '003',
            'name': 'add_analytics_tables',
            'content': '''
-- Add analytics and reporting tables
CREATE TABLE IF NOT EXISTS detection_analytics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    camera_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_count INTEGER DEFAULT 0,
    avg_confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_analytics_date_camera ON detection_analytics(date, camera_id);
CREATE INDEX idx_metrics_name_timestamp ON system_metrics(metric_name, timestamp);
'''
        }
    ]
    
    for migration in migrations:
        filename = f"{migration['version']}_{migration['name']}.sql"
        filepath = os.path.join(migration_dir, filename)
        
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(migration['content'].strip())
            logger.info(f"Created migration: {filename}")


def main():
    """Main migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration tool')
    parser.add_argument('--action', choices=['migrate', 'rollback', 'status', 'backup', 'restore', 'create-samples'], 
                       default='migrate', help='Action to perform')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--target-version', type=int, help='Target version for rollback')
    parser.add_argument('--backup-path', help='Backup file path for restore')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', default='5432', help='Database port')
    parser.add_argument('--database', default='events_db', help='Database name')
    parser.add_argument('--user', default='user', help='Database user')
    parser.add_argument('--password', help='Database password (or set PGPASSWORD env var)')
    
    args = parser.parse_args()
    
    # Get password from args or environment
    password = args.password or os.environ.get('PGPASSWORD')
    if not password:
        logger.error("Database password must be provided via --password or PGPASSWORD environment variable")
        sys.exit(1)
    
    connection_params = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': password
    }
    
    migrator = DatabaseMigrator(connection_params)
    
    try:
        if args.action == 'create-samples':
            create_sample_migrations()
            logger.info("✅ Sample migrations created")
            
        elif args.action == 'status':
            current_version = migrator.get_current_schema_version()
            available_migrations = migrator.get_available_migrations()
            health_info = migrator.health_check()
            
            print(f"\n📊 Database Status:")
            print(f"Current schema version: {current_version}")
            print(f"Available migrations: {len(available_migrations)}")
            print(f"Database size: {health_info.get('size', 'unknown')}")
            print(f"Tables: {len(health_info.get('tables', []))}")
            print(f"Health: {health_info.get('status', 'unknown')}")
            
        elif args.action == 'migrate':
            success = migrator.run_migrations(dry_run=args.dry_run)
            sys.exit(0 if success else 1)
            
        elif args.action == 'backup':
            backup_path = migrator.backup_database()
            print(f"Backup created: {backup_path}")
            
        elif args.action == 'restore':
            if not args.backup_path:
                logger.error("--backup-path required for restore action")
                sys.exit(1)
            success = migrator.restore_backup(args.backup_path)
            sys.exit(0 if success else 1)
            
        elif args.action == 'rollback':
            if not args.target_version:
                logger.error("--target-version required for rollback action")
                sys.exit(1)
            success = migrator.rollback_migration(args.target_version)
            sys.exit(0 if success else 1)
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
