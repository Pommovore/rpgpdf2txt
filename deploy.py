#!/usr/bin/env python3
"""
Script de déploiement pour RPGPDF2Text (Local et Distant).

Options :
    --dev    : Déploiement local (installation des dépendances).
    --prod   : Déploiement complet distant (fichiers + config Nginx/Systemd).
    --update : Déploiement partiel distant (uniquement les fichiers suivis par git).
    --dry-run: Prévisualise les fichiers transférés (pour --prod ou --update).

Variables d'environnement requises (pour --prod et --update) :
    REMOTE_LOGIN  : nom d'utilisateur SSH
    REMOTE_PWD    : mot de passe SSH (ou utiliser une clé SSH)
"""

import os
import sys
import argparse
import yaml
import subprocess
from pathlib import Path
from loguru import logger

# ─── Configuration du logging ──────────────────────────────────────────────────
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

# ─── Chemins de base ────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent
CONFIG_PATH = PROJECT_DIR / "config" / "deploy.yaml"

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
            logger.error(f"Clé manquante dans deploy.yaml : {key}")
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


# Répertoires à ne jamais traverser ou transférer
EXCLUDE_DIRS = {".venv", ".git", "__pycache__", "data", "tokens", ".github"}

# Fichiers individuels à exclure
EXCLUDE_FILES = {
    ".env", 
    "ci_test.db", 
    "deploiement.py", 
    "deploy.py", 
    "update_deploy.py",
    "nginx_rpgpdf2txt.conf",
    "rpgpdf2txt.service"
}

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


def collect_git_files(base_dir: Path) -> list:
    """Collecte uniquement les fichiers suivis par git, en excluant ceux à ignorer."""
    result = subprocess.run(["git", "ls-files"], cwd=base_dir, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("Échec de la commande 'git ls-files', utilisation de la collecte standard (tous les fichiers).")
        return collect_files(base_dir)

    files = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        f = Path(line)
        # Exclusions manuelles supplémentaires
        if f.name in EXCLUDE_FILES or any(f.name.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
            continue
        if any(p in EXCLUDE_DIRS for p in f.parts):
            continue
        
        full_path = base_dir / f
        if not full_path.exists():
            continue
            
        files.append(full_path)

    return files


def generate_env_file(config: dict) -> str:
    """Génère le contenu du fichier .env pour la production."""
    prefix = config.get("app_prefix", "")
    lines = [
        "# Fichier .env généré automatiquement par deploy.py",
        "# Modifiez les valeurs ci-dessous selon votre environnement de production",
        "",
        "SECRET_KEY=CHANGEZ_MOI_CLE_TRES_LONGUE_ET_SECRETE",
        f"DATABASE_URL=sqlite:///./data/db/rpgpdf2text.db",
        f"APP_PREFIX={prefix}",
        "",
    ]
    return "\n".join(lines)


def deploy_local():
    """Effectue un déploiement local (mode --dev)."""
    logger.info("Démarrage du processus de préparation pour l'environnement: Développement Local")
    logger.info("Mise à jour des dépendances avec uv...")
    ret = os.system("uv sync")
    if ret == 0:
        logger.info("✅ Déploiement local terminé avec succès.")
        logger.info("🚀 Lancement du serveur local de développement...")
        try:
            os.system("uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        except KeyboardInterrupt:
            logger.info("\n🛑 Arrêt du serveur de développement et fin du script.")
    else:
        logger.error("❌ Échec lors de l'installation des dépendances.")


def _setup_ssh(config: dict, login: str, pwd: str):
    """Initialise et retourne une connexion SSH et SFTP."""
    try:
        import paramiko
    except ImportError:
        logger.error("Le module 'paramiko' est requis. Installez-le en local avec : uv pip install paramiko")
        sys.exit(1)

    machine = config["machine_name"]
    
    logger.info(f"🔐 Connexion SSH à {login}@{machine}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect_kwargs = {"hostname": machine, "username": login}
        if pwd:
            connect_kwargs["password"] = pwd
        else:
            logger.info("  Pas de mot de passe fourni, tentative par clé SSH...")
        ssh.connect(**connect_kwargs)
        logger.info("✅ Connexion SSH établie")
    except Exception as e:
        logger.error(f"❌ Échec de la connexion SSH : {e}")
        sys.exit(1)

    sftp = ssh.open_sftp()
    
    def run_sudo(cmd: str):
        """Exécute une commande en sudo proprement via la connexion SSH active."""
        if pwd:
            _ssh_exec(ssh, f"sudo -S {cmd}", show_output=True, sudo_pwd=pwd)
        else:
            _ssh_exec(ssh, f"sudo {cmd}", show_output=True)
            
    return ssh, sftp, run_sudo


def _run_db_migrations(ssh, target_dir: str):
    """Exécute les migrations de base de données nécessaires sur le serveur."""
    db_path = f"{target_dir}/data/db/rpgpdf2text.db"
    
    logger.info("🛠️  Vérification des migrations de base de données...")
    
    # 1. Ajouter la colonne api_token si elle n'existe pas
    check_col_cmd = f"sqlite3 {db_path} \"PRAGMA table_info(users);\""
    exit_code, output = _ssh_exec_with_output(ssh, check_col_cmd)
    
    if "api_token" not in output:
        logger.info("  ➕ Ajout de la colonne 'api_token' à la table 'users'...")
        _ssh_exec(ssh, f"sqlite3 {db_path} \"ALTER TABLE users ADD COLUMN api_token VARCHAR;\"")
        _ssh_exec(ssh, f"sqlite3 {db_path} \"CREATE UNIQUE INDEX ix_users_api_token ON users (api_token);\"")
    else:
        logger.info("  ✅ La colonne 'api_token' existe déjà.")

    # 2. Backfill des tokens via un script Python sur le serveur
    logger.info("  🔑 Vérification et backfill des tokens API...")
    
    remote_script_path = f"{target_dir}/tmp_migrate.py"
    py_backfill = f"""
import sqlite3
import secrets
try:
    conn = sqlite3.connect("{db_path}")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE api_token IS NULL AND (role IN ('admin', 'creator') OR is_validated = 1)")
    users = cur.fetchall()
    for u in users:
        token = secrets.token_urlsafe(32)
        cur.execute("UPDATE users SET api_token = ? WHERE id = ?", (token, u[0]))
    conn.commit()
    conn.close()
    print(f"Backfilled {{len(users)}} users")
except Exception as e:
    print(f"Migration error: {{e}}")
    exit(1)
"""
    # Créer le fichier sur le serveur
    _ssh_exec(ssh, f"cat << 'EOF' > {remote_script_path}\n{py_backfill}\nEOF")
    
    # Exécuter le script
    _ssh_exec(ssh, f"python3 {remote_script_path}", show_output=True)
    
    # Supprimer le script temporaire
    _ssh_exec(ssh, f"rm {remote_script_path}")
    
    logger.info("  ✅ Migrations terminées.")


def _ssh_exec_with_output(ssh, command: str):
    """Exécute une commande SSH et retourne le code de sortie et le stdout."""
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode().strip()
    return exit_code, output

def _transfer_files(ssh, sftp, files: list, target_dir: str):
    """Crée les dossiers distants et transfère les fichiers spécifiés."""
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


def deploy_remote(config: dict, login: str, pwd: str):
    """Déploie l'application complète sur le serveur distant (--prod)."""
    target_dir = config["target_directory"].rstrip("/")
    files = collect_files(PROJECT_DIR)
    logger.info(f"📦 {len(files)} fichiers à transférer en mode --prod")

    ssh, sftp, run_sudo = _setup_ssh(config, login, pwd)

    try:
        _transfer_files(ssh, sftp, files, target_dir)

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
        logger.info("📁 Répertoires de données vérifiés/créés")

        # Installer les dépendances sur le serveur
        logger.info("📦 Mise à jour des dépendances sur le serveur...")
        _ssh_exec(ssh, f"cd {target_dir} && export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv sync", show_output=True)

        logger.info("⚙️  Application des configurations globales (Nginx/Systemd)...")
        # Config Nginx
        run_sudo(f"cp {target_dir}/config/nginx_rpgpdf2txt.conf /etc/nginx/apps/rpgpdf2txt.conf")
        run_sudo("nginx -t")
        run_sudo("systemctl reload nginx")
        # Config Systemd
        run_sudo(f"cp {target_dir}/config/rpgpdf2txt.service /etc/systemd/system/")
        run_sudo("systemctl daemon-reload")
        # Exécuter les migrations DB
        _run_db_migrations(ssh, target_dir)

        run_sudo("systemctl restart rpgpdf2txt")
        
        logger.info("🎉 Déploiement global (--prod) terminé avec succès !")
        logger.info("═" * 60)
        logger.info("📋 RAPPEL :")
        logger.info(f"  - Vérifiez {target_dir}/.env (SECRET_KEY) si c'est la toute première installation.")
        logger.info("═" * 60)

    finally:
        sftp.close()
        ssh.close()
        logger.info("🔒 Connexion SSH fermée")


def update_remote(config: dict, login: str, pwd: str):
    """Met à jour uniquement le code distant (--update)."""
    target_dir = config["target_directory"].rstrip("/")
    logger.info("🔍 Mode --update : collecte restreinte aux fichiers suivis par git.")
    files = collect_git_files(PROJECT_DIR)
    logger.info(f"📦 {len(files)} fichiers à transférer")

    ssh, sftp, run_sudo = _setup_ssh(config, login, pwd)

    try:
        _transfer_files(ssh, sftp, files, target_dir)

        # Créer les répertoires de données sur le serveur juste au cas où
        data_dirs = ["data", "data/db", "data/logs", "data/users", "data/temp"]
        for d in data_dirs:
            _ssh_exec(ssh, f"mkdir -p {target_dir}/{d}")
            
        # Installer les dépendances sur le serveur
        logger.info("📦 Vérification des dépendances sur le serveur...")
        _ssh_exec(ssh, f"cd {target_dir} && export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv sync", show_output=True)

        # Exécuter les migrations DB
        _run_db_migrations(ssh, target_dir)

        logger.info("🔄 Mode --update : Redémarrage exclusif du service applicatif...")
        run_sudo("systemctl restart rpgpdf2txt")
        
        logger.info("✅ Service relancé avec le nouveau code.")

    finally:
        sftp.close()
        ssh.close()
        logger.info("🔒 Connexion SSH fermée")


def dry_run(config: dict, is_update: bool):
    """Affiche les fichiers qui seraient transférés, sans connexion SSH."""
    target_dir = config["target_directory"].rstrip("/")

    logger.info(f"🖥️  Machine cible  : {config['machine_name']}")
    logger.info(f"📁 Répertoire cible : {target_dir}")
    logger.info(f"🔗 Préfixe app     : {config['app_prefix']}")
    logger.info(f"🔌 Port            : {config['port']}")

    if is_update:
        logger.info("🔍 Mode --update : collecte restreinte aux fichiers suivis par git.")
        files = collect_git_files(PROJECT_DIR)
    else:
        files = collect_files(PROJECT_DIR)

    logger.info(f"📦 {len(files)} fichiers seraient transférés :")
    logger.info("")
    for f in files:
        rel = f.relative_to(PROJECT_DIR)
        logger.info(f"   → {rel}")
    logger.info("")
    logger.info("🔍 Mode --dry-run : aucun transfert ni action n'ont été effectués.")


def _ssh_exec(ssh, command: str, show_output: bool = False, sudo_pwd: str = None):
    """Exécute une commande SSH et log le résultat."""
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=bool(sudo_pwd))
    if sudo_pwd:
        stdin.write(sudo_pwd + "\n")
        stdin.flush()
    exit_code = stdout.channel.recv_exit_status()
    if show_output:
        output = stdout.read().decode().strip()
        if output:
            for line in output.split("\n"):
                if sudo_pwd and line.strip() == "[sudo] password for": continue
                logger.info(f"  [remote] {line}")
    err = stderr.read().decode().strip()
    if exit_code != 0 and err:
        logger.warning(f"  [remote stderr] {err}")
    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Script de déploiement RPGPDF2Text (Local et Distant)"
    )
    parser.add_argument("--dev", action="store_true", help="Déployer en environnement de développement (local)")
    parser.add_argument("--prod", action="store_true", help="Déploiement complet en production (distant)")
    parser.add_argument("--update", action="store_true", help="Mise à jour légère en production (git-tracked, pas de modif Nginx/Systemd)")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les fichiers qui seraient transférés sans effectuer le déploiement")
    
    args = parser.parse_args()

    # Vérification des options
    if not any([args.dev, args.prod, args.update]):
        logger.error("❌ Action manquante : Veuillez spécifier --dev, --prod ou --update.")
        parser.print_help()
        sys.exit(1)

    logger.info("🚀 RPGPDF2Text — Opération de déploiement initiée")
    logger.info("")

    if args.dev:
        deploy_local()
        return

    # Pour --prod et --update, on charge la configuration distante
    config = load_config()

    if args.dry_run:
        dry_run(config, is_update=args.update)
    else:
        login, pwd = get_credentials()
        if args.update:
            update_remote(config, login, pwd)
        else:
            deploy_remote(config, login, pwd)


if __name__ == "__main__":
    main()

