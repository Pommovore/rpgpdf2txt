import os
from datetime import datetime, timezone
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
import hashlib
import asyncio

# Sémaphore global initialisé paresseusement
_extraction_lock = None

def get_extraction_lock():
    global _extraction_lock
    if _extraction_lock is None:
        _extraction_lock = asyncio.Semaphore(settings.MAX_CONCURRENT_EXTRACTIONS)
    return _extraction_lock

async def process_extraction(request_id: int):
    # This runs in background
    db: Session = SessionLocal()
    try:
        req = db.query(ExtractionRequest).filter(ExtractionRequest.id == request_id).first()
        if not req:
            logger.warning(f"Demande d'extraction {request_id} non trouvée en base.")
            return
            
        logger.info(f"Début du traitement de la demande {request_id} (ID Texte: {req.id_texte})")
        req.status = "processing"
        
        # 0. Calcul du hash et vérification du cache
        logger.info(f"Étape 0/4 : Calcul de l'empreinte du fichier '{req.file_path}'")
        sha256_hash = hashlib.sha256()
        with open(req.file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()
        req.file_hash = file_hash
        
        cached_req = db.query(ExtractionRequest).filter(
            ExtractionRequest.file_hash == file_hash,
            ExtractionRequest.status.in_(["success", "success_cached"]),
            ExtractionRequest.txt_file_path.isnot(None),
            ExtractionRequest.id != request_id
        ).first()

        if cached_req and os.path.exists(cached_req.txt_file_path):
            logger.info(f"Cache hit! Réutilisation de l'extraction de la demande {cached_req.id} (Hash: {file_hash})")
            req.txt_file_path = cached_req.txt_file_path
            req.status = "success_cached"
            req.completed_at = datetime.now(timezone.utc)
            db.commit()
            
            with open(req.txt_file_path, "r", encoding="utf-8") as f:
                corrected_text = f.read()
            
            # Aller directement à l'étape 4 (Webhook)
            logger.info(f"Étape 4/4 : Envoi de la notification au webhook : {req.webhook_url}")
            excerpt = corrected_text[:500]
            if len(corrected_text) > 500:
                excerpt += "..."
                
            download_token = create_access_token(
                data={"sub": str(req.id), "type": "download"}, 
                expires_delta=timedelta(days=365)
            )
            download_url = f"{settings.EXTERNAL_URL}{settings.API_V1_STR}/extract/{req.id}/download?token={download_token}"

            await send_client_webhook(req.webhook_url, {
                "message": "L'extraction est terminée (depuis le cache).",
                "etat": "succès",
                "id_texte": req.id_texte,
                "url": download_url,
                "extrait": excerpt
            })
            return
        else:
            logger.info("Miss du cache, attente de disponibilité dans la file (1 extraction à la fois)...")
            db.commit()
            
            # Prise du verrou global pour l'extraction afin de ne pas surcharger le serveur
            lock = get_extraction_lock()
            async with lock:
                # Vérification si la tâche a été annulée par un admin pendant l'attente
                db.refresh(req)
                if req.status == "error":
                    logger.info("Extraction annulée pendant l'attente (vide-file admin). Abandon.")
                    return
                    
                # 1. Extraction du texte dans un thread séparé pour ne pas bloquer l'Event Loop (Tesseract très lourd)
                logger.info(f"Étape 1/4 : Extraction du texte depuis le PDF '{req.file_path}' (Verrou Acquis)")
                raw_text = await asyncio.to_thread(extract_text_from_pdf, req.file_path)
                logger.info(f"Extraction terminée. Longueur brute : {len(raw_text)} caractères.")
                
                # 2. Correction IA (si demandée)
                config = db.query(SystemConfig).first()
                hf_token = config.hf_token if config else None
                
                corrected_text = raw_text
                is_truncated = False
                
                if req.ia_validate:
                    if hf_token and raw_text.strip():
                        logger.info("Étape 2/4 : Correction IA demandée. Envoi à HuggingFace...")
                        try:
                            corrected_text, is_truncated = await correct_text_with_hf(raw_text, hf_token)
                            logger.info(f"Correction IA terminée. Longueur finale : {len(corrected_text)} caractères.")
                        except Exception as e:
                            logger.error(f"Échec de la correction IA, utilisation du texte brut : {e}")
                    else:
                        logger.warning("Correction IA demandée mais impossible (Token HF manquant ou texte vide).")
                        
                # Vérification ultime avant sauvegarde des fichiers : si la tâche a été annulée pendant le traitement IA/OCR
                db.refresh(req)
                if req.status == "error":
                    logger.info("Extraction annulée pendant le traitement (vide-file admin). Abandon de la sauvegarde.")
                    return
                    
                # 3. Sauvegarde du résultat
                logger.info("Étape 3/4 : Sauvegarde du fichier texte résultat...")
                user = db.query(User).filter(User.id == req.user_id).first()
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                
                txt_filename = f"{timestamp}_{req.id_texte}.txt"
                if is_truncated:
                    logger.warning("Le texte a été tronqué pour l'IA.")
                    txt_filename = f"{timestamp}_{req.id_texte}_IA_truncated.txt"
                    
                txt_path = os.path.join(settings.USERS_DIR, user.directory_name, txt_filename)
                
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(corrected_text)
                    
                req.txt_file_path = txt_path
                req.status = "success"
                req.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Fichier sauvegardé avec succès dans: {txt_path}")
                
                # 4. Envoi du Webhook
                logger.info(f"Étape 4/4 : Envoi de la notification au webhook : {req.webhook_url}")
                excerpt = corrected_text[:500]
                if len(corrected_text) > 500:
                    excerpt += "..."
                    
                # Create a single-use or long-lived download token specifically for this request
                download_token = create_access_token(
                    data={"sub": str(req.id), "type": "download"}, 
                    expires_delta=timedelta(days=365)
                )
                download_url = f"{settings.EXTERNAL_URL}{settings.API_V1_STR}/extract/{req.id}/download?token={download_token}"

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
            req.completed_at = datetime.now(timezone.utc)
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
