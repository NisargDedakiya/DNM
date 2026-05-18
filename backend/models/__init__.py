"""
Database models for ORM mapping.
SQLAlchemy model definitions using async-compatible patterns.
"""

from backend.database.base import Base, BaseModel, TimestampMixin, UUIDMixin
from backend.models.finding import Finding, FindingStatus, SeverityLevel
from backend.models.program import Program
from backend.models.report import Report
from backend.models.scan import Scan, ScanStatus, ScanType
from backend.models.user import User
from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.technology import Technology
from backend.models.organization import Organization
from backend.models.team_member import TeamMember, MemberRole
from backend.models.monitoring_rule import MonitoringRule, MonitoringFrequency
from backend.models.alert import Alert, AlertType, AlertSeverity
from backend.models.exposure import (
	Exposure,
	ExposureHistory,
	AssetFingerprint,
	ExposureType,
	RiskLevel,
)
from backend.models.recon_snapshot import ReconSnapshot, SnapshotType
from backend.models.change_event import ChangeEvent, ChangeType, ChangeSeverity
from backend.models.graph_node import GraphNode, NodeType
from backend.models.graph_edge import GraphEdge, RelationshipType
from backend.models.executive_report import ExecutiveReport, ExecutiveReportType
from backend.models.platform_program import PlatformProgram, PlatformName
from backend.models.hackerone_program import HackerOneProgram
from backend.models.hackerone_report import HackerOneReport
from backend.models.bugcrowd_program import (
	BugcrowdProgram,
	BugcrowdAsset,
	BugcrowdSyncHistory,
	BugcrowdProgramStatus,
	BugcrowdAssetType,
)
from backend.models.triage_result import TriageResult
from backend.models.report_draft import ReportDraft
from backend.models.notification import (
	Notification,
	NotificationType,
	NotificationChannel,
	NotificationSeverity,
	NotificationStatus,
)

__all__ = [
	"Base",
	"BaseModel",
	"TimestampMixin",
	"UUIDMixin",
	"User",
	"Asset",
	"Endpoint",
	"Technology",
	"Program",
	"Scan",
	"ScanType",
	"ScanStatus",
	"Finding",
	"SeverityLevel",
	"FindingStatus",
	"Report",
	"Organization",
	"TeamMember",
	"MemberRole",
	"MonitoringRule",
	"MonitoringFrequency",
	"Alert",
	"AlertType",
	"AlertSeverity",
	"Exposure",
	"ExposureHistory",
	"AssetFingerprint",
	"ExposureType",
	"RiskLevel",
	"ReconSnapshot",
	"SnapshotType",
	"ChangeEvent",
	"ChangeType",
	"ChangeSeverity",
	"GraphNode",
	"NodeType",
	"GraphEdge",
	"RelationshipType",
	"ExecutiveReport",
	"ExecutiveReportType",
	"PlatformProgram",
	"PlatformName",
	"HackerOneProgram",
	"HackerOneReport",
	"BugcrowdProgram",
	"BugcrowdAsset",
	"BugcrowdSyncHistory",
	"BugcrowdProgramStatus",
	"BugcrowdAssetType",
	"TriageResult",
	"ReportDraft",
	"Notification",
	"NotificationType",
	"NotificationChannel",
	"NotificationSeverity",
	"NotificationStatus",
]
