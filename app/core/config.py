from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os

def load_deploy_config() -> dict:
    """Charge la configuration de déploiement depuis config/deployment.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "deployment.yaml")
    config_path = os.path.abspath(config_path)
    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("deploy", {}) if data else {}
        except ImportError:
            # PyYAML non installé, on ignore silencieusement
            return {}
    return {}

# Charger la config de déploiement pour extraire les valeurs par défaut
_deploy_config = load_deploy_config()

class Settings(BaseSettings):
    PROJECT_NAME: str = "RPGPDF2Text API"
    API_V1_STR: str = "/api/v1"
    BASE_URL: str = Field(default="http://localhost:8000")
    
    # Préfixe de l'application (ex: "/rpgpdf2txt") pour déploiement derrière un reverse proxy
    APP_PREFIX: str = Field(default=_deploy_config.get("app_prefix", ""))
    
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

# Normaliser le préfixe : supprimer le slash final s'il y en a un
if settings.APP_PREFIX.endswith("/"):
    settings.APP_PREFIX = settings.APP_PREFIX.rstrip("/")
