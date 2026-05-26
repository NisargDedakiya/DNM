from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
import uuid
from backend.database.base import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=True, default="New Investigation")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
