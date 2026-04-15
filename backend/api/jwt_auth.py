"""
JWT authentication utilities for Django
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
import bcrypt
from django.conf import settings
import os

# Using bcrypt directly for password hashing

# JWT Configuration - get from settings or environment
JWT_SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production'))
JWT_ALGORITHM = getattr(settings, 'JWT_ALGORITHM', os.getenv('JWT_ALGORITHM', 'HS256'))
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(getattr(settings, 'JWT_ACCESS_TOKEN_EXPIRE_MINUTES', os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30')))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(getattr(settings, 'JWT_REFRESH_TOKEN_EXPIRE_DAYS', os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7')))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    try:
        # Convert password to bytes
        password_bytes = plain_password.encode('utf-8')
        # Truncate to 72 bytes if necessary (bcrypt limit)
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Verify using bcrypt
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a plain password using bcrypt"""
    # Bcrypt has a 72 byte limit - truncate if necessary
    # Convert to bytes to check length properly
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate to 72 bytes (not characters, to handle multi-byte characters correctly)
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash using bcrypt directly
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token (longer expiration)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_2fa_pending_token(data: dict) -> str:
    """
    Short-lived (5 min) token issued after successful password verification
    when the user has 2FA enabled.  Carries type='2fa_pending' so it cannot
    be used as a normal access token.  The frontend must POST it to
    /2fa/login-verify together with the OTP to receive real access tokens.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode.update({"exp": expire, "type": "2fa_pending"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

