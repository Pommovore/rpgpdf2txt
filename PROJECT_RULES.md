# Règles et Conventions du Projet RPGPDF2Text

Ce document définit les standards de développement, l'architecture et les workflows à respecter pour maintenir la cohérence et la qualité du projet.

## 1. Technologies Principales

*   **Backend** : Python 3.12+ avec FastAPI.
*   **Base de données** : SQLite (Dev/Test/Prod) via SQLAlchemy.
*   **Frontend** : HTML5, CSS3, JavaScript (Vanilla), Bootstrap 5.3.
*   **Gestionnaire de dépendances** : `uv`.

## 2. Architecture & Organisation du Code

### Backend
*   **Structure Modulaire** : Utiliser les **Blueprints** FastAPI pour organiser les routes par domaine fonctionnel (ex: `routes/auth_routes.py`, `routes/event_routes.py`).
*   **Logique Métier** : Déporter la logique complexe dans des **Services** (`services/`) plutôt que de la laisser dans les routes.
*   **Modèles** : Définis dans `models.py`. Utiliser SQLAlchemy ORM.
*   **Gestion des Erreurs** : Utiliser des blocs `try/except` et retourner des messages flash ou JSON appropriés.
*   **Éviter les requêtes N+1** : Utiliser `joinedload` dans les requêtes SQLAlchemy pour charger les relations efficacement.

### Frontend
*   **Framework UI** : **Bootstrap 5** est le standard. Ne pas introduire d'autres frameworks CSS lourds (ex: Tailwind) sans validation.
*   **Icônes** : Utiliser **Bootstrap Icons** (`bi bi-nom-icone`).
*   **Templating** : Jinja2. Utiliser l'héritage de templates (`{% extends "base.html" %}`).
*   **JavaScript** : Écrire du JS moderne (ES6+). Placer les scripts spécifiques dans `static/js/`. Tout le code javascript qui peut être externalisé des fichiers html doit l'être.

## 3. Conventions de Nommage et Langue

*   **Code (Variables, Fonctions, Classes)** : Anglais (`get_user`, `Event`, `is_organizer`).
*   **Commentaires et Docstrings** : Français (pour faciliter la compréhension par l'équipe).
*   **Interfaces Utilisateur (UI)** : Français.
*   **Base de Données** : Noms de tables et colonnes en Anglais (`user`, `event_id`, `created_at`).

## 4. Base de Données

*   **Migrations** : Utiliser **Flask-Migrate** (`alembic`).
    *   Toute modification de schéma DOIT passer par une migration.
    *   Commandes : `flask db migrate -m "Description"` puis `flask db upgrade`.
*   **Contraintes** : Définir explicitement les Foreign Keys et Index.

## 5. Workflow de Développement

### Démarrage
*   Activer l'environnement virtuel : `source .venv/bin/activate` (ou via `uv`).
*   Lancer le serveur de dev : `uv run flask run` ou via `run_local.sh`.

### Déploiement
*   Utiliser le script `update_deploy.py`.
*   **NE PAS** modifier les fichiers directement sur le serveur de production.
*   Toujours tester en local (`--dev`) avant de déployer en production (`--prod`).
*   Commande : `uv run python update_deploy.py --dev` (ou `--prod`).

## 6. Bonnes Pratiques

*   **Sécurité** :
    *   Utiliser les décorateurs `@login_required` et `@admin_required`.
    *   Protéger les formulaires avec CSRF (`form.hidden_tag()` ou `csrf_token`).
*   **Logs** : Utiliser `ActivityLog` pour tracer les actions importantes (création, modification, suppression).
*   **Code Propre** : Supprimer le code mort et les `print` de debug avant de commiter.
