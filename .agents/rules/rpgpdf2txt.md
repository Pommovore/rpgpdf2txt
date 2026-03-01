---
trigger: always_on
---

# Instructions spécifiques au projet RPSPDF2TXT

Tu es un expert Python optimisant le flux de travail avec l'outil 'uv'. 
Toutes tes propositions de commandes et ton exécution de code doivent suivre ces règles :

1. GESTION DES PACKAGES :
   - N'utilise JAMAIS `pip install`. Utilise exclusivement `uv add <package>`.
   - Pour supprimer un package : `uv remove <package>`.
   - Pour synchroniser l'environnement : `uv sync`.

2. EXÉCUTION DE SCRIPTS :
   - Pour lancer un script Python, utilise toujours le préfixe `uv run`. 
     Exemple : `uv run main.py` au lieu de `python main.py`.
   - Si un script nécessite une dépendance sans l'installer dans le projet, utilise : 
     `uv run --with <package> <script>.py`.

3. GESTION DES ENVIRONNEMENTS :
   - Si tu dois créer un environnement, utilise `uv venv`.
   - Rappelle-toi que `uv` gère automatiquement l'isolation, il n'est donc pas nécessaire d'activer manuellement le venv dans tes instructions de commande.

4. FICHIERS DE CONFIGURATION :
   - Priorise la lecture et la modification du fichier `pyproject.toml`.
   - Ignore le fichier `requirements.txt` sauf pour l'importer via `uv pip compile`.

5. STYLE :
   - Sois concis et privilégie les One-Liners avec `uv run` pour tester des extraits de code.

6. COMMITS :
   - Ne fais jamais de "git commit" sans que je ne te l'aie demandé.