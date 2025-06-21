"""
JWT Authentication for Annotation Frontend Service.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from calendar import timegm

from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from config import settings

# Security scheme for JWT Bearer token
oauth2_scheme = HTTPBearer()
oauth2_password_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


class TokenData(BaseModel):
    """Token data extracted from JWT."""
    sub: str
    exp: int
    roles: List[str] = []
    scopes: List[str] = []


class LoginCredentials(BaseModel):
    """Login credentials for authentication."""
    username: str
    password: str


def verify_jwt_token(token: str) -> TokenData:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData: Decoded token data
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=["HS256"]
        )
        
        # Extract required claims
        subject = payload.get("sub")
        expiration = payload.get("exp")
        
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if expiration is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing expiration claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            sub=subject,
            exp=expiration,
            roles=payload.get("roles", []),
            scopes=payload.get("scopes", [])
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
) -> TokenData:
    """
    FastAPI dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials from request header
        
    Returns:
        TokenData: Current user token data
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return verify_jwt_token(credentials.credentials)


def require_scopes(*required_scopes: str):
    """
    Create a dependency that requires specific scopes.
    
    Args:
        *required_scopes: Required scopes for the endpoint
        
    Returns:
        Dependency function that checks user scopes
    """
    async def check_scopes(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        user_scopes = set(current_user.scopes)
        required_scopes_set = set(required_scopes)
        
        if not required_scopes_set.issubset(user_scopes):
            missing_scopes = required_scopes_set - user_scopes
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Missing scopes: {', '.join(missing_scopes)}",
            )
        
        return current_user
    
    return check_scopes


def require_roles(*required_roles: str):
    """
    Create a dependency that requires specific roles.
    
    Args:
        *required_roles: Required roles for the endpoint
        
    Returns:
        Dependency function that checks user roles
    """
    async def check_roles(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        user_roles = set(current_user.roles)
        required_roles_set = set(required_roles)
        
        if not required_roles_set.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required roles: {', '.join(required_roles)}",
            )
        
        return current_user
    
    return check_roles


def require_role(required_role: str):
    """
    Create a dependency that requires a specific role.
    
    Args:
        required_role: Required role for the endpoint
        
    Returns:
        Dependency function that checks user role
    """
    async def check_role(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required role: {required_role}",
            )
        
        return current_user
    
    return check_role


def create_test_token(
    subject: str,
    scopes: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a test JWT token for testing purposes.
    
    Args:
        subject: Token subject (user ID)
        scopes: List of scopes to include
        roles: List of roles to include
        expires_delta: Token expiration delta
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=1)
    
    now = datetime.utcnow()
    expire = now + expires_delta
    
    # Use the same time calculation method as jose library
    now_timestamp = timegm(now.utctimetuple())
    exp_timestamp = timegm(expire.utctimetuple())
    
    payload = {
        "sub": subject,
        "exp": exp_timestamp,
        "scopes": scopes or [],
        "roles": roles or [],
        "iat": now_timestamp
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def authenticate_user(username: str, password: str) -> Optional[TokenData]:
    """
    Authenticate user with username and password.
    In production, this would check against a proper user database.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        TokenData if authentication successful, None otherwise
    """
    # Demo users - in production, check against database with hashed passwords
    demo_users = {
        "annotator": {
            "password": "annotator_pass",
            "roles": ["annotator"],
            "scopes": ["annotation:read", "annotation:write"]
        },
        "compliance_officer": {
            "password": "compliance_pass", 
            "roles": ["compliance_officer"],
            "scopes": ["data:read", "data:delete", "annotation:read"]
        },
        "admin": {
            "password": "admin_pass",
            "roles": ["admin", "annotator", "compliance_officer"],
            "scopes": ["annotation:read", "annotation:write", "data:read", "data:delete", "admin:all"]
        }
    }
    
    user = demo_users.get(username)
    if not user or user["password"] != password:
        return None
    
    return TokenData(
        sub=username,
        exp=int((datetime.utcnow() + timedelta(hours=8)).timestamp()),
        roles=user["roles"],
        scopes=user["scopes"]
    )


def create_access_token(user_data: TokenData, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token for authenticated user.
    
    Args:
        user_data: User token data
        expires_delta: Token expiration delta
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=8)
    
    now = datetime.utcnow()
    expire = now + expires_delta
    
    # Use the same time calculation method as jose library
    now_timestamp = timegm(now.utctimetuple())
    exp_timestamp = timegm(expire.utctimetuple())
    
    payload = {
        "sub": user_data.sub,
        "exp": exp_timestamp,
        "scopes": user_data.scopes,
        "roles": user_data.roles,
        "iat": now_timestamp
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
