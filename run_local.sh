#!/bin/bash
# Démarrage du serveur de développement
# En utilisant uv comme spécifié dans les règles du projet

echo "Vérification des dépendances..."
uv pip install -r requirements.txt

echo "Démarrage du serveur RPGPDF2Text..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
