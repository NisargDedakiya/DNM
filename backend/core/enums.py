"""
Core application enums for consistency across services.
"""
from enum import Enum


class FindingSeverity(str, Enum):
    """Finding severity classification."""

    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FindingStatus(str, Enum):
    """Finding workflow states."""

    open = "open"
    triaged = "triaged"
    confirmed = "confirmed"
    fixed = "fixed"
    accepted = "accepted"
    duplicate = "duplicate"


class ScanStatus(str, Enum):
    """Scan execution states."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ScanType(str, Enum):
    """Scan categories."""

    recon = "recon"
    surface = "surface"
    deep = "deep"
    manual = "manual"
