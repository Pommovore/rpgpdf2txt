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

> [!NOTE]
> Nginx transmet les requêtes **avec le chemin complet** (ex: `/rpgpdf2txt/login`).
> L'application monte ses routes sous le préfixe `APP_PREFIX` dans `main.py` et gère ces chemins nativement.
> Il n'y a **pas** de `root_path` ni de `--root-path` dans la configuration uvicorn.

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

> [!IMPORTANT]
> Après l'installation de `uv`, assurez-vous que `~/.local/bin` est dans votre `PATH`.
> Si ce n'est pas le cas, ajoutez cette ligne à votre `~/.bashrc` :
> ```bash
> export PATH=$PATH:$HOME/.local/bin
> ```

---

## 2. Configuration

Toute la configuration de déploiement est centralisée dans **`config/deploy.yaml`** :

```yaml
deploy:
  machine_name: "minimoi.mynetgear.com"  # Nom/IP du serveur cible
  port: 8885                             # Port d'écoute de l'application
  target_directory: "/opt/rpgpdf2txt/"   # Répertoire d'installation
  app_prefix: "/rpgpdf2txt"              # Préfixe URL (reverse proxy)
```

> [!IMPORTANT]
> Le champ `app_prefix` est utilisé par l'application pour monter dynamiquement **toutes les routes, redirections, et fichiers statiques** sous ce préfixe.

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
1. Connexion SSH au serveur défini dans `deploy.yaml`
2. Création du répertoire cible (`/opt/rpgpdf2txt/`)
3. Transfert de tous les fichiers du projet (hors exclusions)
4. Génération du fichier `.env` de production (s'il n'existe pas déjà)
5. Création des répertoires de données (`data/db`, `data/logs`, `data/users`, `data/temp`)
6. Création d'un environnement virtuel et installation des dépendances (`uv venv && uv pip install -r requirements.txt`)

> [!NOTE]
> **Fichiers exclus du transfert :** `.venv/`, `.git/`, `__pycache__/`, `data/`, `.env`, `.github/`, `deploy.py`, `*.pyc`
>
> Le fichier `.env` n'est **jamais** écrasé lors d'un redéploiement. Les données dans `data/` sont également préservées.

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

L'application et l'environnement virtuel sont créés par votre utilisateur SSH (ex: `jack`). Il est recommandé de laisser cet utilisateur propriétaire :

```bash
sudo chown -R $USER:$USER /opt/rpgpdf2txt
sudo chmod -R 755 /opt/rpgpdf2txt
sudo chmod -R 775 /opt/rpgpdf2txt/data
```

> [!CAUTION]
> Ne changez **pas** le propriétaire en `www-data`. Le service systemd tourne sous l'utilisateur qui a déployé l'application, car `uv` crée des liens symboliques vers `~/.local/share/uv/` qui doivent rester accessibles.

---

## 5. Configuration Nginx

Le fichier de configuration est fourni dans `config/nginx_rpgpdf2txt.conf`.

### Installation

```bash
# Adaptez le chemin selon votre configuration nginx
sudo cp /opt/rpgpdf2txt/config/nginx_rpgpdf2txt.conf /etc/nginx/apps/rpgpdf2txt.conf
sudo nginx -t
sudo systemctl reload nginx
```

### Points clés de la configuration

| Paramètre | Valeur | Rôle |
|---|---|---|
| `proxy_pass` | `http://127.0.0.1:8885` | Proxy vers Uvicorn (**sans** `/` final) |
| `client_max_body_size` | `50M` | Taille max des uploads PDF |
| `proxy_read_timeout` | `300s` | Timeout pour les extractions longues |

> [!WARNING]
> Le `proxy_pass` ne doit **pas** avoir de slash final (`/`). L'application gère elle-même les chemins préfixés. Si vous mettez un slash, le préfixe sera supprimé par nginx et les routes ne fonctionneront pas correctement.

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
sudo cp /opt/rpgpdf2txt/config/rpgpdf2txt.service /etc/systemd/system/
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

| Directive | Valeur | Rôle |
|---|---|---|
| `User` / `Group` | `jack` | L'utilisateur qui a déployé (accès au `.venv`) |
| `NoNewPrivileges` | `true` | Empêche l'escalade de privilèges |
| `ProtectSystem` | `strict` | Système de fichiers en lecture seule |
| `ProtectHome` | `read-only` | Lecture seule sur `/home` (requis pour les binaires `uv`) |
| `PrivateTmp` | `true` | `/tmp` privé et isolé (requis pour les uploads multipart) |
| `ReadWritePaths` | `/opt/rpgpdf2txt/data` | Seul dossier de données en écriture |

> [!IMPORTANT]
> **`PrivateTmp=true`** est indispensable. Sans cette directive, Starlette (FastAPI) ne peut pas écrire les fichiers uploadés dans un répertoire temporaire, ce qui provoque une erreur `400 Bad Request` ("There was an error parsing the body").

---

## 7. Vérification Post-Déploiement

### Checklist

1. **Service actif ?**
   ```bash
   sudo systemctl status rpgpdf2txt
   # Doit afficher : Active: active (running)
   ```

2. **Nginx répond ?**
   ```bash
   curl -I http://localhost/rpgpdf2txt/login
   # Doit retourner : HTTP/1.1 200 OK
   ```

3. **Logs applicatifs ?**
   ```bash
   tail -f /opt/rpgpdf2txt/data/logs/app.log
   ```

4. **Base de données créée ?**
   ```bash
   ls -la /opt/rpgpdf2txt/data/db/rpgpdf2text.db
   ```

5. **Upload fonctionnel ?**
   - Connectez-vous au dashboard et tentez une extraction PDF
   - Vérifiez les logs : les étapes 1/4 à 4/4 doivent s'afficher

---

## 8. Mise à Jour

Pour mettre à jour l'application après des modifications :

```bash
# Depuis la machine de développement
REMOTE_LOGIN=utilisateur REMOTE_PWD=motdepasse python deploiement.py

# Sur le serveur, copier les fichiers de config si modifiés
sudo cp /opt/rpgpdf2txt/config/rpgpdf2txt.service /etc/systemd/system/
sudo systemctl daemon-reload

# Redémarrer le service
sudo systemctl restart rpgpdf2txt
```

---

## 9. Dépannage

### Erreurs courantes

| Symptôme | Cause | Solution |
|---|---|---|
| `Permission denied` au démarrage | `ProtectHome=true` empêche l'accès aux binaires `uv` | Mettre `ProtectHome=read-only` |
| `No module named uvicorn` | Dépendances non installées dans le venv | `cd /opt/rpgpdf2txt && uv pip install -r requirements.txt` |
| `400 Bad Request` sur `/extract` | `/tmp` non accessible (ProtectSystem=strict) | Ajouter `PrivateTmp=true` au service systemd |
| `uv: command not found` (SSH) | `~/.local/bin` pas dans le PATH non-interactif | `export PATH=$PATH:$HOME/.local/bin` avant d'appeler `uv` |
| Double préfixe dans les URLs | `root_path` défini à la fois dans FastAPI et `--root-path` | Ne **pas** utiliser `--root-path`, le préfixe est géré par le montage des routes |

---

## Arborescence des fichiers de configuration

```
config/
├── deploy.yaml          # Configuration centrale de déploiement
├── nginx_rpgpdf2txt.conf    # Configuration Nginx (reverse proxy)
└── rpgpdf2txt.service       # Fichier de service Systemd
```
