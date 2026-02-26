import argparse
import sys
from loguru import logger

def deploy(dev_mode: bool):
    """
    Simulation du script de déploiement selon les règles du projet.
    """
    env = "Développement" if dev_mode else "Production"
    logger.info(f"Démarrage du processus de déploiement pour l'environnement: {env}")
    
    # Dans un cas réel, on exécuterait les migrations alembic, la copie des fichiers, etc.
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
