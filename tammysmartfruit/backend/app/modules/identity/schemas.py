"""
Identity & Authentication Pydantic V2 Schemas
"""

from datetime import datetime
from typing import List, Optional, Set
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class LoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=3, max_length=120, description="Username or Email address")
    password: str = Field(..., min_length=6, max_length=128, description="User password")

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: str
    username: str
    roles: List[str]
    organization_id: Optional[str] = None
    data_scope: str = "OWN"

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, description="Opaque CSPRNG Refresh Token")

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Optional specific refresh token to revoke")

class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    full_name: str
    is_active: bool
    is_verified: bool
    preferred_locale: str
    roles: List[str]
    permissions: List[str]
    organization_id: Optional[uuid.UUID] = None
    data_scope: str
    created_at: datetime

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=60)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)
    preferred_locale: str = Field("vi", pattern="^(vi|en)$")
    initial_role: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    full_name: str
    is_active: bool
    is_verified: bool
    preferred_locale: str
    created_at: datetime
