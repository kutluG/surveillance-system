"""
Test JWT Authentication for Annotation Frontend Service.
"""
import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from calendar import timegm

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import create_test_token, verify_jwt_token, TokenData
from config import settings


@pytest.fixture
def valid_token():
    """Create a valid JWT token for testing."""
    return create_test_token(
        subject="test-user-123",
        scopes=["annotation:read", "annotation:write"],
        roles=["annotator"],
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def expired_token():
    """Create an expired JWT token for testing."""
    return create_test_token(
        subject="test-user-123",
        scopes=["annotation:read", "annotation:write"],
        roles=["annotator"],
        expires_delta=timedelta(seconds=-1)  # Already expired
    )


@pytest.fixture
def limited_scope_token():
    """Create a token with limited scopes (read only)."""
    return create_test_token(
        subject="read-only-user",
        scopes=["annotation:read"],  # Missing annotation:write
        roles=["viewer"],
        expires_delta=timedelta(hours=1)
    )


class TestTokenVerification:
    """Test JWT token verification functionality."""
    
    def test_verify_valid_token(self, valid_token):
        """Test that a valid token is properly decoded."""
        token_data = verify_jwt_token(valid_token)
        
        assert isinstance(token_data, TokenData)
        assert token_data.sub == "test-user-123"
        assert "annotation:read" in token_data.scopes
        assert "annotation:write" in token_data.scopes
        assert "annotator" in token_data.roles
        # Token should not be expired
        assert token_data.exp > timegm(datetime.utcnow().utctimetuple())
    
    def test_verify_expired_token(self, expired_token):
        """Test that an expired token raises HTTPException."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(expired_token)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_invalid_token(self):
        """Test that an invalid token raises HTTPException."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()
    
    def test_verify_malformed_token(self):
        """Test that a malformed token raises HTTPException."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token("not-a-jwt-at-all")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_token_missing_subject(self):
        """Test token without subject claim."""
        from jose import jwt
        from fastapi import HTTPException
        
        payload = {
            "exp": timegm((datetime.utcnow() + timedelta(hours=1)).utctimetuple()),
            "scopes": ["annotation:read"]
            # Missing "sub" claim
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(token)
        
        assert exc_info.value.status_code == 401
        assert "subject" in exc_info.value.detail.lower()


class TestTokenCreation:
    """Test token creation helper functions."""
    
    def test_create_test_token_basic(self):
        """Test basic token creation."""
        token = create_test_token("test-user")
        token_data = verify_jwt_token(token)
        
        assert token_data.sub == "test-user"
        assert token_data.scopes == []
        assert token_data.roles == []
    
    def test_create_test_token_with_scopes_and_roles(self):
        """Test token creation with scopes and roles."""
        token = create_test_token(
            "test-user",
            scopes=["read", "write"],
            roles=["admin", "user"]
        )
        token_data = verify_jwt_token(token)
        
        assert token_data.sub == "test-user"
        assert token_data.scopes == ["read", "write"]
        assert token_data.roles == ["admin", "user"]
    
    def test_create_test_token_custom_expiration(self):
        """Test token creation with custom expiration."""
        short_expiry = timedelta(minutes=5)
        token = create_test_token("test-user", expires_delta=short_expiry)
        token_data = verify_jwt_token(token)
        
        # Should expire within the next 5 minutes
        expected_exp = timegm((datetime.utcnow() + short_expiry).utctimetuple())
        actual_exp = token_data.exp
        
        # Allow some tolerance for processing time
        assert abs(actual_exp - expected_exp) < 5


if __name__ == "__main__":
    pytest.main([__file__])
