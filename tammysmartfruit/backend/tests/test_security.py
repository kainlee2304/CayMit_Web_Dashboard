"""
Security & Cryptography Test Suite
Tests Argon2id, PBKDF2 Legacy Rehash, RS256 JWT, and CSPRNG Refresh Tokens.
"""

import pytest
from app.core.security import (
    hash_password_argon2,
    verify_and_check_rehash,
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_token_sha256
)
from app.core.errors import UnauthorizedException
from passlib.hash import pbkdf2_sha256

def test_argon2id_hashing_and_verification():
    password = "SecurePassword@2026"
    pwd_hash = hash_password_argon2(password)
    
    assert pwd_hash.startswith("$argon2id$")
    
    is_valid, needs_rehash = verify_and_check_rehash(password, pwd_hash, algo="ARGON2ID")
    assert is_valid is True
    assert needs_rehash is False
    
    is_wrong, _ = verify_and_check_rehash("WrongPassword@123", pwd_hash, algo="ARGON2ID")
    assert is_wrong is False

def test_pbkdf2_legacy_verification_and_rehash_flag():
    password = "LegacyOldPassword@123"
    legacy_hash = pbkdf2_sha256.hash(password)
    
    # Must succeed and indicate that rehash is required
    is_valid, needs_rehash = verify_and_check_rehash(password, legacy_hash, algo="PBKDF2_LEGACY")
    assert is_valid is True
    assert needs_rehash is True
    
    is_wrong, _ = verify_and_check_rehash("WrongLegacyPassword", legacy_hash, algo="PBKDF2_LEGACY")
    assert is_wrong is False

def test_jwt_rs256_signing_and_decoding():
    token = create_access_token(
        subject="01916322-1111-7000-8111-222233334444",
        organization_id="01916320-0000-7000-8000-000000000001",
        roles=["admin_hq", "technician"],
        permissions=["plot:read", "harvest:create"],
        data_scope="ALL"
    )
    
    assert isinstance(token, str)
    assert len(token) > 100
    
    payload = decode_access_token(token)
    assert payload["sub"] == "01916322-1111-7000-8111-222233334444"
    assert payload["org_id"] == "01916320-0000-7000-8000-000000000001"
    assert "admin_hq" in payload["roles"]
    assert "harvest:create" in payload["permissions"]
    assert payload["scope"] == "ALL"

def test_jwt_rs256_tampering_rejection():
    token = create_access_token(subject="user-123")
    
    # Tamper token signature
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1] + ".tampered_signature_xyz"
    
    with pytest.raises(UnauthorizedException):
        decode_access_token(tampered)

def test_opaque_refresh_token_and_sha256():
    raw_token = generate_opaque_token(32)
    assert len(raw_token) >= 32
    
    token_hash1 = hash_token_sha256(raw_token)
    token_hash2 = hash_token_sha256(raw_token)
    
    assert token_hash1 == token_hash2
    assert len(token_hash1) == 64  # Hex SHA-256 length
