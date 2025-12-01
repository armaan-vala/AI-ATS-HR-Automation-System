import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AI-ATS-HR-Automation-System"
    SECRET_KEY: str = "super_secret_key_change_this_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database (Supabase)
    DATABASE_URL: str

    # Redis (Render or Local)
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Keys
    GROQ_API_KEY: str | None = None
    
    # Google Keys (Paths to JSON files)
    GOOGLE_TOKEN_PATH: str = "token.json"
    GOOGLE_CREDENTIALS_PATH: str = "credentials.json"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @validator("DATABASE_URL", pre=True)
    def fix_supabase_url(cls, v):
        """Fixes the URL schema for SQLAlchemy if it starts with postgres://"""
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

settings = Settings()