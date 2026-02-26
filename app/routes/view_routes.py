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

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    config = db.query(SystemConfig).first()
    if not config or not config.is_configured:
        return templates.TemplateResponse("setup.html", {"request": request})
    return RedirectResponse(url="/login", status_code=302)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == email).first():
         # In a real app we'd redirect with an error message in URL/flash
         return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})
         
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
        
    return templates.TemplateResponse("login.html", {"request": request, "success": "Registration successful. Please wait for an admin to validate your account before logging in."})

@router.post("/setup")
async def setup_creator(
    request: Request,
    creator_email: str = Form(...),
    hf_token: str = Form(...),
    discord_webhook: str = Form(...),
    admin_password: str = Form(...),
    db: Session = Depends(get_db)
):
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
        
        # Create directory name: moi@ici.fr -> moi_at_ici_fr
        dir_name = creator_email.replace('@', '_at_').replace('.', '_')
        import re
        dir_name = re.sub(r'[^a-zA-Z0-9_]', '', dir_name)
        
        admin_user = User(
            email=creator_email,
            hashed_password=get_password_hash(admin_password),
            role="creator",
            is_validated=True,
            directory_name=dir_name
        )
        db.add(admin_user)
        
    db.commit()
    
    import os
    user_dir_path = os.path.join(settings.USERS_DIR, admin_user.directory_name)
    os.makedirs(user_dir_path, exist_ok=True)
    
    await send_discord_notification(discord_webhook, f"✅ RPGPDF2Text is successfully configured and running! Creator email: {creator_email}")
    return RedirectResponse(url="/login", status_code=302)
