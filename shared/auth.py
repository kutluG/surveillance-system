"""
JWT and API-key authentication utilities for FastAPI services.
"""
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from pydantic import BaseModel

# Configuration from environment
SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me")
ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
_API_KEYS: List[str] = os.getenv("API_KEYS", "").split(",")  # Comma-separated list


oauth2_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenData(BaseModel):
    """
    Data stored in JWT payload after validation.
    """
    sub: str
    scopes: List[str] = []


def create_access_token(
    subject: str,
    scopes: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT access token.
    :param subject: Identifier for the token (e.g. service or user ID).
    :param scopes: List of scope strings to embed.
    :param expires_delta: Token lifetime; defaults to ACCESS_TOKEN_EXPIRE_MINUTES.
    :return: Encoded JWT.
    """
    to_encode: Dict[str, any] = {"sub": subject, "scopes": scopes or []}
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_jwt_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.
    :param token: Encoded JWT string.
    :raises HTTPException: If token is invalid or expired.
    :return: TokenData object with claims.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
            )
        scopes = payload.get("scopes", [])
        return TokenData(sub=subject, scopes=scopes)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
) -> TokenData:
    """
    FastAPI dependency to retrieve and validate JWT bearer token.
    Raises 401 if missing or invalid.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_jwt_token(credentials.credentials)


async def get_api_key(
    api_key: str = Security(api_key_scheme)
) -> str:
    """
    FastAPI dependency to validate an API key header.
    Raises 403 if missing or not recognized.
    """
    if not api_key or api_key not in _API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key",
        )
    return api_key