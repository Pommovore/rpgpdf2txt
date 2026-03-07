from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os
import subprocess

def load_deploy_config() -> dict:
    """Charge la configuration de déploiement depuis config/deployment.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "deploy.yaml")
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
    
    @property
    def EXTERNAL_URL(self) -> str:
        machine = _deploy_config.get("machine_name", "localhost")
        prefix = self.APP_PREFIX
        # Si on est sur localhost, on garde probablement le port 8000 pour le dev
        if machine == "localhost":
            return f"http://localhost:8000{prefix}"
        # En production, on suppose HTTPS (via Nginx configuré précédemment)
        return f"https://{machine}{prefix}"
    
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
    DATA_DIR: str = "./data"
    USERS_DIR: str = "./data/users"
    TEMP_DIR: str = "./data/temp"

    # Propriétés dynamiques pour récupérer les informations Git
    @property
    def APP_VERSION(self) -> str:
        """Récupère la version de l'application basée sur la date du dernier commit."""
        try:
            cmd = ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d_%H%M%S"]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, cwd=os.path.dirname(__file__)).strip()
            return f"rpgpf2txt_{out}"
        except Exception:
            return "rpgpf2txt_inconnue"

    @property
    def GITHUB_URL(self) -> str:
        """Récupère l'URL du dépôt GitHub depuis la configuration Git locale."""
        try:
            cmd = ["git", "config", "--get", "remote.origin.url"]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, cwd=os.path.dirname(__file__)).strip()
            # Transformation des URLs SSH en URLs HTTPS
            if out.startswith("git@"):
                out = out.replace(":", "/").replace("git@", "https://")
            if out.endswith(".git"):
                out = out[:-4]
            return out
        except Exception:
            return "#"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

# Normaliser le préfixe : supprimer le slash final s'il y en a un
if settings.APP_PREFIX.endswith("/"):
    settings.APP_PREFIX = settings.APP_PREFIX.rstrip("/")
