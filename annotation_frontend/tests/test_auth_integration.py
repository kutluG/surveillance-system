"""
Integration test for JWT authentication with FastAPI endpoints.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import create_test_token, get_current_user, require_scopes
from config import settings


class TestAuthDependencies:
    """Test FastAPI authentication dependencies."""
    
    def test_get_current_user_with_valid_token(self):
        """Test that get_current_user works with valid credentials."""
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create valid token
        token = create_test_token("test-user", scopes=["annotation:read"])
        
        # Mock credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        # Test the dependency function
        import asyncio
        async def run_test():
            user_data = await get_current_user(credentials)
            assert user_data.sub == "test-user"
            assert "annotation:read" in user_data.scopes
            return user_data
        
        user_data = asyncio.run(run_test())
        assert user_data is not None
    
    def test_get_current_user_with_invalid_credentials(self):
        """Test that get_current_user rejects invalid credentials."""
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        
        # Mock invalid credentials
        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="invalid")
        
        import asyncio
        async def run_test():
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)
            assert exc_info.value.status_code == 401
        
        asyncio.run(run_test())
    
    def test_require_scopes_with_sufficient_permissions(self):
        """Test that require_scopes allows access with sufficient permissions."""
        from auth import TokenData
        
        # Create user with required scope
        user_data = TokenData(
            sub="test-user",
            exp=1234567890,
            scopes=["annotation:read", "annotation:write"],
            roles=["annotator"]
        )
        
        # Test scope requirement
        scope_checker = require_scopes("annotation:read")
        
        import asyncio
        async def run_test():
            result = await scope_checker(user_data)
            assert result.sub == "test-user"
            return result
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_require_scopes_with_insufficient_permissions(self):
        """Test that require_scopes denies access with insufficient permissions."""
        from auth import TokenData
        from fastapi import HTTPException
        
        # Create user without required scope
        user_data = TokenData(
            sub="test-user",
            exp=1234567890,
            scopes=["annotation:read"],  # Missing annotation:write
            roles=["viewer"]
        )
        
        # Test scope requirement
        scope_checker = require_scopes("annotation:write")
        
        import asyncio
        async def run_test():
            with pytest.raises(HTTPException) as exc_info:
                await scope_checker(user_data)
            assert exc_info.value.status_code == 403
            assert "insufficient privileges" in exc_info.value.detail.lower()
        
        asyncio.run(run_test())


class TestSecurityConfiguration:
    """Test security configuration and settings."""
    
    def test_jwt_secret_key_loaded(self):
        """Test that JWT secret key is properly loaded."""
        assert settings.JWT_SECRET_KEY is not None
        assert len(settings.JWT_SECRET_KEY) > 0
        assert settings.JWT_SECRET_KEY != ""
    
    def test_token_with_different_secret_fails(self):
        """Test that tokens signed with different secrets fail validation."""
        from jose import jwt
        from fastapi import HTTPException
        from auth import verify_jwt_token
        from calendar import timegm
        from datetime import datetime, timedelta
        
        # Create token with different secret
        payload = {
            "sub": "test-user",
            "exp": timegm((datetime.utcnow() + timedelta(hours=1)).utctimetuple()),
            "scopes": ["annotation:read"]
        }
        wrong_secret_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        # Should fail verification
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(wrong_secret_token)
        
        assert exc_info.value.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__])
