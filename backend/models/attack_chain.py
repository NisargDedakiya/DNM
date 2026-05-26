from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import uuid
from backend.database.base import Base

class AttackChain(Base):
    __tablename__ = "attack_chains"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, index=True, nullable=False)
    
    chain_name = Column(String, nullable=False)
    severity = Column(String, nullable=False) # e.g., CRITICAL, HIGH
    
    exploitability_score = Column(Float, default=0.0)
    blast_radius = Column(String, nullable=True) # e.g., "high_lateral_movement"
    
    summary = Column(String, nullable=True)
    
    # Array of finding IDs that make up the chain
    finding_ids = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
