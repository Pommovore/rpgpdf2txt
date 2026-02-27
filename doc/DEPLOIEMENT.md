# Guide de Déploiement — RPGPDF2Text

Ce document décrit le processus complet pour déployer RPGPDF2Text sur un serveur Linux Ubuntu 22.04, derrière un reverse proxy Nginx.

## Architecture de Déploiement

```
┌──────────────┐       ┌─────────────┐       ┌──────────────────────┐
│   Client     │──────▶│   Nginx     │──────▶│  Uvicorn (FastAPI)   │
│  (Navigateur)│ HTTPS │  port 80/443│ HTTP  │  port 8885           │
└──────────────┘       │  /rpgpdf2txt│       │  /opt/rpgpdf2txt/    │
                       └─────────────┘       └──────────────────────┘
```

---

## 1. Prérequis Serveur

### Système

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-fra
```

### Installer `uv` (gestionnaire de paquets Python)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Configuration

Toute la configuration de déploiement est centralisée dans **`config/deployment.yaml`** :

```yaml
deploy:
  machine_name: "minimoi.mynetgear.com"  # Nom/IP du serveur cible
  port: 8885                             # Port d'écoute de l'application
  target_directory: "/opt/rpgpdf2txt/"   # Répertoire d'installation
  app_prefix: "/rpgpdf2txt"              # Préfixe URL (reverse proxy)
```

> **Important :** Le champ `app_prefix` est utilisé par l'application pour calculer dynamiquement toutes les routes, redirections, et URLs des fichiers statiques.

---

## 3. Déploiement Automatique

Le script `deploiement.py` automatise le transfert de l'application vers le serveur distant via SSH.

### Dépendance locale

```bash
uv pip install paramiko
```

### Prévisualisation (dry-run)

Sans identifiants, pour voir les fichiers qui seraient transférés :

```bash
python deploiement.py --dry-run
```

### Déploiement réel

```bash
REMOTE_LOGIN=utilisateur REMOTE_PWD=motdepasse python deploiement.py
```

Le script effectue automatiquement :
1. Connexion SSH au serveur défini dans `deployment.yaml`
2. Création du répertoire cible (`/opt/rpgpdf2txt/`)
3. Transfert de tous les fichiers du projet (hors `.venv`, `data/`, `.git/`, `.env`)
4. Génération du fichier `.env` de production (s'il n'existe pas)
5. Création des répertoires de données (`data/db`, `data/logs`, `data/users`, `data/temp`)
6. Création d'un environnement virtuel et installation des dépendances (`uv venv && uv pip install -r requirements.txt`)

> **Fichiers exclus du transfert :** `.venv/`, `.git/`, `__pycache__/`, `data/`, `.env`, `.github/`, `deploiement.py`, `*.pyc`

---

## 4. Configuration du Serveur

### 4.1 Fichier `.env` de Production

Le script `deploiement.py` génère un `.env` sur le serveur. **Vous devez modifier `SECRET_KEY`** :

```bash
sudo nano /opt/rpgpdf2txt/.env
```

```env
SECRET_KEY=VOTRE_CLE_TRES_LONGUE_ET_SECRETE
DATABASE_URL=sqlite:///./data/db/rpgpdf2text.db
APP_PREFIX=/rpgpdf2txt
```

### 4.2 Permissions

L'application et l'environnement virtuel sont créés par votre utilisateur SSH. Il est recommandé de laisser cet utilisateur propriétaire. Assurez-vous simplement que les droits sont corrects :

```bash
sudo chown -R $USER:$USER /opt/rpgpdf2txt
sudo chmod -R 755 /opt/rpgpdf2txt
sudo chmod -R 775 /opt/rpgpdf2txt/data
```

---

## 5. Configuration Nginx

Le fichier de configuration est fourni dans `config/nginx_rpgpdf2txt.conf`.

### Installation

```bash
sudo cp config/nginx_rpgpdf2txt.conf /etc/nginx/sites-available/rpgpdf2txt
sudo ln -s /etc/nginx/sites-available/rpgpdf2txt /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Points clés de la configuration

| Paramètre | Valeur | Rôle |
|---|---|---|
| `proxy_pass` | `http://127.0.0.1:8885/` | Redirection vers Uvicorn |
| `X-Forwarded-Prefix` | `/rpgpdf2txt` | Indique le préfixe à FastAPI |
| `client_max_body_size` | `50M` | Taille max des uploads PDF |
| `proxy_read_timeout` | `300s` | Timeout pour les extractions longues |

### HTTPS (recommandé)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d minimoi.mynetgear.com
```

---

## 6. Service Systemd

Le fichier de service est fourni dans `config/rpgpdf2txt.service`.

### Installation

```bash
sudo cp config/rpgpdf2txt.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rpgpdf2txt
sudo systemctl start rpgpdf2txt
```

### Commandes utiles

| Commande | Description |
|---|---|
| `sudo systemctl status rpgpdf2txt` | Vérifier l'état du service |
| `sudo systemctl restart rpgpdf2txt` | Redémarrer l'application |
| `sudo systemctl stop rpgpdf2txt` | Arrêter l'application |
| `sudo journalctl -u rpgpdf2txt -f` | Suivre les logs en temps réel |
| `sudo journalctl -u rpgpdf2txt --since "1 hour ago"` | Logs de la dernière heure |

### Sécurité du service

Le service tourne avec des protections renforcées :
- **Utilisateur** : L'utilisateur qui a déployé l'application (ex: `jack`), pour avoir accès à l'environnement virtuel `.venv`.
- **`NoNewPrivileges`** : empêche l'escalade de privilèges
- **`ProtectSystem=strict`** : système de fichiers en lecture seule
- **`ProtectHome=read-only`** : la lecture du dossier utilisateur est requise, car `uv` a besoin d'accéder aux binaires Python gérés dans `~/.local/` (via les liens symboliques du `.venv`)
- **`ReadWritePaths`** : seul `/opt/rpgpdf2txt/data` est accessible en écriture

---

## 7. Vérification Post-Déploiement

### Checklist

1. **Service actif ?**
   ```bash
   sudo systemctl status rpgpdf2txt
   ```

2. **Nginx répond ?**
   ```bash
   curl -I http://localhost/rpgpdf2txt/login
   ```

3. **Logs applicatifs ?**
   ```bash
   tail -f /opt/rpgpdf2txt/data/logs/app.log
   ```

4. **Base de données créée ?**
   ```bash
   ls -la /opt/rpgpdf2txt/data/db/rpgpdf2text.db
   ```

---

## 8. Mise à Jour

Pour mettre à jour l'application après des modifications :

```bash
# Depuis la machine de développement
REMOTE_LOGIN=utilisateur REMOTE_PWD=motdepasse python deploiement.py

# Sur le serveur, redémarrer le service
sudo systemctl restart rpgpdf2txt
```

> **Note :** Le fichier `.env` n'est jamais écrasé lors d'un redéploiement. Les données dans `data/` sont également préservées.

---

## Arborescence des fichiers de configuration

```
config/
├── deployment.yaml          # Configuration centrale de déploiement
├── nginx_rpgpdf2txt.conf    # Configuration Nginx (reverse proxy)
└── rpgpdf2txt.service       # Fichier de service Systemd
```
