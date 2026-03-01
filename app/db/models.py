from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.database import Base

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    is_configured = Column(Boolean, default=False)
    hf_token = Column(String, nullable=True)
    discord_webhook = Column(String, nullable=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user") # "creator", "admin", "user"
    is_validated = Column(Boolean, default=False)
    directory_name = Column(String, unique=True, nullable=True)
    api_token = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ExtractionRequest(Base):
    __tablename__ = "extraction_requests"

    id = Column(Integer, primary_key=True, index=True)
    id_texte = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending") # pending, processing, success, error
    webhook_url = Column(String, nullable=False)
    file_path = Column(String, nullable=True) # the original uploaded pdf location
    txt_file_path = Column(String, nullable=True) # the final output text
    ia_validate = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship to user
    from sqlalchemy.orm import relationship
    user = relationship("User", backref="extraction_requests")

class ActivityLog(Base):
    """
    Modèle de journal d'activité pour tracer les actions importantes.
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
