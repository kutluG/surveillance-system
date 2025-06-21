"""
CLI tool for managing API keys in the Agent Orchestrator Service.

This tool allows administrators to create, list, and revoke API keys
for the Agent Orchestrator Service. It provides a command-line interface
for key management operations.

Usage:
    python api_key_manager.py create --name "Service Key" --permissions agent:read,agent:write
    python api_key_manager.py list
    python api_key_manager.py revoke --key-id key_12345678

Author: Agent Orchestrator Team
Version: 1.0.0
"""

import asyncio
import argparse
import sys
from typing import List, Optional
from datetime import datetime

from .auth import APIKeyManager, get_api_key_manager
from .config import get_config


def print_table(headers: List[str], rows: List[List[str]]):
    """Print a formatted table."""
    # Calculate column widths
    col_widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Print header
    header_row = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
    print(header_row)
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        row_str = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        print(row_str)


async def create_api_key(
    name: str,
    permissions: List[str],
    expires_in_days: Optional[int] = None,
    rate_limit: int = 100
):
    """Create a new API key."""
    try:
        api_key_manager = get_api_key_manager()
        
        api_key, key_info = api_key_manager.create_key(
            name=name,
            permissions=permissions,
            expires_in_days=expires_in_days,
            rate_limit=rate_limit
        )
        
        print("✅ API Key created successfully!")
        print(f"🔑 API Key: {api_key}")
        print(f"📋 Key ID: {key_info.key_id}")
        print(f"📝 Name: {key_info.name}")
        print(f"🛡️  Permissions: {', '.join(key_info.permissions)}")
        print(f"⏰ Created: {key_info.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if key_info.expires_at:
            print(f"⏳ Expires: {key_info.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("⏳ Expires: Never")
        print(f"🚦 Rate Limit: {key_info.rate_limit} requests/minute")
        print()
        print("⚠️  WARNING: Store this API key securely. It will not be shown again!")
        
    except Exception as e:
        print(f"❌ Failed to create API key: {e}")
        sys.exit(1)


async def list_api_keys():
    """List all API keys."""
    try:
        api_key_manager = get_api_key_manager()
        keys = api_key_manager.list_keys()
        
        if not keys:
            print("No API keys found.")
            return
        
        print(f"Found {len(keys)} API key(s):")
        print()
        
        headers = ["Key ID", "Name", "Status", "Permissions", "Created", "Expires", "Last Used"]
        rows = []
        
        for key in keys:
            status = "🟢 Active" if key.is_active else "🔴 Inactive"
            permissions = ", ".join(key.permissions)
            if len(permissions) > 30:
                permissions = permissions[:27] + "..."
            
            created = key.created_at.strftime('%Y-%m-%d')
            expires = key.expires_at.strftime('%Y-%m-%d') if key.expires_at else "Never"
            last_used = key.last_used.strftime('%Y-%m-%d') if key.last_used else "Never"
            
            rows.append([
                key.key_id,
                key.name,
                status,
                permissions,
                created,
                expires,
                last_used
            ])
        
        print_table(headers, rows)
        
    except Exception as e:
        print(f"❌ Failed to list API keys: {e}")
        sys.exit(1)


async def revoke_api_key(key_id: str):
    """Revoke an API key."""
    try:
        api_key_manager = get_api_key_manager()
        
        # Check if key exists
        key_info = api_key_manager.get_key_info(key_id)
        if not key_info:
            print(f"❌ API key '{key_id}' not found.")
            sys.exit(1)
        
        # Confirm revocation
        print(f"Are you sure you want to revoke API key '{key_info.name}' ({key_id})? [y/N]: ", end="")
        confirm = input().strip().lower()
        
        if confirm not in ['y', 'yes']:
            print("Revocation cancelled.")
            return
        
        # Revoke the key
        success = api_key_manager.revoke_key(key_id)
        
        if success:
            print(f"✅ API key '{key_info.name}' ({key_id}) has been revoked.")
        else:
            print(f"❌ Failed to revoke API key '{key_id}'.")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Failed to revoke API key: {e}")
        sys.exit(1)


async def show_key_info(key_id: str):
    """Show detailed information about an API key."""
    try:
        api_key_manager = get_api_key_manager()
        key_info = api_key_manager.get_key_info(key_id)
        
        if not key_info:
            print(f"❌ API key '{key_id}' not found.")
            sys.exit(1)
        
        print(f"API Key Information: {key_id}")
        print("=" * 50)
        print(f"📝 Name: {key_info.name}")
        print(f"🛡️  Permissions: {', '.join(key_info.permissions)}")
        print(f"📊 Status: {'🟢 Active' if key_info.is_active else '🔴 Inactive'}")
        print(f"⏰ Created: {key_info.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if key_info.expires_at:
            print(f"⏳ Expires: {key_info.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("⏳ Expires: Never")
        if key_info.last_used:
            print(f"🕐 Last Used: {key_info.last_used.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("🕐 Last Used: Never")
        print(f"🚦 Rate Limit: {key_info.rate_limit} requests/minute")
        print(f"🎯 Allowed Endpoints: {', '.join(key_info.allowed_endpoints)}")
        
    except Exception as e:
        print(f"❌ Failed to get key info: {e}")
        sys.exit(1)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="API Key Management CLI for Agent Orchestrator Service"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new API key')
    create_parser.add_argument('--name', required=True, help='Name for the API key')
    create_parser.add_argument(
        '--permissions',
        default='agent:read',
        help='Comma-separated list of permissions (default: agent:read)'
    )
    create_parser.add_argument(
        '--expires-in-days',
        type=int,
        help='Days until expiration (default: 30, use 0 for no expiration)'
    )
    create_parser.add_argument(
        '--rate-limit',
        type=int,
        default=100,
        help='Requests per minute allowed (default: 100)'
    )
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all API keys')
    
    # Revoke command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke an API key')
    revoke_parser.add_argument('--key-id', required=True, help='Key ID to revoke')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show API key information')
    info_parser.add_argument('--key-id', required=True, help='Key ID to show info for')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    try:
        config = get_config()
        print(f"🔧 Using configuration from: {config}")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        sys.exit(1)
    
    # Execute command
    if args.command == 'create':
        permissions = [p.strip() for p in args.permissions.split(',')]
        expires_in_days = args.expires_in_days if args.expires_in_days != 0 else None
        
        asyncio.run(create_api_key(
            name=args.name,
            permissions=permissions,
            expires_in_days=expires_in_days,
            rate_limit=args.rate_limit
        ))
        
    elif args.command == 'list':
        asyncio.run(list_api_keys())
        
    elif args.command == 'revoke':
        asyncio.run(revoke_api_key(args.key_id))
        
    elif args.command == 'info':
        asyncio.run(show_key_info(args.key_id))


if __name__ == '__main__':
    main()
