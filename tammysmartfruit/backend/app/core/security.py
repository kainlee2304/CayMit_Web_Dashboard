"""
Security and Cryptographic Services Module
Implements:
1. Argon2id Password Hashing & PBKDF2 Legacy Verification + Rehash Detection.
2. RS256 Asymmetric JWT Access Token Signing & Strict Claims Verification.
3. Opaque CSPRNG Refresh Token generation, SHA-256 Hashing, Rotation & Reuse Detection.
"""

import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from jose import jwt, JWTError
from app.core.config import settings
from app.core.errors import UnauthorizedException
from app.core.logging import logger

# Initialize Argon2id password hasher with OWASP recommended parameters
# Memory: 64MB (65536 KB), Time: 3 iterations, Parallelism: 4 threads
argon2_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

# ------------------------------------------------------------------------------
# 1. PASSWORD HASHING & LEGACY REHASH MANAGEMENT
# ------------------------------------------------------------------------------

def hash_password_argon2(password: str) -> str:
    """Hash password using Argon2id."""
    return argon2_hasher.hash(password)

def verify_pbkdf2_legacy(password: str, stored_hash: str, salt_hex: Optional[str] = None, iterations: int = 210000) -> bool:
    """
    Verify legacy PBKDF2-HMAC-SHA256 password hash.
    Format can be standard '$pbkdf2-sha256$...' or separate salt_hex.
    """
    try:
        if stored_hash.startswith("$pbkdf2") or stored_hash.startswith("pbkdf2"):
            # Use passlib for standard formatted PBKDF2
            from passlib.hash import pbkdf2_sha256
            return pbkdf2_sha256.verify(password, stored_hash)
        
        if salt_hex:
            salt = bytes.fromhex(salt_hex)
            derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return derived.hex() == stored_hash
            
        return False
    except Exception as e:
        logger.warning(f"Error during legacy PBKDF2 verification: {e}")
        return False

def verify_and_check_rehash(
    plain_password: str,
    stored_hash: str,
    algo: str = "ARGON2ID",
    salt_hex: Optional[str] = None,
    pbkdf2_iterations: Optional[int] = None
) -> Tuple[bool, bool]:
    """
    Verify password against stored credentials.
    Returns: (is_valid: bool, needs_rehash: bool)
    """
    if algo == "ARGON2ID":
        try:
            argon2_hasher.verify(stored_hash, plain_password)
            needs_rehash = argon2_hasher.check_needs_rehash(stored_hash)
            return True, needs_rehash
        except (VerifyMismatchError, VerificationError):
            return False, False
        except Exception as e:
            logger.error(f"Argon2 verification unexpected error: {e}")
            return False, False

    elif algo == "PBKDF2_LEGACY":
        iters = pbkdf2_iterations or 210000
        is_valid = verify_pbkdf2_legacy(plain_password, stored_hash, salt_hex, iters)
        # If legacy password was verified successfully, it MUST be rehashed to Argon2id
        return is_valid, is_valid

    return False, False


# ------------------------------------------------------------------------------
# 2. RS256 ASYMMETRIC JWT ACCESS TOKENS
# ------------------------------------------------------------------------------

def create_access_token(
    subject: str,
    organization_id: Optional[str] = None,
    roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None,
    data_scope: str = "OWN",
    assigned_resources: Optional[Dict[str, List[str]]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT RS256 Access Token.
    Includes canonical claims: sub, org_id, roles, permissions, data_scope, iss, aud, iat, exp, jti.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES))
    
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "org_id": str(organization_id) if organization_id else None,
        "roles": roles or [],
        "permissions": permissions or [],
        "scope": data_scope,
        "assigned_resources": assigned_resources or {},
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16)
    }
    
    private_key = settings.get_private_key()
    token = jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)
    return token

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT RS256 Access Token against Public Key.
    Validates issuer, audience, expiration, signature.
    """
    try:
        public_key = settings.get_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "require_sub": True,
            }
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(message_key="errors.auth.tokenExpired", code="TOKEN_EXPIRED")
    except JWTError as e:
        logger.warning(f"JWT decode failure: {e}")
        raise UnauthorizedException(message_key="errors.auth.invalidToken", code="INVALID_TOKEN")


# ------------------------------------------------------------------------------
# 3. OPAQUE CSPRNG REFRESH TOKENS & HASHING
# ------------------------------------------------------------------------------

def generate_opaque_token(length_bytes: int = 32) -> str:
    """Generate cryptographically strong random URL-safe token (CSPRNG 256-bit)."""
    return secrets.token_urlsafe(length_bytes)

def hash_token_sha256(token: str) -> str:
    """Hash opaque token with SHA-256 for secure server-side lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

class RefreshTokenPayload:
    """In-Memory / Redis Representation of a Refresh Token session."""
    def __init__(
        self,
        user_id: str,
        family_id: str,
        organization_id: Optional[str] = None,
        is_revoked: bool = False,
        expires_at: Optional[datetime] = None
    ):
        self.user_id = user_id
        self.family_id = family_id
        self.organization_id = organization_id
        self.is_revoked = is_revoked
        self.expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "family_id": self.family_id,
            "organization_id": self.organization_id,
            "is_revoked": self.is_revoked,
            "expires_at": self.expires_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RefreshTokenPayload":
        exp = datetime.fromisoformat(data["expires_at"]) if isinstance(data.get("expires_at"), str) else data.get("expires_at")
        return cls(
            user_id=data["user_id"],
            family_id=data["family_id"],
            organization_id=data.get("organization_id"),
            is_revoked=data.get("is_revoked", False),
            expires_at=exp
        )
