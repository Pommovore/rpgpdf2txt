# Architecture de RPGPDF2Text

Ce document détaille l'architecture sous-jacente de RPGPDF2Text, ainsi que les instructions nécessaires à son déploiement. L'application respecte les conventions définies dans `PROJECT_RULES.md`.

## Composition Technologique
- **Framework** : FastAPI (Python 3.10+).
- **Gestionnaire de paquets/d'exécution** : `uv`
- **Frontend** : Modèles Jinja2, Bootstrap 5 pur (sans frameworks JS complexes), et icônes Bootstrap. Les fichiers Javascript sont externalisés dans `/app/static/js/`. La langue par défaut du code front/back est le français (UI, docstrings).
- **Base de données** : SQLite gérée avec **SQLAlchemy** (ORM). Modèles décrits dans `app/db/models.py`.
- **Méthodologies d'Extraction** : `PyMuPDF` (Extraction texte pure), `pdf2image` + `pytesseract` (OCR).
- **LLM/Correction** : L'API d'inference **Hugging Face** en Serverless (`meta-llama/Meta-Llama-3-8B-Instruct`).
- **Traçabilité** : Journalisation fine à l'aide de **Loguru** écrivant dans `/data/logs/app.log`. Actions utilisateurs consignées dans la table SQL `ActivityLog`.

## Structure Dossiers `app/`

- `/routes/` : Regroupe les différents contrôleurs de l'application (API Web pour l'interface `view_routes.py`, Authentification `auth_routes.py`, requêtes fonctionnelles métier `api_routes.py`).
- `/core/` : Paramètres de l'application via `pydantic-settings` et module cryptographique `bcrypt` et JWT pour la tokenisation (`security.py`).
- `/services/` : La logique asynchrone lourde et métier. Extraction (`pdf_extractor.py`), IA (`hf_corrector.py`), webhooks (`webhook.py`).
- `/db/` : Les modèles de données et l'initialisation SQLAlchemy.
- `/templates/` & `/static/` : Interface de l'application et JS.

Dossiers d'exploitation (générés à l'exécution) :
- `/data/db/` : Base de données SQLite.
- `/data/logs/` : Journaux de fonctionnement.
- `/data/users/` : Répertoires physiques des utilisateurs hébergeant les dépôts des extractions.
- `/data/temp/` : Emplacement temporaire des upload PDF avant traitement.

## Procédure de Déploiement

Le système prévoit deux environnements de déploiements. Le processus d'installation global est géré via le binaire `uv` pour les dépendances.

### 1. Prérequis Serveur (Linux Ubuntu/WSL)
Avant toute chose, vous devrez posséder :
- **Python 3.10+** (et `curl` ou `wget` pour instancier `uv`).
- Les librairies systèmes pour le traitement PDF :
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-fra
```

### 2. Variables d'Environnement
Vous pouvez définir un fichier `.env` à la racine pour forcer la configuration :
```
SECRET_KEY=une_super_cle_secrete_longue
DATABASE_URL=sqlite:///./data/db/rpgpdf2text.db
```

### 3. Utilisation de l'outil de gestion `update_deploy.py`

Le script personnalisé `update_deploy.py` simule ou prépare l'environnement via la CI ou sur le serveur. Il agit sur deux flags selon le comportement voulu : 

**Pour développer en local** :
Vous pouvez utiliser le script shell `bash run_local.sh`, ou passer par le script via :
```bash
python update_deploy.py --dev
```

**Pour la mise en production** :
```bash
python update_deploy.py --prod
```
Cette commande prépare le terrain de production et s'assure que les commandes `uv` nécessaires pour installer le `requirements.txt` soient prises en compte.

Dans les deux cas, le gestionnaire `uv` est responsable d'installer `/requirements.txt` en utilisant votre environnement virtuel. 
Pour démarrer finalement le service à la main :
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```
