# Fonctionnement de RPGPDF2Text

RPGPDF2Text est une application web conçue pour faciliter l'extraction de texte propre depuis des fichiers PDF, qu'il s'agisse de documents natifs ou de scans. Le système intègre nativement une correction avancée via l'intelligence artificielle pour s'affranchir des coquilles classiques liées à la reconnaissance optique de caractères (OCR).

## Rôles Utilisateurs

Le système repose sur une hiérarchie stricte à 3 niveaux :

### 1. Le Créateur (Super-Administrateur)
- Déploie et configure l'application (Token API, Webhook Global).
- Accède à l'administration complète.

### 2. Les Administrateurs
- Accèdent à l'interface d'administration `/admin`.
- Peuvent lister toutes les demandes d'inscription.
- Doivent valider manuellement chaque compte pour lui donner accès au service.

### 3. Les Utilisateurs
- Devront s'inscrire via une adresse e-mail.
- Devront attendre la validation de leur compte.
- Une fois validés, ils accèdent au tableau de bord (`/dashboard`) pour soumettre de nouveaux PDF et consulter l'historique de leurs extractions passées.

## Pipeline d'Extraction (Le parcours du fichier)

Lorsqu'un utilisateur soumet un PDF depuis son tableau de bord :
1. **Dépôt** : Le PDF est envoyé accompagné d'un identifiant texte (pour le nommage) et d'une URL de Webhook.
2. **Identification** : L'application analyse brièvement le fichier en tâche de fond. 
3. **Extraction Physique** : 
    - S'il contient du texte natif (police embarquée), le texte est directement extrait de façon propre et rapide.
    - S'il s'agit d'un scan (image), l'application convertit les pages en images et applique une reconnaissance optique de caractère (OCR).
4. **Correction Sémantique** : Le texte brut extrait n'est pas toujours parfait. Il est par la suite soumis à un grand modèle de langage hébergé (via Hugging Face) pour en corriger la syntaxe et les potentielles coquilles de l'OCR.
5. **Livraison** : 
    - Le texte final corrigé est compilé dans un document `.txt`.
    - Le document est isolé dans le répertoire personnel et sécurisé de l'utilisateur hébergé sur le serveur principal (ex: `/data/users/email_at_domaine_com/`).
    - L'application prévient simultanément le service tiers (sur l'URL webhook fournie à l'étape 1) du succès de l'opération en lui envoyant le contenu final.

Ce fonctionnement garantit une isolation de la donnée tout en permettant au service tiers (bot Discord, site web, intégration personnalisée) d'exploiter la donnée proprement formatée dès qu'elle est prête.

## Exemple d'utilisation de l'API avec cURL

Pour interagir avec l'API, vous devez d'abord obtenir un token d'authentification (JWT), puis l'utiliser pour soumettre votre PDF.

### 1. Obtenir un token d'authentification

L'API utilise le standard OAuth2 avec `username` (qui correspond à votre email) et `password`.

```bash
curl -X POST "https://votre-domaine.com/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=votre_email@domaine.com&password=votre_mot_de_passe"
```

Si vos identifiants sont corrects et que votre compte est validé, le serveur vous renverra une réponse JSON contenant votre token :

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
  "token_type": "bearer"
}
```

### 2. Soumettre un document PDF à l'extraction

#### Option A: Avec le token d'authentification (JWT)
Utilisez la valeur de `access_token` obtenue à l'étape précédente dans l'en-tête `Authorization` pour lancer l'extraction :

```bash
curl -X POST "https://votre-domaine.com/api/v1/extract" \
  -H "Authorization: Bearer VOTRE_TOKEN_JWT" \
  -F "id_texte=mon_texte_01" \
  -F "webhook_url=https://votre-site.com/webhook/reception" \
  -F "ia_validate=true" \
  -F "pdf_file=@/chemin/vers/votre_fichier.pdf"
```

#### Option B: Avec votre Token d'API personnel
Il est possible d'utiliser un **Token d'API statique**, disponible sur votre interface Tableau de Bord une fois votre compte validé. 
Cette méthode est plus simple car le token n'expire jamais. Utilisez l'en-tête `token` dans votre requête :

```bash
curl -X POST "https://votre-domaine.com/api/v1/extract" \
  -H "token: VOTRE_TOKEN_API" \
  -F "id_texte=mon_texte_01" \
  -F "webhook_url=https://votre-site.com/webhook/reception" \
  -F "ia_validate=true" \
  -F "pdf_file=@/chemin/vers/votre_fichier.pdf"
```

### Paramètres de la requête :
- **Authorization** : Token JWT de l'utilisateur (nécessite une authentification par le Header).
- **id_texte** : Un identifiant unique pour votre document (minimum 3 caractères).
- **webhook_url** : L'URL de votre service qui sera appelée par le système une fois l'extraction terminée (recevra en POST le statut et l'URL de téléchargement).
- **ia_validate** : (`true` ou `false`) Active ou désactive la correction sémantique du texte par l'IA.
- **pdf_file** : Le fichier PDF à traiter (envoi en tant que fichier via `multipart/form-data`).
