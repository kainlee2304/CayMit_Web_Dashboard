"""
Configuration Settings Module
Production-grade configuration loaded via environment variables using Pydantic Settings V2.
"""

import os
from typing import List, Optional
from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application Basics
    APP_ENV: str = "development"
    APP_NAME: str = "Tam My Smart Fruit Backend"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server Binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # PostgreSQL 16 Connection (Runtime Non-Superuser Role)
    DATABASE_URL: str = "postgresql+asyncpg://tammy_app_user:app_secure_password_2026@127.0.0.1:5433/tammysmartfruit_clean_test"
    DATABASE_SYNC_URL: str = "postgresql://tammy_app_user:app_secure_password_2026@127.0.0.1:5433/tammysmartfruit_clean_test"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Redis 7 In-Memory Cache & Celery
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # JWT RS256 Asymmetric Settings
    JWT_ALGORITHM: str = "RS256"
    JWT_ISSUER: str = "tammy-smart-fruit-auth"
    JWT_AUDIENCE: str = "tammy-smart-fruit-api"
    ACCESS_TOKEN_TTL_MINUTES: int = 30
    REFRESH_TOKEN_TTL_DAYS: int = 14

    # RSA Keys: Can be specified as paths or direct PEM content
    JWT_PRIVATE_KEY_PATH: Optional[str] = "./jwt_rs256.key"
    JWT_PUBLIC_KEY_PATH: Optional[str] = "./jwt_rs256.key.pub"
    JWT_PRIVATE_KEY: Optional[str] = None
    JWT_PUBLIC_KEY: Optional[str] = None

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    def get_private_key(self) -> str:
        """Resolve RSA private key from environment variable or file."""
        if self.JWT_PRIVATE_KEY:
            return self.JWT_PRIVATE_KEY
        
        candidates = [
            self.JWT_PRIVATE_KEY_PATH,
            os.path.join(os.path.dirname(__file__), "..", "..", "jwt_rs256.key"),
            "jwt_rs256.key"
        ]
        for path in candidates:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
                    
        raise ValueError("RSA Private Key not found! Provide JWT_PRIVATE_KEY or valid JWT_PRIVATE_KEY_PATH.")

    def get_public_key(self) -> str:
        """Resolve RSA public key from environment variable or file."""
        if self.JWT_PUBLIC_KEY:
            return self.JWT_PUBLIC_KEY
            
        candidates = [
            self.JWT_PUBLIC_KEY_PATH,
            os.path.join(os.path.dirname(__file__), "..", "..", "jwt_rs256.key.pub"),
            "jwt_rs256.key.pub"
        ]
        for path in candidates:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
                    
        raise ValueError("RSA Public Key not found! Provide JWT_PUBLIC_KEY or valid JWT_PUBLIC_KEY_PATH.")

settings = Settings()
