import argparse
import sys
import os
from loguru import logger

def load_deploy_config() -> dict:
    """Charge la configuration de déploiement depuis config/deployment.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "config", "deployment.yaml")
    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("deploy", {}) if data else {}
        except ImportError:
            logger.warning("PyYAML non installé, impossible de lire deployment.yaml")
            return {}
    return {}

def deploy(dev_mode: bool):
    """
    Script de déploiement selon les règles du projet.
    En mode production, injecte APP_PREFIX dans le .env.
    """
    env = "Développement" if dev_mode else "Production"
    logger.info(f"Démarrage du processus de déploiement pour l'environnement: {env}")
    
    deploy_config = load_deploy_config()
    app_prefix = deploy_config.get("app_prefix", "")
    
    if not dev_mode and app_prefix:
        # En production, s'assurer que APP_PREFIX est dans le .env
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        env_content = ""
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_content = f.read()
        
        # Mettre à jour ou ajouter APP_PREFIX
        if "APP_PREFIX=" in env_content:
            lines = env_content.split("\n")
            lines = [f"APP_PREFIX={app_prefix}" if l.startswith("APP_PREFIX=") else l for l in lines]
            env_content = "\n".join(lines)
        else:
            env_content += f"\nAPP_PREFIX={app_prefix}\n"
        
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)
        
        logger.info(f"APP_PREFIX configuré dans .env : {app_prefix}")
    
    logger.info("Mise à jour des dépendances avec uv...")
    # os.system("uv pip install -r requirements.txt")
    
    logger.info(f"Déploiement en {env} terminé avec succès.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de déploiement de RPGPDF2Text")
    parser.add_argument("--dev", action="store_true", help="Déployer en environnement de développement")
    parser.add_argument("--prod", action="store_true", help="Déployer en environnement de production")
    args = parser.parse_args()
    
    if args.prod:
        deploy(dev_mode=False)
    elif args.dev:
        deploy(dev_mode=True)
    else:
        logger.error("Veuillez spécifier --dev ou --prod")
        sys.exit(1)

