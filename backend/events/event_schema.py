from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class EventType(str, Enum):
    # Scan Domain
    SCAN_STARTED = "scan.started"
    SCAN_PROGRESS = "scan.progress"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"

    # Finding Domain
    FINDING_CREATED = "finding.created"
    FINDING_TRIAGED = "finding.triaged"
    FINDING_P1_ALERT = "finding.p1_alert"

    # Exposure Domain
    EXPOSURE_SNAPSHOT = "exposure.snapshot"
    EXPOSURE_DRIFT = "exposure.drift"
    EXPOSURE_RISK_EVO = "exposure.risk_evolution"
    EXPOSURE_REGRESSION = "exposure.regression"

    # Cluster/Worker Domain
    CLUSTER_JOB_QUEUED = "cluster.job_queued"
    CLUSTER_JOB_ASSIGNED = "cluster.job_assigned"
    CLUSTER_JOB_STARTED = "cluster.job_started"
    CLUSTER_JOB_COMPLETED = "cluster.job_completed"
    CLUSTER_JOB_FAILED = "cluster.job_failed"
    CLUSTER_WORKER_REGISTERED = "cluster.worker_registered"
    CLUSTER_WORKER_HEARTBEAT = "cluster.worker_heartbeat"

    # Collaboration Domain
    INVESTIGATION_CREATED = "collaboration.investigation_created"
    INVESTIGATION_COMMENT_ADDED = "collaboration.comment_added"
    INVESTIGATION_EVIDENCE_UPLOADED = "collaboration.evidence_uploaded"
    INVESTIGATION_ASSIGNED = "collaboration.assigned"
    INVESTIGATION_REASSIGNED = "collaboration.reassigned"
    INVESTIGATION_WORKFLOW_UPDATED = "collaboration.workflow_updated"
    INVESTIGATION_THREAD_OPENED = "collaboration.thread_opened"

    # Telemetry/Observability Domain
    TRACE_STARTED = "trace.started"
    TRACE_COMPLETED = "trace.completed"
    METRIC_RECORDED = "metric.recorded"
    MONITORING_HEALTH_UPDATED = "monitoring.health_updated"
    TELEMETRY_EVENT = "telemetry.event"
    
    # Approval Domain
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    
    # Report Domain
    REPORT_GENERATED = "report.generated"
    REPORT_SUBMITTED = "report.submitted"

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class EventMetadata(BaseModel):
    version: str = "v1"
    correlation_id: str
    parent_span_id: Optional[str] = None
    span_id: Optional[str] = None
    environment: str = "production"

class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    org_id: str
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: EventMetadata
    payload: Dict[str, Any]
