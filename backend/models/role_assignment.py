from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
import uuid
from backend.database.base import Base

class RoleAssignment(Base):
    __tablename__ = "role_assignments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column(String, ForeignKey("workspace_members.id", ondelete="CASCADE"), index=True, nullable=False)
    
    role = Column(String, nullable=False) # e.g., owner, admin, hunter
    assigned_at = Column(DateTime, default=datetime.utcnow)
