from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from datetime import datetime
import uuid
from backend.database.base import Base

class TelegramSession(Base):
    __tablename__ = "telegram_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, index=True, nullable=False)
    telegram_user_id = Column(String, index=True, nullable=False, unique=True)
    username = Column(String, nullable=True)
    
    linked_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
