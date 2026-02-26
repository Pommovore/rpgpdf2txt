# RPGPDF2Text

RPGPDF2Text est une application robuste développée sous FastAPI permettant l'extraction intelligente de textes à partir de fichiers PDF (natifs ou scannés) et leur correction linguistique automatique via l'Intelligence Artificielle (Hugging Face).

L'infrastructure intègre un système d'identification strict à 3 rôles (Créateur, Administrateurs, Utilisateurs) garantissant la protection et l'isolation des données extraites.

## Documentation Détaillée

Pour comprendre le projet plus en profondeur, veuillez vous référer aux deux documents suivants :

- 📖 **[Description Fonctionnelle (doc/DESCRIPTION.md)](doc/DESCRIPTION.md)** : Décrit le parcours utilisateur, la gestion des rôles, et le fonctionnement étape par étape du pipeline d'extraction PDF.
- ⚙️ **[Architecture & Déploiement (doc/ARCHITECTURE.md)](doc/ARCHITECTURE.md)** : Détaille la stack technique (FastAPI, SQLite, SQLAlchemy, uv, Uvicorn, Hugging Face API), la structure des dossiers internes, et la procédure complète de déploiement en local ou production.

## Démarrage Rapide

Si les prérequis systèmes (`poppler-utils`, `tesseract-ocr`) sont installés sur votre machine fonctionnant sous Linux/WSL :

```bash
# S'assurer d'avoir `uv` installé
curl -LsSf https://astral.sh/uv/install.sh | sh

# Démarrer le script de lancement local
bash run_local.sh
```

L'interface web et l'API seront alors instantanément accessibles sur `http://localhost:8000`. Lors de votre toute première visite, une page de Setup vous invitera à configurer votre clé API Hugging Face et votre compte administrateur.
