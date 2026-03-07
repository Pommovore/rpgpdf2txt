from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import SystemConfig, User
from app.core.security import get_password_hash
from app.services.webhook import send_discord_notification
from app.core.config import settings
import os

def _is_admin(request: Request) -> bool:
    token = request.cookies.get("access_token")
    if not token:
        return False
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("role") in ["admin", "creator"]
    except JWTError:
        return False

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Préfixe pour les templates (liens href, src, etc.)
_prefix = settings.APP_PREFIX

# Variables globales disponibles dans tous les templates
templates.env.globals["app_version"] = settings.APP_VERSION
templates.env.globals["github_url"] = settings.GITHUB_URL

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    config = db.query(SystemConfig).first()
    if not config or not config.is_configured:
        return templates.TemplateResponse("setup.html", {"request": request, "app_prefix": _prefix})
    return RedirectResponse(url=f"{_prefix}/login", status_code=302)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "app_prefix": _prefix})

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not _is_admin(request):
        return RedirectResponse(url=f"{_prefix}/login", status_code=302)
    return templates.TemplateResponse("admin.html", {"request": request, "app_prefix": _prefix})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return RedirectResponse(url=f"{_prefix}/extraction", status_code=302)

@router.get("/extraction", response_class=HTMLResponse)
async def extraction_page(request: Request):
    return templates.TemplateResponse("extraction.html", {"request": request, "app_prefix": _prefix})

@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request, "app_prefix": _prefix})

@router.get("/preferences", response_class=HTMLResponse)
async def preferences_page(request: Request):
    return templates.TemplateResponse("preferences.html", {"request": request, "app_prefix": _prefix})

@router.get("/cache", response_class=HTMLResponse)
async def cache_page(request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        return RedirectResponse(url=f"{_prefix}/login", status_code=302)
        
    from app.db.models import ExtractionRequest
    # Récupérer les extraits uniques par file_hash (status success)
    # L'utilisation de group_by pour éviter les doublons sur SQLite (comportement spécifique de SQLite)
    cached_requests = db.query(ExtractionRequest).filter(
        ExtractionRequest.status == "success",
        ExtractionRequest.file_hash.isnot(None),
        ExtractionRequest.txt_file_path.isnot(None)
    ).group_by(ExtractionRequest.file_hash).order_by(ExtractionRequest.completed_at.desc()).all()
    
    return templates.TemplateResponse("cache.html", {
        "request": request, 
        "app_prefix": _prefix, 
        "cached_requests": cached_requests,
        "settings_API_V1_STR": settings.API_V1_STR
    })

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "app_prefix": _prefix})

@router.post("/register")
async def register_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if len(password) < 8:
         return templates.TemplateResponse("register.html", {"request": request, "app_prefix": _prefix, "error": "Le mot de passe doit faire au moins 8 caractères."})

    if db.query(User).filter(User.email == email).first():
         return templates.TemplateResponse("register.html", {"request": request, "app_prefix": _prefix, "error": "Email already registered"})
         
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role="user",
        is_validated=False
    )
    db.add(user)
    db.commit()
    
    config = db.query(SystemConfig).first()
    if config and config.discord_webhook:
        msg = f"🔔 Nouveau compte en attente de validation: {email}\nLien: {request.base_url}admin/users"
        await send_discord_notification(config.discord_webhook, msg)
        
    return templates.TemplateResponse("login.html", {"request": request, "app_prefix": _prefix, "success": "Registration successful. Please wait for an admin to validate your account before logging in."})

@router.post("/setup")
async def setup_creator(
    request: Request,
    creator_email: str = Form(...),
    hf_token: str = Form(...),
    discord_webhook: str = Form(...),
    admin_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if len(admin_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    config = db.query(SystemConfig).first()
    if config and config.is_configured:
        raise HTTPException(status_code=400, detail="System already configured")
    
    if not config:
        config = SystemConfig()
        db.add(config)
        
    config.hf_token = hf_token
    config.discord_webhook = discord_webhook
    config.is_configured = True
    
    admin_user = db.query(User).filter(User.email == creator_email).first()
    if not admin_user:
        
        # Créer le nom de répertoire : moi@ici.fr -> moi_at_ici_fr
        dir_name = creator_email.replace('@', '_at_').replace('.', '_')
        import re
        dir_name = re.sub(r'[^a-zA-Z0-9_]', '', dir_name)
        
        import secrets
        api_token = secrets.token_urlsafe(32)
        
        admin_user = User(
            email=creator_email,
            hashed_password=get_password_hash(admin_password),
            role="creator",
            is_validated=True,
            directory_name=dir_name,
            api_token=api_token
        )
        db.add(admin_user)
        
    db.commit()
    
    import os
    user_dir_path = os.path.join(settings.USERS_DIR, admin_user.directory_name)
    os.makedirs(user_dir_path, exist_ok=True)
    
    await send_discord_notification(discord_webhook, f"✅ RPGPDF2Text is successfully configured and running! Creator email: {creator_email}")
    return RedirectResponse(url=f"{_prefix}/login", status_code=302)

