# RPGPDF2Text

RPGPDF2Text est une application web développée sous **FastAPI** permettant l'extraction intelligente de textes à partir de fichiers PDF (natifs ou scannés) et leur correction linguistique automatique via l'Intelligence Artificielle (Hugging Face).

L'infrastructure intègre un système d'identification strict à 3 rôles (Créateur, Administrateurs, Utilisateurs) garantissant la protection et l'isolation des données extraites.

## Fonctionnalités

- 📄 **Extraction de texte** depuis des PDF natifs (PyMuPDF) ou scannés (OCR via Tesseract)
- 🤖 **Correction IA** automatique via l'API HuggingFace (Meta-Llama-3-8B-Instruct)
- 🔐 **Authentification JWT** avec 3 niveaux de rôles (Créateur, Admin, Utilisateur)
- 🔔 **Notifications Webhook** vers Discord ou tout service externe
- 📊 **Dashboard** avec historique des extractions et téléchargement des résultats
- 🌐 **Déploiement derrière un reverse proxy** (Nginx) avec préfixe d'URL configurable

## Documentation

| Document | Description |
|---|---|
| 📖 [Description Fonctionnelle](doc/DESCRIPTION.md) | Parcours utilisateur, rôles, pipeline d'extraction |
| ⚙️ [Architecture Technique](doc/ARCHITECTURE.md) | Stack technique, structure des dossiers, services |
| 🚀 [Guide de Déploiement](doc/DEPLOIEMENT.md) | Déploiement en production (SSH, Nginx, Systemd) |

## Stack Technique

| Composant | Technologie |
|---|---|
| Backend | Python 3.12+, FastAPI, Uvicorn |
| Base de données | SQLite + SQLAlchemy ORM |
| Frontend | Jinja2, Bootstrap 5, JavaScript ES6+ |
| Extraction PDF | PyMuPDF, pdf2image, pytesseract |
| Correction IA | API HuggingFace (Serverless Inference) |
| Logging | Loguru |
| Déploiement | uv, Nginx (reverse proxy), Systemd |

## Démarrage Rapide (Local)

### Prérequis système

```bash
# Ubuntu / Debian / WSL
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-fra
```

### Lancement

```bash
# Installer uv (si pas déjà fait)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Démarrer le serveur de développement
bash run_local.sh
```

L'interface web sera accessible sur `http://localhost:8000`. Lors de la première visite, une page de Setup vous invitera à configurer votre clé API Hugging Face et votre compte créateur.

## Déploiement en Production

Le déploiement est entièrement automatisé via un script SSH. Voir le **[Guide de Déploiement](doc/DEPLOIEMENT.md)** pour les instructions complètes.

```bash
# Prévisualiser les fichiers à transférer
python deploiement.py --dry-run

# Déployer sur le serveur
REMOTE_LOGIN=user REMOTE_PWD=password python deploiement.py
```

## Structure du Projet

```
rpgpdf2txt/
├── app/
│   ├── core/           # Configuration (config.py) et sécurité (security.py)
│   ├── db/             # Modèles SQLAlchemy et initialisation DB
│   ├── routes/         # Routes FastAPI (views, auth, API)
│   ├── services/       # Logique métier (extraction, IA, webhooks)
│   ├── static/js/      # JavaScript externalisé
│   └── templates/      # Templates Jinja2
├── config/
│   ├── deployment.yaml         # Configuration de déploiement
│   ├── nginx_rpgpdf2txt.conf   # Configuration Nginx
│   └── rpgpdf2txt.service      # Service Systemd
├── data/               # Données d'exploitation (généré à l'exécution)
│   ├── db/             # Base de données SQLite
│   ├── logs/           # Journaux applicatifs
│   ├── temp/           # Fichiers PDF temporaires
│   └── users/          # Répertoires des utilisateurs
├── doc/                # Documentation du projet
├── deploiement.py      # Script de déploiement distant (SSH/SFTP)
├── requirements.txt    # Dépendances Python
└── run_local.sh        # Script de lancement local
```


## Licence

Ce projet est sous licence **GNU Affero General Public License v3.0 (AGPL-3.0)**.

Cela signifie que :
- ✅ **Vous pouvez** utiliser, modifier et distribuer ce logiciel.
- 🔗 **Effet copyleft** : Si vous modifiez ce code et le distribuez (ou l'hébergez sur un serveur pour que d'autres l'utilisent), vous **devez** publier vos modifications sous la même licence AGPL.
- 🔓 **Accès au code** : Les utilisateurs de votre version doivent pouvoir télécharger votre code source.

Voir **[Licence](doc/LICENSE.md)** pour le texte complet.