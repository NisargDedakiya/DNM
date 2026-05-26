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
from backend.models.exposure_event import ExposureEvent
from backend.models.hunt_memory import HuntMemory
from backend.models.risk_snapshot import RiskSnapshot
from backend.models.exposure_snapshot import ExposureSnapshot
from backend.models.drift_event import DriftEvent
from backend.models.risk_evolution_event import RiskEvolutionEvent
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
from backend.models.worker_node import WorkerNode
from backend.models.cluster_job import ClusterJob
from backend.models.investigation import Investigation
from backend.models.investigation_comment import InvestigationComment
from backend.models.evidence_item import EvidenceItem
from backend.models.task_assignment import TaskAssignment
from backend.models.sso_configuration import SSOConfiguration
from backend.models.private_workspace import PrivateWorkspace
from backend.models.federated_identity import FederatedIdentity
from backend.models.grid_agent import GridAgent
from backend.models.exposure_mutation import ExposureMutation
from backend.models.anomaly_event import AnomalyEvent
from backend.models.threat_intel import ThreatIntel
from backend.models.cve_mapping import CVEMapping
from backend.models.external_exposure import ExternalExposure
from backend.models.attack_path import AttackPath
from backend.models.blast_radius_event import BlastRadiusEvent
from backend.models.privilege_chain import PrivilegeChain
from backend.models.api_key import ApiKey
from backend.models.webhook_subscription import WebhookSubscription
from backend.models.developer_application import DeveloperApplication
from backend.models.hunt_strategy import HuntStrategy
from backend.models.recon_campaign import ReconCampaign
from backend.models.strategy_memory import StrategyMemory
from backend.models.plugin import Plugin
from backend.models.plugin_installation import PluginInstallation
from backend.models.integration_connector import IntegrationConnector
from backend.models.security_event import SecurityEvent
from backend.models.audit_log import AuditLog
from backend.models.recovery_snapshot import RecoverySnapshot

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
	"HuntMemory",
	"RiskSnapshot",
	"ExposureSnapshot",
	"DriftEvent",
	"RiskEvolutionEvent",
	"ExposureEvent",
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
	"WorkerNode",
	"ClusterJob",
	"Investigation",
	"InvestigationComment",
	"EvidenceItem",
	"TaskAssignment",
	"SSOConfiguration",
	"PrivateWorkspace",
	"FederatedIdentity",
	"GridAgent",
	"ExposureMutation",
	"AnomalyEvent",
	"ThreatIntel",
	"CVEMapping",
	"ExternalExposure",
	"AttackPath",
	"BlastRadiusEvent",
	"PrivilegeChain",
	"ApiKey",
	"WebhookSubscription",
	"DeveloperApplication",
	"HuntStrategy",
	"ReconCampaign",
	"StrategyMemory",
	"Plugin",
	"PluginInstallation",
	"IntegrationConnector",
	"SecurityEvent",
	"AuditLog",
	"RecoverySnapshot",
]

