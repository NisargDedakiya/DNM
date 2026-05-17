"""
Exposure intelligence model for attack surface analytics.
Tracks discovered exposures, vulnerabilities, and misconfigurations.
"""
from uuid import UUID
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, UUIDMixin, TimestampMixin


class ExposureType(str, Enum):
    """Types of exposures discovered on attack surface."""

    PUBLIC_ADMIN_PANEL = "public_admin_panel"  # Admin interface accessible
    EXPOSED_API = "exposed_api"  # Unprotected API endpoint
    OUTDATED_TECHNOLOGY = "outdated_technology"  # Vulnerable software version
    WEAK_HEADERS = "weak_headers"  # Missing security headers
    EXPOSED_STORAGE = "exposed_storage"  # Publicly accessible storage
    DEBUG_INTERFACE = "debug_interface"  # Debug mode enabled
    WEAK_AUTHENTICATION = "weak_authentication"  # Weak auth detected
    SERVICE_MISCONFIGURATION = "service_misconfiguration"  # Config issues
    INFORMATION_DISCLOSURE = "information_disclosure"  # Data leakage
    UNPATCHED_SERVICE = "unpatched_service"  # Unpatched service
    DATABASE_EXPOSURE = "database_exposure"  # Database publicly accessible
    CERTIFICATE_ISSUE = "certificate_issue"  # SSL/TLS problems


class RiskLevel(str, Enum):
    """Risk level classification for exposures."""

    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Should be addressed soon
    MEDIUM = "medium"  # Should be monitored
    LOW = "low"  # Can be addressed later
    INFO = "info"  # Informational only


class Exposure(Base, UUIDMixin, TimestampMixin):
    """
    Attack surface exposure record.
    Tracks discovered exposures, misconfigurations, and intelligence.
    """

    __tablename__ = "exposure"

    # Foreign keys
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("finding.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Exposure metadata
    exposure_type: Mapped[str] = mapped_column(
        SQLEnum(ExposureType),
        nullable=False,
        index=True,
    )
    risk_level: Mapped[str] = mapped_column(
        SQLEnum(RiskLevel),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Confidence and scoring
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.8,
        nullable=False,
    )  # 0.0-1.0
    risk_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )  # Weighted risk score
    criticality_factor: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )  # Asset criticality multiplier

    # Detection and timeline
    first_detected: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )
    last_detected: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )
    detection_count: Mapped[int] = mapped_column(Integer, default=1)

    # Intelligence data
    fingerprint_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
    )  # Technology fingerprint
    evidence: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
    )  # Detection evidence
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )  # Additional context (column name 'metadata' preserved in DB)

    # Status tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remediation_status: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )  # "not_started", "in_progress", "resolved", "wont_fix"
    remediation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    asset = relationship(
        "Asset",
        back_populates="exposures",
        foreign_keys=[asset_id],
    )
    organization = relationship(
        "Organization",
        foreign_keys=[organization_id],
    )
    finding = relationship(
        "Finding",
        foreign_keys=[finding_id],
    )

    __table_args__ = (
        Index("idx_exposure_org_asset", "organization_id", "asset_id"),
        Index("idx_exposure_org_risk", "organization_id", "risk_level"),
        Index("idx_exposure_org_type", "organization_id", "exposure_type"),
        Index("idx_exposure_active_detected", "is_active", "last_detected"),
        Index(
            "idx_exposure_risk_criticality",
            "risk_score",
            "criticality_factor",
        ),
    )


class ExposureHistory(Base, UUIDMixin, TimestampMixin):
    """
    Historical tracking of exposure changes.
    Maintains audit trail for exposure lifecycle.
    """

    __tablename__ = "exposure_history"

    # Foreign keys
    exposure_id: Mapped[UUID] = mapped_column(
        ForeignKey("exposure.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Change tracking
    change_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # "created", "updated", "remediated", "redetected"
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_exposure_hist_exposure", "exposure_id", "created_at"),
        Index("idx_exposure_hist_org", "organization_id", "created_at"),
        Index("idx_exposure_hist_asset", "asset_id", "created_at"),
    )


class AssetFingerprint(Base, UUIDMixin, TimestampMixin):
    """
    Aggregated technology fingerprint for asset.
    Caches most recent detection of technologies on asset.
    """

    __tablename__ = "asset_fingerprint"

    # Foreign keys
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Framework and technology detection
    detected_framework: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    framework_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    detected_server: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    server_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    detected_cms: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    cms_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Security headers presence (boolean flags)
    has_csp: Mapped[bool] = mapped_column(Boolean, default=False)
    has_hsts: Mapped[bool] = mapped_column(Boolean, default=False)
    has_x_frame_options: Mapped[bool] = mapped_column(Boolean, default=False)
    has_x_content_type_options: Mapped[bool] = mapped_column(Boolean, default=False)
    has_referrer_policy: Mapped[bool] = mapped_column(Boolean, default=False)

    # Technology stack
    technologies: Mapped[list] = mapped_column(
        JSON,
        nullable=True,
    )  # [{name, version, category, confidence}]
    detected_technologies_count: Mapped[int] = mapped_column(Integer, default=0)

    # HTTP response metadata
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
    )
    response_body_preview: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    # Detection confidence and quality
    fingerprint_confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )  # Overall fingerprint quality
    last_fingerprint_source: Mapped[str] = mapped_column(
        String(64),
        nullable=True,
    )  # "httpx", "nuclei", "katana"

    # Relationships
    asset = relationship(
        "Asset",
        back_populates="fingerprint",
        foreign_keys=[asset_id],
    )
    organization = relationship(
        "Organization",
        foreign_keys=[organization_id],
    )

    __table_args__ = (
        Index("idx_fingerprint_org", "organization_id", "created_at"),
        Index("idx_fingerprint_framework", "detected_framework", "framework_confidence"),
        Index("idx_fingerprint_server", "detected_server", "server_confidence"),
    )
