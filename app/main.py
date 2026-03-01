from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.db.database import engine, Base
from app.db import models
import os
from loguru import logger
import sys

# Configuration du logging structuré
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
os.makedirs(f"{settings.DATA_DIR}/logs", exist_ok=True)
logger.add(f"{settings.DATA_DIR}/logs/app.log", rotation="10 MB", retention="10 days", level="INFO")

def create_directories():
    """Crée les répertoires nécessaires s'ils n'existent pas."""
    dirs = [
        settings.DATA_DIR,
        settings.USERS_DIR,
        settings.TEMP_DIR,
        f"{settings.DATA_DIR}/logs",
        f"{settings.DATA_DIR}/db"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        logger.info(f"Ensured directory exists: {d}")

# Initialisation des tables de la base de données
os.makedirs(f"{settings.DATA_DIR}/db", exist_ok=True)
Base.metadata.create_all(bind=engine)

from app.routes import auth_routes, view_routes, api_routes

# Préfixe de l'application (ex: "/rpgpdf2txt" en prod, "" en local)
_prefix = settings.APP_PREFIX

app = FastAPI(title=settings.PROJECT_NAME)

# Fichiers statiques et routes montés sous le préfixe
# En local (_prefix=""), les routes sont à la racine (/login, /api/v1/...)
# En prod (_prefix="/rpgpdf2txt"), les routes sont sous le préfixe (/rpgpdf2txt/login, ...)
app.mount(f"{_prefix}/static", StaticFiles(directory="app/static"), name="static")

app.include_router(view_routes.router, prefix=_prefix)
app.include_router(auth_routes.router, prefix=_prefix + settings.API_V1_STR + "/auth", tags=["auth"])
app.include_router(api_routes.router, prefix=_prefix + settings.API_V1_STR, tags=["api"])

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback

@app.middleware("http")
async def log_request_details(request: Request, call_next):
    """Middleware de diagnostic : logue les en-têtes des requêtes POST."""
    if request.method == "POST" and "/extract" in request.url.path:
        logger.info(f"📥 POST {request.url.path}")
        logger.info(f"   Content-Type: {request.headers.get('content-type', 'MANQUANT')}")
        logger.info(f"   Content-Length: {request.headers.get('content-length', 'MANQUANT')}")
        logger.info(f"   Transfer-Encoding: {request.headers.get('transfer-encoding', 'N/A')}")
    response = await call_next(request)
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Logue les erreurs de validation (422/400) avec tous les détails."""
    logger.error(f"Erreur de validation sur {request.method} {request.url.path}")
    logger.error(f"Détails: {exc.errors()}")
    from fastapi.responses import JSONResponse
    from fastapi.encoders import jsonable_encoder
    return JSONResponse(
        status_code=400,
        content={"detail": jsonable_encoder(exc.errors())},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Logue les exceptions HTTP (404, 401, etc.) avec la cause originale."""
    logger.warning(f"Exception HTTP {exc.status_code} sur {request.url.path} : {exc.detail}")
    # Tracer l'exception sous-jacente (ex: MultipartDecodeError)
    if exc.__cause__:
        logger.error(f"   Cause sous-jacente: {type(exc.__cause__).__name__}: {exc.__cause__}")
        logger.error(f"   Traceback:\n{''.join(traceback.format_exception(type(exc.__cause__), exc.__cause__, exc.__cause__.__traceback__))}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Vérification des répertoires de sortie au démarrage
@app.on_event("startup")
async def startup_event():
    prefix_info = f" avec préfixe '{settings.APP_PREFIX}'" if settings.APP_PREFIX else " (sans préfixe)"
    logger.info(f"Démarrage de l'API{prefix_info}...")
    create_directories()


# Route principale gérée par view_routes.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

