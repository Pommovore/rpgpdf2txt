from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.db.database import engine, Base
from app.db import models
import os
from loguru import logger
import sys

# Setup structured logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
os.makedirs(f"{settings.DATA_DIR}/logs", exist_ok=True)
logger.add(f"{settings.DATA_DIR}/logs/app.log", rotation="10 MB", retention="10 days", level="INFO")

def create_directories():
    """Create necessary directories if they don't exist"""
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

# Initialize DB tables
os.makedirs(f"{settings.DATA_DIR}/db", exist_ok=True)
Base.metadata.create_all(bind=engine)

from app.routes import auth_routes, view_routes, api_routes
from fastapi.staticfiles import StaticFiles

app = FastAPI(title=settings.PROJECT_NAME)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(view_routes.router)
app.include_router(auth_routes.router, prefix=settings.API_V1_STR + "/auth", tags=["auth"])
app.include_router(api_routes.router, prefix=settings.API_V1_STR, tags=["api"])



# Make sure basic output directories exist at startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up API...")
    create_directories()


# Root route removed, handled by views.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
