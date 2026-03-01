from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, Query, Request
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.db.models import User, ActivityLog, ExtractionRequest
from app.routes.deps import get_current_admin_user, get_current_active_user
from app.core.config import settings
from app.services.extractor_job import process_extraction
from jose import jwt, JWTError
import os
import re
import shutil
import uuid
from loguru import logger

router = APIRouter()

@router.get("/admin/users")
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    users = db.query(User).all()
    return [{"id": u.id, "email": u.email, "role": u.role, "is_validated": u.is_validated, "directory_name": u.directory_name} for u in users]

@router.post("/admin/users/{user_id}/validate")
def validate_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_validated:
        return {"msg": "User already validated"}
        
    user.is_validated = True
    
    # Generate unique API token
    import secrets
    user.api_token = secrets.token_urlsafe(32)
    
    # Create directory name: moi@ici.fr -> moi_at_ici_fr
    dir_name = user.email.replace('@', '_at_').replace('.', '_')
    
    # Ensure it's safe for filesystem just in case
    dir_name = re.sub(r'[^a-zA-Z0-9_]', '', dir_name)
    user.directory_name = dir_name
    
    db.commit()
    
    # Create physical directory
    user_dir_path = os.path.join(settings.USERS_DIR, dir_name)
    os.makedirs(user_dir_path, exist_ok=True)
    
    # Log the action
    log = ActivityLog(user_id=current_user.id, action=f"L'admin a validé l'utilisateur {user.email}")
    db.add(log)
    db.commit()
    
    return {"msg": "User validated and directory created", "directory": dir_name}

from fastapi import BackgroundTasks, UploadFile, File, Form
from app.services.extractor_job import process_extraction
import shutil
import uuid

@router.post("/extract", status_code=202)
def extract_document(
    background_tasks: BackgroundTasks,
    id_texte: str = Form(..., min_length=3),
    webhook_url: str = Form(...),
    ia_validate: bool = Form(False),
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Démarre une nouvelle demande d'extraction de texte.
    """
    logger.info(f"Requête d'extraction reçue | Utilisateur: {current_user.email} | ID Texte: {id_texte}")
    
    if not pdf_file.filename.lower().endswith('.pdf'):
        logger.warning(f"Fichier rejeté (non-PDF): {pdf_file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    # Sauvegarde temporaire du fichier
    temp_filename = f"{uuid.uuid4()}_{pdf_file.filename}"
    file_path = os.path.abspath(os.path.join(settings.TEMP_DIR, temp_filename))
    
    logger.debug(f"Sauvegarde du PDF temporaire dans: {file_path}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(pdf_file.file, buffer)
        
    # Find existing job or create new one
    req = db.query(ExtractionRequest).filter(ExtractionRequest.id_texte == id_texte).first()
    
    if req:
        # Overwrite existing request
        req.user_id = current_user.id
        req.status = "pending"
        req.webhook_url = webhook_url
        req.file_path = file_path
        req.ia_validate = ia_validate
        req.error_message = None
        req.completed_at = None
        action_msg = f"Demande d'extraction relancée/écrasée pour '{id_texte}'"
    else:
        # Create new request
        req = ExtractionRequest(
            id_texte=id_texte,
            user_id=current_user.id,
            status="pending",
            webhook_url=webhook_url,
            file_path=file_path,
            ia_validate=ia_validate
        )
        db.add(req)
        action_msg = f"Nouvelle demande d'extraction initiée pour '{id_texte}'"
    
    log = ActivityLog(user_id=current_user.id, action=action_msg)
    db.add(log)
    
    db.commit()
    db.refresh(req)
    
    # Lancement du traitement en arrière-plan
    logger.info(f"Demande {req.id} ({id_texte}) ajoutée à la file d'attente.")
    background_tasks.add_task(process_extraction, req.id)
    
    return {"msg": "Extraction started", "request_id": req.id}

from fastapi.responses import FileResponse
# Les imports FastAPI et jose ont été déplacés en haut du fichier

@router.get("/extract/{request_id}/download")
def download_text(
    request_id: int, 
    request: Request,
    token: str = Query(None),
    db: Session = Depends(get_db)
):
    actual_token = token
    if not actual_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            actual_token = auth_header.split(" ")[1]
            
    if not actual_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        payload = jwt.decode(actual_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if payload.get("type") == "download":
            if str(payload.get("sub")) != str(request_id):
                raise HTTPException(status_code=403, detail="Invalid token for this download")
            req = db.query(ExtractionRequest).filter(ExtractionRequest.id == request_id).first()
        else:
            email = payload.get("sub")
            if not email:
                raise HTTPException(status_code=401, detail="Invalid token")
            user = db.query(User).filter(User.email == email, User.is_validated == True).first()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid user")
            req = db.query(ExtractionRequest).filter(ExtractionRequest.id == request_id, ExtractionRequest.user_id == user.id).first()
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token signature")

    if not req or req.status != "success" or not req.txt_file_path:
        raise HTTPException(status_code=404, detail="File not found or not ready")
        
    return FileResponse(path=req.txt_file_path, filename=os.path.basename(req.txt_file_path), media_type="text/plain")

@router.get("/user/requests")
def get_user_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    Récupère la liste des demandes de l'utilisateur.
    """
    logger.debug(f"Récupération de l'historique pour {current_user.email}")
    requests = db.query(ExtractionRequest).options(joinedload(ExtractionRequest.user)).filter(ExtractionRequest.user_id == current_user.id).order_by(ExtractionRequest.created_at.desc()).all()
    result = []
    for r in requests:
        result.append({
            "id": r.id,
            "id_texte": r.id_texte,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "error_message": r.error_message
        })
    return result
