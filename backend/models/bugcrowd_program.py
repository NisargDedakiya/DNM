"""
Bugcrowd Program Model
Stores normalized Bugcrowd engagement data for recon-ready ingestion
"""
from datetime import datetime
from uuid import UUID
import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from backend.database.base import Base
import enum


class BugcrowdProgramStatus(str, enum.Enum):
    """Program engagement status"""
    ACTIVE = "active"
    CLOSED = "closed"
    PENDING = "pending"
    ARCHIVED = "archived"


class BugcrowdAssetType(str, enum.Enum):
    """Asset type classifications"""
    WEBSITE = "website"
    API = "api"
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    CLOUD_SERVICE = "cloud_service"
    IOT_DEVICE = "iot_device"
    HARDWARE = "hardware"
    SOURCE_CODE = "source_code"
    OTHER = "other"


class BugcrowdProgram(Base):
    """
    Bugcrowd engagement data model
    Normalized storage for imported Bugcrowd programs
    """
    __tablename__ = "bugcrowd_programs"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Organization context
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    organization = relationship("Organization", back_populates="bugcrowd_programs")
    
    # Program identification
    engagement_url = Column(String(500), nullable=False, unique=True, index=True)
    program_name = Column(String(255), nullable=False, index=True)
    program_slug = Column(String(255), nullable=True)
    bugcrowd_program_id = Column(String(255), nullable=True, index=True)
    
    # Scope data
    scope_data = Column(JSON, nullable=False)  # Structured scope: {in_scope, out_of_scope, notes}
    
    # Metadata
    program_metadata = Column(JSON, nullable=True)  # {bounty_ranges, asset_types, auth_required, severity_ratings}
    
    # Program status
    status = Column(SQLEnum(BugcrowdProgramStatus), default=BugcrowdProgramStatus.ACTIVE, index=True)
    
    # Engagement metadata
    program_description = Column(Text, nullable=True)
    asset_categories = Column(JSON, nullable=True)  # List of asset type classifications
    
    # Sync tracking
    last_synced_at = Column(DateTime, nullable=True)
    last_modified_at = Column(DateTime, nullable=True)
    html_snapshot = Column(Text, nullable=True)  # Snapshot of HTML for re-parsing if needed
    
    # Extraction metadata
    extraction_version = Column(String(50), default="1.0")  # Version of extraction pipeline
    ai_extraction_used = Column(Boolean, default=False)
    extraction_confidence = Column(Integer, nullable=True)  # 0-100 confidence score
    
    # Relationships
    extracted_assets = relationship("BugcrowdAsset", back_populates="program", cascade="all, delete-orphan")
    sync_history = relationship("BugcrowdSyncHistory", back_populates="program", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BugcrowdAsset(Base):
    """
    Extracted scope asset from Bugcrowd program
    Normalized target representation
    """
    __tablename__ = "bugcrowd_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relationship to program
    program_id = Column(String(36), ForeignKey("bugcrowd_programs.id"), nullable=False, index=True)
    program = relationship("BugcrowdProgram", back_populates="extracted_assets")
    
    # Asset identification
    target = Column(String(500), nullable=False, index=True)  # domain, IP, URL, etc
    asset_type = Column(SQLEnum(BugcrowdAssetType), nullable=False, index=True)
    
    # Scope classification
    in_scope = Column(Boolean, default=True, index=True)
    priority_level = Column(String(50), nullable=True)  # critical, high, medium, low
    
    # Normalization data
    normalized_target = Column(String(500), nullable=True)
    wildcard_pattern = Column(Boolean, default=False)
    base_domain = Column(String(255), nullable=True, index=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    restrictions = Column(JSON, nullable=True)  # Rate limits, endpoints to avoid, etc
    asset_program_metadata = Column(JSON, nullable=True)  # Additional asset-specific data
    
    # Validation
    validation_status = Column(String(50), default="pending")  # pending, valid, invalid, needs_review
    validation_error = Column(Text, nullable=True)
    
    # Recon integration
    synced_to_asset_inventory = Column(Boolean, default=False)
    asset_inventory_id = Column(String(36), nullable=True, index=True)  # Link to Asset model
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BugcrowdSyncHistory(Base):
    """
    Track sync history for auditing and monitoring
    """
    __tablename__ = "bugcrowd_sync_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relationship
    program_id = Column(String(36), ForeignKey("bugcrowd_programs.id"), nullable=False, index=True)
    program = relationship("BugcrowdProgram", back_populates="sync_history")
    
    # Sync details
    sync_status = Column(String(50), nullable=False)  # success, failed, partial
    assets_imported = Column(Integer, default=0)
    assets_updated = Column(Integer, default=0)
    errors = Column(JSON, nullable=True)
    
    # Timestamps
    synced_at = Column(DateTime, default=datetime.utcnow, index=True)
    duration_seconds = Column(Integer, nullable=True)
