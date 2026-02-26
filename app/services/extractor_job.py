import os
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from app.db.database import engine, SessionLocal
from app.db.models import ExtractionRequest, SystemConfig, User
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.hf_corrector import correct_text_with_hf
from app.services.webhook import send_client_webhook
from app.core.config import settings
from app.core.security import create_access_token
from datetime import timedelta

async def process_extraction(request_id: int):
    # This runs in background
    db: Session = SessionLocal()
    try:
        req = db.query(ExtractionRequest).filter(ExtractionRequest.id == request_id).first()
        if not req:
            return
            
        req.status = "processing"
        db.commit()
        
        # 1. Extract text
        raw_text = extract_text_from_pdf(req.file_path)
        
        # 2. Correct text
        config = db.query(SystemConfig).first()
        hf_token = config.hf_token if config else None
        
        corrected_text = raw_text
        is_truncated = False
        
        if req.ia_validate and hf_token and raw_text.strip():
            try:
                corrected_text, is_truncated = await correct_text_with_hf(raw_text, hf_token)
            except Exception as e:
                logger.error(f"HF Correction failed, using raw: {e}")
                
        # 3. Save text
        user = db.query(User).filter(User.id == req.user_id).first()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        txt_filename = f"{timestamp}_{req.id_texte}.txt"
        if is_truncated:
            txt_filename = f"{timestamp}_{req.id_texte}_IA_truncated.txt"
            
        txt_path = os.path.join(settings.USERS_DIR, user.directory_name, txt_filename)
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(corrected_text)
            
        req.txt_file_path = txt_path
        req.status = "success"
        req.completed_at = datetime.utcnow()
        db.commit()
        
        # 4. Webhook
        excerpt = corrected_text[:500]
        if len(corrected_text) > 500:
            excerpt += "..."
            
        # Create a single-use or long-lived download token specifically for this request
        download_token = create_access_token(
            data={"sub": str(req.id), "type": "download"}, 
            expires_delta=timedelta(days=365)
        )
        download_url = f"{settings.BASE_URL}{settings.API_V1_STR}/extract/{req.id}/download?token={download_token}"

        await send_client_webhook(req.webhook_url, {
            "message": "L'extraction est terminée.",
            "etat": "succès",
            "id_texte": req.id_texte,
            "url": download_url,
            "extrait": excerpt
        })
        
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {e}")
        req = db.query(ExtractionRequest).filter(ExtractionRequest.id == request_id).first()
        if req:
            req.status = "error"
            req.error_message = str(e)
            req.completed_at = datetime.utcnow()
            db.commit()
            await send_client_webhook(req.webhook_url, {
                "message": "L'extraction a échoué.",
                "etat": "échec",
                "id_texte": req.id_texte,
                "erreur": str(e)
            })
    finally:
        db.close()
        # Clean up temporary PDF file
        if req and req.file_path and os.path.exists(req.file_path):
            try:
                os.remove(req.file_path)
                logger.info(f"Cleaned up temporary file: {req.file_path}")
            except Exception as e:
                logger.error(f"Failed to clean up temporary file: {e}")
