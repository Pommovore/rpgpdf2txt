from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "RPGPDF2Text API"
    API_V1_STR: str = "/api/v1"
    BASE_URL: str = Field(default="http://localhost:8000")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./data/db/rpgpdf2text.db")
    
    # Security
    SECRET_KEY: str = Field(default="CHANGE_ME_IN_PRODUCTION_A_VERY_LONG_SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # These will also be stored/overridden in the DB for the "creator" level,
    # but we can have environment fallbacks
    HF_TOKEN: Optional[str] = None
    DISCORD_WEBHOOK_URL: Optional[str] = None
    
    # Storage
    DATA_DIR: str = "./data"
    USERS_DIR: str = "./data/users"
    TEMP_DIR: str = "./data/temp"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
