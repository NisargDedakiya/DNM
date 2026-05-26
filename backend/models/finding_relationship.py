from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from datetime import datetime
import uuid
from backend.database.base import Base

class FindingRelationship(Base):
    __tablename__ = "finding_relationships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_a_id = Column(String, index=True, nullable=False)
    finding_b_id = Column(String, index=True, nullable=False)
    
    # Types: "escalates_to", "same_vulnerability", "auth_bypass_chain", "infrastructure_link"
    relationship_type = Column(String, nullable=False)
    
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
