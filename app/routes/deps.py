from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User

from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="token", auto_error=False)

def get_token(
    request: Request,
    token_url: str = Depends(oauth2_scheme),
    api_token: str = Depends(api_key_header)
) -> str | None:
    """Extraie le token depuis n'importe quelle source supportée (Header, Query, Cookie)."""
    # 1. Tenter depuis le paramètre de requête ou header spécifique Custom (API key/Token d'URL)
    if api_token:
        # Dans get_current_user on s'en servira spécifiquement géré.
        # Mais get_token va récupérer l'accès général.
        pass

    # 1. Header classique Authorization: Bearer
    if token_url:
        return token_url
        
    # 2. Query string (ex: pour download)
    query_token = request.query_params.get("token")
    if query_token:
        return query_token
        
    # 3. Cookie (pour les vues HTML)
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
        
    return None

def get_user_from_token(token: str, db: Session) -> User | None:
    payload = decode_access_token(token)
    if not payload:
        return None
    email: str = payload.get("sub")
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()

def get_current_user(
    db: Session = Depends(get_db),
    token: str | None = Depends(get_token),
    api_token: str = Depends(api_key_header)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check custom API token first if provided
    if api_token:
        # On vérifie si ce token correspond directement au token d'API d'un compte systeme (ex: creator)
        user = db.query(User).filter(User.api_token == api_token).first()
        if user:
            return user

    if not token:
        raise credentials_exception

    user = get_user_from_token(token, db)
    if user is None:
        raise credentials_exception
        
    return user

def get_current_user_optional(
    db: Session = Depends(get_db),
    token: str | None = Depends(get_token)
) -> User | None:
    """Retourne l'utilisateur courant s'il est loggé, sinon None. Ne lève pas d'exception 401."""
    if not token:
        return None
    return get_user_from_token(token, db)

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_validated:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["admin", "creator"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user
