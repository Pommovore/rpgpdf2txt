#!/usr/bin/env python3
"""
Script de déploiement distant pour RPGPDF2Text.
Se connecte en SSH à la machine cible définie dans config/deployment.yaml
et y recopie l'application.

Utilisation :
    python deploiement.py [--dry-run]

Variables d'environnement requises :
    REMOTE_LOGIN  : nom d'utilisateur SSH
    REMOTE_PWD    : mot de passe SSH (ou utiliser une clé SSH)

Dépendances supplémentaires (ne sont PAS dans requirements.txt car ne concernent pas l'app elle-même) :
    uv pip install paramiko
"""

import os
import sys
import argparse
import yaml
from pathlib import Path
from loguru import logger

# ─── Configuration du logging ──────────────────────────────────────────────────
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

# ─── Chemins de base ────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent
CONFIG_PATH = PROJECT_DIR / "config" / "deployment.yaml"

def load_config() -> dict:
    """Charge la configuration de déploiement."""
    if not CONFIG_PATH.exists():
        logger.error(f"Fichier de configuration introuvable : {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    deploy = data.get("deploy", {})
    required_keys = ["machine_name", "port", "target_directory", "app_prefix"]
    for key in required_keys:
        if key not in deploy:
            logger.error(f"Clé manquante dans deployment.yaml : {key}")
            sys.exit(1)

    return deploy


def get_credentials() -> tuple:
    """Récupère les identifiants SSH depuis les variables d'environnement."""
    login = os.environ.get("REMOTE_LOGIN")
    pwd = os.environ.get("REMOTE_PWD")

    if not login:
        logger.error("Variable d'environnement REMOTE_LOGIN non définie.")
        sys.exit(1)

    # Le mot de passe peut être vide si on utilise une clé SSH
    return login, pwd


# Répertoires à ne jamais traverser
EXCLUDE_DIRS = {".venv", ".git", "__pycache__", "data", "tokens", ".github"}

# Fichiers individuels à exclure
EXCLUDE_FILES = {".env", "ci_test.db", "deploiement.py"}

# Extensions à exclure
EXCLUDE_EXTENSIONS = {".pyc"}


def collect_files(base_dir: Path) -> list:
    """Collecte tous les fichiers à transférer (en élagant les répertoires exclus)."""
    files = []
    for dirpath, dirnames, filenames in os.walk(base_dir):
        # Élaguer les répertoires exclus pour ne pas les traverser
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            if filename in EXCLUDE_FILES:
                continue
            if any(filename.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                continue
            files.append(Path(dirpath) / filename)

    return files


def generate_env_file(config: dict) -> str:
    """Génère le contenu du fichier .env pour la production."""
    prefix = config.get("app_prefix", "")
    lines = [
        "# Fichier .env généré automatiquement par deploiement.py",
        "# Modifiez les valeurs ci-dessous selon votre environnement de production",
        "",
        "SECRET_KEY=CHANGEZ_MOI_CLE_TRES_LONGUE_ET_SECRETE",
        f"DATABASE_URL=sqlite:///./data/db/rpgpdf2text.db",
        f"APP_PREFIX={prefix}",
        "",
    ]
    return "\n".join(lines)


def deploy_remote(config: dict, login: str, pwd: str):
    """Déploie l'application sur le serveur distant via SSH/SFTP."""
    try:
        import paramiko
    except ImportError:
        logger.error("Le module 'paramiko' est requis. Installez-le avec : uv pip install paramiko")
        sys.exit(1)

    machine = config["machine_name"]
    target_dir = config["target_directory"]
    # Supprimer le slash final pour la cohérence
    target_dir = target_dir.rstrip("/")

    # Collecter les fichiers à transférer
    files = collect_files(PROJECT_DIR)
    logger.info(f"📦 {len(files)} fichiers à transférer")

    # Connexion SSH
    logger.info(f"🔐 Connexion SSH à {login}@{machine}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect_kwargs = {"hostname": machine, "username": login}
        if pwd:
            connect_kwargs["password"] = pwd
        else:
            # Tenter la connexion par clé SSH par défaut
            logger.info("  Pas de mot de passe fourni, tentative par clé SSH...")
        ssh.connect(**connect_kwargs)
        logger.info("✅ Connexion SSH établie")
    except Exception as e:
        logger.error(f"❌ Échec de la connexion SSH : {e}")
        sys.exit(1)

    sftp = ssh.open_sftp()

    try:
        # Créer le répertoire cible s'il n'existe pas
        _ssh_exec(ssh, f"mkdir -p {target_dir}")

        # Créer les sous-répertoires nécessaires sur le serveur
        remote_dirs = set()
        for f in files:
            rel = f.relative_to(PROJECT_DIR)
            parent = str(rel.parent)
            if parent != ".":
                remote_dirs.add(parent)

        for d in sorted(remote_dirs):
            remote_path = f"{target_dir}/{d}"
            _ssh_exec(ssh, f"mkdir -p {remote_path}")

        # Transférer les fichiers
        transferred = 0
        for f in files:
            rel = f.relative_to(PROJECT_DIR)
            remote_path = f"{target_dir}/{rel}"
            try:
                sftp.put(str(f), remote_path)
                transferred += 1
                if transferred % 20 == 0:
                    logger.info(f"  📤 {transferred}/{len(files)} fichiers transférés...")
            except Exception as e:
                logger.warning(f"  ⚠️  Échec du transfert de {rel} : {e}")

        logger.info(f"📤 {transferred}/{len(files)} fichiers transférés avec succès")

        # Générer le .env de production s'il n'existe pas déjà
        try:
            sftp.stat(f"{target_dir}/.env")
            logger.info("📝 Le fichier .env existe déjà sur le serveur, il n'est pas écrasé")
        except FileNotFoundError:
            env_content = generate_env_file(config)
            with sftp.open(f"{target_dir}/.env", "w") as remote_env:
                remote_env.write(env_content)
            logger.info("📝 Fichier .env de production créé (pensez à modifier SECRET_KEY !)")

        # Créer les répertoires de données sur le serveur
        data_dirs = ["data", "data/db", "data/logs", "data/users", "data/temp"]
        for d in data_dirs:
            _ssh_exec(ssh, f"mkdir -p {target_dir}/{d}")
        logger.info("📁 Répertoires de données créés")

        # Installer les dépendances sur le serveur
        # L'environnement SSH non interactif ne charge pas tjs le ~/.profile, on ajoute les chemins courants d'install uv au PATH
        logger.info("📦 Installation des dépendances sur le serveur...")
        _ssh_exec(ssh, f"cd {target_dir} && export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv venv && uv pip install -r requirements.txt", show_output=True)

        logger.info("🎉 Déploiement terminé avec succès !")
        logger.info("")
        logger.info("═" * 60)
        logger.info("📋 ÉTAPES SUIVANTES :")
        logger.info(f"  1. Modifiez {target_dir}/.env (SECRET_KEY, etc.)")
        logger.info(f"  2. Configurez nginx (voir config/nginx_rpgpdf2txt.conf)")
        logger.info(f"  3. Installez le service systemd (voir config/rpgpdf2txt.service)")
        logger.info(f"  4. Lancez : sudo systemctl start rpgpdf2txt")
        logger.info("═" * 60)

    finally:
        sftp.close()
        ssh.close()
        logger.info("🔒 Connexion SSH fermée")


def dry_run(config: dict):
    """Affiche les fichiers qui seraient transférés, sans connexion SSH."""
    target_dir = config["target_directory"].rstrip("/")

    logger.info(f"🖥️  Machine cible  : {config['machine_name']}")
    logger.info(f"📁 Répertoire cible : {target_dir}")
    logger.info(f"🔗 Préfixe app     : {config['app_prefix']}")
    logger.info(f"🔌 Port            : {config['port']}")

    files = collect_files(PROJECT_DIR)
    logger.info(f"📦 {len(files)} fichiers seraient transférés :")
    logger.info("")
    for f in files:
        rel = f.relative_to(PROJECT_DIR)
        logger.info(f"   → {rel}")
    logger.info("")
    logger.info("🔍 Mode dry-run : aucun transfert effectué")


def _ssh_exec(ssh, command: str, show_output: bool = False):
    """Exécute une commande SSH et log le résultat."""
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    if show_output:
        output = stdout.read().decode().strip()
        if output:
            for line in output.split("\n"):
                logger.info(f"  [remote] {line}")
    err = stderr.read().decode().strip()
    if exit_code != 0 and err:
        logger.warning(f"  [remote stderr] {err}")
    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Déploiement distant de RPGPDF2Text sur le serveur cible"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les fichiers qui seraient transférés sans effectuer le déploiement"
    )
    args = parser.parse_args()

    logger.info("🚀 RPGPDF2Text — Script de déploiement distant")
    logger.info("")

    config = load_config()

    if args.dry_run:
        dry_run(config)
    else:
        login, pwd = get_credentials()
        deploy_remote(config, login, pwd)


if __name__ == "__main__":
    main()

