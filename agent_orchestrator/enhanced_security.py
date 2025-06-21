"""
Enhanced Security Module for Agent Orchestrator Service

This module provides comprehensive security features including:
- OAuth2 authentication with JWT tokens
- Role-Based Access Control (RBAC)
- API key rotation and management
- Comprehensive audit logging
- Security event monitoring

Author: Agent Orchestrator Team
Version: 2.0.0
"""

import json
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Union
from enum import Enum
from contextlib import asynccontextmanager

from fastapi import HTTPException, Security, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from pydantic import BaseModel, Field
import jwt
import logging
from passlib.context import CryptContext

from .config import Config

logger = logging.getLogger(__name__)

# Initialize audit logger
audit_logger = None

def get_audit_logger():
    """Get or create audit logger instance"""
    global audit_logger
    if audit_logger is None:
        audit_logger = AuditLogger()
    return audit_logger

# Security configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
security = HTTPBearer(scheme_name="Bearer Authentication", auto_error=False)


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    SERVICE = "service"
    AGENT = "agent"


class AgentType(str, Enum):
    """Agent types for specialized access control"""
    RAG_AGENT = "rag_agent"
    RULE_AGENT = "rule_agent"
    NOTIFICATION_AGENT = "notification_agent"
    MONITORING_AGENT = "monitoring_agent"
    ANALYSIS_AGENT = "analysis_agent"


class Permission(str, Enum):
    """Granular permissions"""
    # Agent permissions
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_EXECUTE = "agent:execute"
    
    # Task permissions
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    
    # System permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_HEALTH = "system:health"
    SYSTEM_LOGS = "system:logs"
    
    # Security permissions
    SECURITY_MANAGE = "security:manage"
    SECURITY_AUDIT = "security:audit"
    
    # Admin permissions
    ADMIN_ALL = "admin:all"


class SecurityEvent(str, Enum):
    """Security event types for audit logging"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    API_KEY_CREATED = "api_key_created"
    API_KEY_ROTATED = "api_key_rotated"
    API_KEY_REVOKED = "api_key_revoked"
    PERMISSION_DENIED = "permission_denied"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class User(BaseModel):
    """User model for authentication"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: List[UserRole] = Field(default_factory=list)
    permissions: List[Permission] = Field(default_factory=list)
    agent_types: List[AgentType] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    login_attempts: int = 0
    locked_until: Optional[datetime] = None


class Token(BaseModel):
    """JWT token model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: List[str] = Field(default_factory=list)


class TokenData(BaseModel):
    """Token payload data"""
    username: Optional[str] = None
    roles: List[UserRole] = Field(default_factory=list)
    permissions: List[Permission] = Field(default_factory=list)
    agent_types: List[AgentType] = Field(default_factory=list)
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None  # JWT ID for token tracking


class APIKeyInfo(BaseModel):
    """Enhanced API key information"""
    key_id: str
    name: str
    description: Optional[str] = None
    roles: List[UserRole] = Field(default_factory=list)
    permissions: List[Permission] = Field(default_factory=list)
    agent_types: List[AgentType] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    rotation_interval_days: int = 90
    is_active: bool = True
    rate_limit: int = 100
    allowed_endpoints: List[str] = Field(default_factory=list)
    allowed_ips: List[str] = Field(default_factory=list)
    max_concurrent_requests: int = 10
    usage_count: int = 0


class AuditLog(BaseModel):
    """Audit log entry"""
    id: str = Field(default_factory=lambda: secrets.token_hex(16))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: SecurityEvent
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    risk_score: int = 0  # 0-100, higher = more suspicious


class SecurityError(HTTPException):
    """Base security error"""
    def __init__(self, status_code: int, detail: str, headers: Dict[str, str] = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers or {})


class AuthenticationError(SecurityError):
    """Authentication failed"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(SecurityError):
    """Authorization failed"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class RateLimitError(SecurityError):
    """Rate limit exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "60"}
        )


class RolePermissionManager:
    """Manages role-based permissions"""
    
    def __init__(self):
        self._role_permissions = self._initialize_role_permissions()
        self._agent_type_permissions = self._initialize_agent_type_permissions()
    
    def _initialize_role_permissions(self) -> Dict[UserRole, Set[Permission]]:
        """Initialize default role permissions"""
        return {
            UserRole.ADMIN: {
                Permission.ADMIN_ALL,
                Permission.SECURITY_MANAGE,
                Permission.SECURITY_AUDIT,
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_METRICS,
                Permission.SYSTEM_HEALTH,
                Permission.SYSTEM_LOGS,
                Permission.AGENT_CREATE,
                Permission.AGENT_READ,
                Permission.AGENT_UPDATE,
                Permission.AGENT_DELETE,
                Permission.AGENT_EXECUTE,
                Permission.TASK_CREATE,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
                Permission.TASK_DELETE,
                Permission.TASK_ASSIGN,
            },
            UserRole.OPERATOR: {
                Permission.AGENT_CREATE,
                Permission.AGENT_READ,
                Permission.AGENT_UPDATE,
                Permission.AGENT_EXECUTE,
                Permission.TASK_CREATE,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
                Permission.TASK_ASSIGN,
                Permission.SYSTEM_METRICS,
                Permission.SYSTEM_HEALTH,
            },
            UserRole.VIEWER: {
                Permission.AGENT_READ,
                Permission.TASK_READ,
                Permission.SYSTEM_METRICS,
                Permission.SYSTEM_HEALTH,
            },
            UserRole.SERVICE: {
                Permission.AGENT_CREATE,
                Permission.AGENT_READ,
                Permission.AGENT_EXECUTE,
                Permission.TASK_CREATE,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
                Permission.SYSTEM_METRICS,
            },
            UserRole.AGENT: {
                Permission.AGENT_READ,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
            },
        }
    
    def _initialize_agent_type_permissions(self) -> Dict[AgentType, Set[Permission]]:
        """Initialize agent type specific permissions"""
        return {
            AgentType.RAG_AGENT: {
                Permission.AGENT_READ,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
            },
            AgentType.RULE_AGENT: {
                Permission.AGENT_READ,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
                Permission.SYSTEM_METRICS,
            },
            AgentType.NOTIFICATION_AGENT: {
                Permission.AGENT_READ,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
            },
            AgentType.MONITORING_AGENT: {
                Permission.AGENT_READ,
                Permission.TASK_READ,
                Permission.SYSTEM_METRICS,
                Permission.SYSTEM_HEALTH,
            },
            AgentType.ANALYSIS_AGENT: {
                Permission.AGENT_READ,
                Permission.TASK_READ,
                Permission.TASK_UPDATE,
                Permission.SYSTEM_METRICS,
            },
        }
    
    def get_role_permissions(self, role: UserRole) -> Set[Permission]:
        """Get permissions for a role"""
        return self._role_permissions.get(role, set()).copy()
    
    def get_agent_type_permissions(self, agent_type: AgentType) -> Set[Permission]:
        """Get permissions for an agent type"""
        return self._agent_type_permissions.get(agent_type, set()).copy()
    
    def get_user_permissions(self, user: User) -> Set[Permission]:
        """Get all permissions for a user"""
        permissions = set(user.permissions)
        
        # Add role-based permissions
        for role in user.roles:
            permissions.update(self.get_role_permissions(role))
        
        # Add agent type permissions
        for agent_type in user.agent_types:
            permissions.update(self.get_agent_type_permissions(agent_type))
        
        return permissions
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        user_permissions = self.get_user_permissions(user)
        
        # Check for admin override
        if Permission.ADMIN_ALL in user_permissions:
            return True
        
        return permission in user_permissions
    
    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = self.get_user_permissions(user)
        
        # Check for admin override
        if Permission.ADMIN_ALL in user_permissions:
            return True
        
        return any(perm in user_permissions for perm in permissions)


class AuditLogger:
    """Comprehensive audit logging"""
    
    def __init__(self):
        self.audit_logs: List[AuditLog] = []
        self.logger = logging.getLogger("security.audit")
    
    async def log_event(
        self,
        event_type: SecurityEvent,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        details: Dict[str, Any] = None,
        risk_score: int = 0
    ) -> AuditLog:
        """Log a security event"""
        
        audit_entry = AuditLog(
            event_type=event_type,
            user_id=user_id,
            api_key_id=api_key_id,
            details=details or {},
            risk_score=risk_score
        )
        
        if request:
            audit_entry.ip_address = request.client.host if request.client else None
            audit_entry.user_agent = request.headers.get("User-Agent")
            audit_entry.endpoint = str(request.url.path)
            audit_entry.method = request.method
        
        self.audit_logs.append(audit_entry)
        
        # Log to standard logger as well
        self.logger.info(
            f"Security Event: {event_type.value} | "
            f"User: {user_id} | API Key: {api_key_id} | "
            f"IP: {audit_entry.ip_address} | "
            f"Endpoint: {audit_entry.endpoint} | "
            f"Risk: {risk_score}"
        )
        
        # Trigger alerts for high-risk events
        if risk_score >= 80:
            await self._trigger_security_alert(audit_entry)
        
        return audit_entry
    
    async def _trigger_security_alert(self, audit_entry: AuditLog):
        """Trigger security alerts for high-risk events"""
        self.logger.warning(
            f"HIGH RISK SECURITY EVENT: {audit_entry.event_type.value} | "
            f"Details: {audit_entry.details} | "
            f"Risk Score: {audit_entry.risk_score}"
        )
        # TODO: Integrate with alerting system
    
    def get_logs(
        self,
        event_type: Optional[SecurityEvent] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Retrieve audit logs with filtering"""
        logs = self.audit_logs
        
        if event_type:
            logs = [log for log in logs if log.event_type == event_type]
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        
        if since:
            logs = [log for log in logs if log.timestamp >= since]
        
        # Sort by timestamp (newest first) and limit
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        return logs[:limit]
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics from audit logs"""
        now = datetime.utcnow()
        last_24h = now - timedelta(days=1)
        last_7d = now - timedelta(days=7)
        
        recent_logs = [log for log in self.audit_logs if log.timestamp >= last_24h]
        weekly_logs = [log for log in self.audit_logs if log.timestamp >= last_7d]
        
        return {
            "total_events": len(self.audit_logs),
            "events_24h": len(recent_logs),
            "events_7d": len(weekly_logs),
            "failed_logins_24h": len([
                log for log in recent_logs 
                if log.event_type == SecurityEvent.LOGIN_FAILURE
            ]),
            "high_risk_events_24h": len([
                log for log in recent_logs 
                if log.risk_score >= 80
            ]),
            "top_events_24h": self._get_top_events(recent_logs),
            "top_ips_24h": self._get_top_ips(recent_logs),
        }
    
    def _get_top_events(self, logs: List[AuditLog]) -> Dict[str, int]:
        """Get top event types from logs"""
        event_counts = {}
        for log in logs:
            event_counts[log.event_type.value] = event_counts.get(log.event_type.value, 0) + 1
        return dict(sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    def _get_top_ips(self, logs: List[AuditLog]) -> Dict[str, int]:
        """Get top IP addresses from logs"""
        ip_counts = {}
        for log in logs:
            if log.ip_address:
                ip_counts[log.ip_address] = ip_counts.get(log.ip_address, 0) + 1
        return dict(sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10])


# Enhanced OAuth2 and JWT Token Management
class TokenManager:
    """Enhanced JWT token management with refresh tokens and blacklisting"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.blacklisted_tokens: Set[str] = set()
        self.active_refresh_tokens: Dict[str, Dict] = {}  # jti -> user_info
        
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Add standard JWT claims
        jti = secrets.token_urlsafe(32)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti,
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        jti = secrets.token_urlsafe(32)
        
        to_encode = {
            "sub": user_data.get("sub"),
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti,
            "type": "refresh"
        }
        
        # Store refresh token info for validation
        self.active_refresh_tokens[jti] = {
            "username": user_data.get("sub"),
            "created_at": datetime.utcnow(),
            "expires_at": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            
            # Check if token is blacklisted
            if jti in self.blacklisted_tokens:
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token from refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[ALGORITHM])
            
            if payload.get("type") != "refresh":
                return None
            
            jti = payload.get("jti")
            if jti not in self.active_refresh_tokens:
                return None
            
            username = payload.get("sub")
            if not username:
                return None
            
            # Create new access token
            new_token_data = {"sub": username}
            return self.create_access_token(new_token_data)
            
        except jwt.JWTError:
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Add token to blacklist"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            if jti:
                self.blacklisted_tokens.add(jti)
                return True
        except jwt.JWTError:
            pass
        return False
    
    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            if jti in self.active_refresh_tokens:
                del self.active_refresh_tokens[jti]
                self.blacklisted_tokens.add(jti)
                return True
        except jwt.JWTError:
            pass
        return False
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens from active lists"""
        now = datetime.utcnow()
        expired_jtis = [
            jti for jti, info in self.active_refresh_tokens.items()
            if info["expires_at"] < now
        ]
        
        for jti in expired_jtis:
            del self.active_refresh_tokens[jti]


# Enhanced API Key Management with Rotation
class APIKeyManager:
    """Comprehensive API key management with automatic rotation"""
    
    def __init__(self):
        self.api_keys: Dict[str, APIKeyInfo] = {}
        self.key_usage_stats: Dict[str, Dict] = {}
        
    def generate_api_key(self, user_id: str, name: str, permissions: List[Permission], 
                        expires_in_days: int = 90, auto_rotate_days: Optional[int] = None) -> tuple[str, APIKeyInfo]:
        """Generate new API key with enhanced features"""
        
        # Generate secure key
        raw_key = f"ak_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        key_id = f"key_{secrets.token_urlsafe(16)}"
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=expires_in_days)
        
        api_key_info = APIKeyInfo(
            key_id=key_id,
            name=name,
            key_hash=key_hash,
            user_id=user_id,
            permissions=permissions,
            created_at=created_at,
            expires_at=expires_at,
            auto_rotate_days=auto_rotate_days,
            is_active=True
        )
        
        self.api_keys[key_id] = api_key_info
        self.key_usage_stats[key_id] = {
            "total_requests": 0,
            "last_used": None,
            "daily_usage": {},
            "error_count": 0
        }
        
        logger.info(f"Generated API key: {key_id} for user: {user_id}")
        return raw_key, api_key_info
    
    def rotate_api_key(self, key_id: str, user_id: str) -> Optional[tuple[str, APIKeyInfo]]:
        """Rotate an existing API key"""
        if key_id not in self.api_keys:
            return None
        
        old_key = self.api_keys[key_id]
        if old_key.user_id != user_id:
            return None
        
        # Generate new key while preserving metadata
        raw_key = f"ak_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Update the existing key info
        old_key.key_hash = key_hash
        old_key.created_at = datetime.utcnow()
        old_key.last_rotated = datetime.utcnow()
        old_key.rotation_count += 1
        
        # Reset usage stats but preserve history
        if key_id in self.key_usage_stats:
            stats = self.key_usage_stats[key_id]
            stats["rotation_history"] = stats.get("rotation_history", [])
            stats["rotation_history"].append({
                "rotated_at": datetime.utcnow(),
                "total_requests_before_rotation": stats["total_requests"]
            })
            stats["total_requests"] = 0
            stats["last_used"] = None
            stats["error_count"] = 0
        
        logger.info(f"Rotated API key: {key_id} for user: {user_id}")
        return raw_key, old_key
    
    def verify_api_key(self, raw_key: str) -> Optional[APIKeyInfo]:
        """Verify API key and update usage statistics"""
        if not raw_key.startswith("ak_"):
            return None
        
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        for key_id, key_info in self.api_keys.items():
            if key_info.key_hash == key_hash and key_info.is_active:
                # Check expiration
                if key_info.expires_at < datetime.utcnow():
                    key_info.is_active = False
                    logger.warning(f"API key {key_id} has expired")
                    return None
                
                # Update usage statistics
                self._update_key_usage(key_id)
                
                # Check if auto-rotation is needed
                if self._should_auto_rotate(key_info):
                    logger.info(f"API key {key_id} is due for auto-rotation")
                    # Note: Auto-rotation would be handled by a background task
                
                return key_info
        
        return None
    
    def _update_key_usage(self, key_id: str):
        """Update API key usage statistics"""
        if key_id not in self.key_usage_stats:
            return
        
        stats = self.key_usage_stats[key_id]
        stats["total_requests"] += 1
        stats["last_used"] = datetime.utcnow()
        
        # Track daily usage
        today = datetime.utcnow().date().isoformat()
        if "daily_usage" not in stats:
            stats["daily_usage"] = {}
        stats["daily_usage"][today] = stats["daily_usage"].get(today, 0) + 1
    
    def _should_auto_rotate(self, key_info: APIKeyInfo) -> bool:
        """Check if API key should be auto-rotated"""
        if not key_info.auto_rotate_days:
            return False
        
        days_since_creation = (datetime.utcnow() - key_info.created_at).days
        days_since_rotation = 0
        
        if key_info.last_rotated:
            days_since_rotation = (datetime.utcnow() - key_info.last_rotated).days
        
        return (days_since_rotation >= key_info.auto_rotate_days or 
                days_since_creation >= key_info.auto_rotate_days)
    
    def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """Revoke an API key"""
        if key_id not in self.api_keys:
            return False
        
        key_info = self.api_keys[key_id]
        if key_info.user_id != user_id:
            return False
        
        key_info.is_active = False
        key_info.revoked_at = datetime.utcnow()
        
        logger.info(f"Revoked API key: {key_id} for user: {user_id}")
        return True
    
    def get_user_api_keys(self, user_id: str) -> List[APIKeyInfo]:
        """Get all API keys for a user"""
        return [key for key in self.api_keys.values() if key.user_id == user_id]
    
    def get_key_usage_stats(self, key_id: str, user_id: str) -> Optional[Dict]:
        """Get usage statistics for an API key"""
        if key_id not in self.api_keys or key_id not in self.key_usage_stats:
            return None
        
        key_info = self.api_keys[key_id]
        if key_info.user_id != user_id:
            return None
        
        return self.key_usage_stats[key_id]


# Enhanced Security Middleware
class SecurityMiddleware:
    """Comprehensive security middleware for request processing"""
    
    def __init__(self, token_manager: TokenManager, api_key_manager: APIKeyManager):
        self.token_manager = token_manager
        self.api_key_manager = api_key_manager
        self.rate_limiters: Dict[str, Dict] = {}
        
    async def authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Authenticate request using JWT token or API key"""
        
        # Try JWT token first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            # Check if it's an API key (starts with ak_)
            if token.startswith("ak_"):
                api_key_info = self.api_key_manager.verify_api_key(token)
                if api_key_info:
                    return {
                        "type": "api_key",
                        "user_id": api_key_info.user_id,
                        "key_id": api_key_info.key_id,
                        "permissions": api_key_info.permissions,
                        "rate_limit": api_key_info.rate_limit_per_hour
                    }
            else:
                # Try JWT token
                payload = self.token_manager.verify_token(token)
                if payload:
                    return {
                        "type": "jwt",
                        "user_id": payload.get("sub"),
                        "permissions": payload.get("permissions", []),
                        "roles": payload.get("roles", []),
                        "jti": payload.get("jti")
                    }
        
        return None
    
    async def check_rate_limit(self, identifier: str, max_requests: int = 100, 
                              window_minutes: int = 60) -> bool:
        """Enhanced rate limiting with sliding window"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        if identifier not in self.rate_limiters:
            self.rate_limiters[identifier] = {"requests": [], "blocked_until": None}
        
        limiter = self.rate_limiters[identifier]
        
        # Check if currently blocked
        if limiter["blocked_until"] and limiter["blocked_until"] > now:
            return False
        
        # Clean old requests
        limiter["requests"] = [req_time for req_time in limiter["requests"] 
                              if req_time > window_start]
        
        # Check limit
        if len(limiter["requests"]) >= max_requests:
            # Block for the window duration
            limiter["blocked_until"] = now + timedelta(minutes=window_minutes)
            return False
        
        # Add current request
        limiter["requests"].append(now)
        return True
    
    def detect_suspicious_patterns(self, user_id: str, request: Request) -> List[str]:
        """Detect suspicious activity patterns"""
        patterns = []
        
        # Check for unusual geographic location
        # (This would require GeoIP database in production)
        
        # Check for unusual user agent
        user_agent = request.headers.get("user-agent", "")
        if not user_agent or len(user_agent) < 10:
            patterns.append("suspicious_user_agent")
        
        # Check for rapid successive requests
        # (This would be implemented with Redis in production)
        
        # Check for unusual access patterns
        # (This would require historical data analysis)
        
        return patterns


# Global instances
config = Config()  # Assuming config is available
token_manager = TokenManager(config.secret_key)
api_key_manager = APIKeyManager()
security_middleware = SecurityMiddleware(token_manager, api_key_manager)

# Enhanced Security Dependencies
async def get_current_user_enhanced(request: Request, 
                                   credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Dict[str, Any]:
    """Enhanced user authentication with comprehensive security"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Authenticate using enhanced middleware
    auth_result = await security_middleware.authenticate_request(request)    
    if not auth_result:
        await get_audit_logger().log_security_event(
            event_type=SecurityEvent.UNAUTHORIZED_ACCESS,
            user_id=None,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
            details={"reason": "invalid_credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )    
    # Check rate limiting
    identifier = f"{auth_result['user_id']}:{request.client.host if request.client else 'unknown'}"
    rate_limit = auth_result.get("rate_limit", 1000)  # Default rate limit
    if not await security_middleware.check_rate_limit(identifier, rate_limit, 60):
        await get_audit_logger().log_security_event(
            event_type=SecurityEvent.RATE_LIMIT_EXCEEDED,
            user_id=auth_result['user_id'],
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
            details={"rate_limit": rate_limit}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"        )
    
    # Detect suspicious patterns
    suspicious_patterns = security_middleware.detect_suspicious_patterns(auth_result['user_id'], request)
    if suspicious_patterns:
        await get_audit_logger().log_security_event(
            event_type=SecurityEvent.SUSPICIOUS_ACTIVITY,
            user_id=auth_result['user_id'],
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
            details={"patterns": suspicious_patterns},
            risk_score=85
        )
    
    return auth_result

def require_permission_enhanced(permission: Permission):
    """Enhanced permission checking with comprehensive audit logging"""
    async def permission_dependency(request: Request, 
                                   user_auth: Dict[str, Any] = Depends(get_current_user_enhanced)) -> Dict[str, Any]:
        user_permissions = user_auth.get("permissions", [])
        
        # Check if user has the required permission
        if permission.value not in [p.value if hasattr(p, 'value') else p for p in user_permissions]:
            await get_audit_logger().log_security_event(
                event_type=SecurityEvent.PERMISSION_DENIED,
                user_id=user_auth['user_id'],
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
                details={
                    "required_permission": permission.value,
                    "user_permissions": [p.value if hasattr(p, 'value') else p for p in user_permissions],
                    "endpoint": str(request.url)
                },
                risk_score=60
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission.value}"
            )
        
        return user_auth
    
    return permission_dependency

def require_role_enhanced(role: UserRole):
    """Enhanced role checking with comprehensive audit logging"""
    async def role_dependency(request: Request,
                             user_auth: Dict[str, Any] = Depends(get_current_user_enhanced)) -> Dict[str, Any]:
        
        user_roles = user_auth.get("roles", [])
        
        # Check if user has the required role
        if role.value not in [r.value if hasattr(r, 'value') else r for r in user_roles]:
            await get_audit_logger().log_security_event(
                event_type=SecurityEvent.PERMISSION_DENIED,
                user_id=user_auth['user_id'],
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
                details={
                    "required_role": role.value,
                    "user_roles": [r.value if hasattr(r, 'value') else r for r in user_roles],
                    "endpoint": str(request.url)
                },
                risk_score=65
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role.value}"
            )
        
        return user_auth
    
    return role_dependency
