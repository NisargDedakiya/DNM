from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from datetime import datetime
import uuid
from backend.database.base import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # "user", "assistant", "system"
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
