"""
Verification Wizard Module
Guided verification workflows for manual finding validation.
Tracks evidence collection, validates completeness, and guides hunters.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class VerificationStatus(str, Enum):
    """Verification workflow status"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    EVIDENCE_COLLECTED = "evidence_collected"
    VALIDATION_COMPLETE = "validation_complete"
    REJECTED = "rejected"
    COMPLETED = "completed"


class EvidenceType(str, Enum):
    """Types of evidence that can be collected"""
    SCREENSHOT = "screenshot"
    HTTP_REQUEST = "http_request"
    HTTP_RESPONSE = "http_response"
    SOURCE_CODE = "source_code"
    LOG_OUTPUT = "log_output"
    CONSOLE_OUTPUT = "console_output"
    REPRODUCTION_STEPS = "reproduction_steps"
    ANALYSIS_NOTES = "analysis_notes"
    CURL_COMMAND = "curl_command"
    API_RESPONSE = "api_response"


@dataclass
class EvidenceItem:
    """Single piece of evidence"""
    type: EvidenceType
    description: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    quality_score: float = 0.0  # 0.0-1.0
    validation_notes: str = ""


@dataclass
class VerificationCheckpoint:
    """Single verification checkpoint/step"""
    checkpoint_id: int
    title: str
    description: str
    required: bool
    required_evidence_types: List[EvidenceType]
    expected_findings: List[str]
    completed: bool = False
    evidence_collected: List[EvidenceItem] = field(default_factory=list)
    notes: str = ""
    quality_assessment: str = ""


@dataclass
class VerificationWorkflow:
    """Complete verification workflow for a finding"""
    finding_id: str
    vulnerability_type: str
    severity: str
    workflow_id: str
    status: VerificationStatus
    created_at: datetime
    updated_at: datetime
    checkpoints: List[VerificationCheckpoint]
    overall_evidence_quality: float
    completeness_score: float
    validation_summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class VerificationWizard:
    """
    Guided verification workflow for manual finding validation.
    Tracks evidence collection and validates completeness.
    """

    def __init__(self):
        """Initialize wizard templates"""
        self.checkpoint_templates = self._initialize_checkpoints()

    def _initialize_checkpoints(self) -> Dict[str, List[Dict]]:
        """Initialize verification checkpoint templates for each vulnerability type"""
        return {
            "xss": [
                {
                    "id": 1,
                    "title": "Input Vector Identified",
                    "description": "Locate and document the exact input point (parameter, field, endpoint)",
                    "required": True,
                    "evidence_types": ["screenshot", "http_request"],
                    "expected_findings": [
                        "Parameter name clearly identified",
                        "Input type documented (form field, URL param, file upload, API endpoint)",
                        "Request method documented (GET, POST, etc)"
                    ]
                },
                {
                    "id": 2,
                    "title": "Payload Reflected",
                    "description": "Verify payload appears in HTTP response without encoding",
                    "required": True,
                    "evidence_types": ["http_response", "screenshot"],
                    "expected_findings": [
                        "Payload visible in HTML response",
                        "No encoding of angle brackets or quotes",
                        "Response shows JavaScript context"
                    ]
                },
                {
                    "id": 3,
                    "title": "Browser Execution Confirmed",
                    "description": "Verify JavaScript executes in browser context",
                    "required": True,
                    "evidence_types": ["screenshot", "console_output"],
                    "expected_findings": [
                        "Browser console output from payload",
                        "No CSP errors preventing execution",
                        "JavaScript context accessible"
                    ]
                },
                {
                    "id": 4,
                    "title": "XSS Type Determined",
                    "description": "Classify as Reflected, Stored, or DOM-based",
                    "required": True,
                    "evidence_types": ["analysis_notes"],
                    "expected_findings": [
                        "XSS type clearly identified",
                        "Proof of type (reflection, persistence, or DOM code)",
                        "Attack surface analysis"
                    ]
                },
                {
                    "id": 5,
                    "title": "Impact Assessed",
                    "description": "Document what data/actions are at risk",
                    "required": True,
                    "evidence_types": ["analysis_notes", "screenshot"],
                    "expected_findings": [
                        "Accessible data documented (cookies, localStorage, form data)",
                        "Possible attacker actions listed",
                        "Business impact quantified"
                    ]
                }
            ],
            "idor": [
                {
                    "id": 1,
                    "title": "Resource Identified",
                    "description": "Document the resource being accessed and its ID format",
                    "required": True,
                    "evidence_types": ["screenshot", "http_request"],
                    "expected_findings": [
                        "Resource type identified (user, document, order, etc)",
                        "ID format documented (numeric, UUID, string)",
                        "ID location noted (URL, parameter, header)"
                    ]
                },
                {
                    "id": 2,
                    "title": "Own Resource Accessed",
                    "description": "Successfully access own resource to establish baseline",
                    "required": True,
                    "evidence_types": ["http_request", "http_response"],
                    "expected_findings": [
                        "Own resource ID captured",
                        "Successful HTTP 200 response",
                        "Expected resource data returned"
                    ]
                },
                {
                    "id": 3,
                    "title": "Other User Resource Accessed",
                    "description": "Access another user's resource with modified ID",
                    "required": True,
                    "evidence_types": ["http_request", "http_response"],
                    "expected_findings": [
                        "Different user's resource ID attempted",
                        "HTTP 200 response (not 403/401)",
                        "Other user's data visible in response"
                    ]
                },
                {
                    "id": 4,
                    "title": "Authorization Check Missing",
                    "description": "Verify that authorization is not properly checking ownership",
                    "required": True,
                    "evidence_types": ["analysis_notes", "screenshot"],
                    "expected_findings": [
                        "Specific authorization check identified as missing",
                        "Comparison of allowed vs actual access",
                        "Permission model documented"
                    ]
                },
                {
                    "id": 5,
                    "title": "Data Sensitivity Assessed",
                    "description": "Evaluate sensitivity of accessible data",
                    "required": True,
                    "evidence_types": ["analysis_notes"],
                    "expected_findings": [
                        "Data fields accessible through IDOR listed",
                        "Sensitivity level per field identified",
                        "Scope of exposure documented (1 user, all users, etc)"
                    ]
                }
            ],
            "ssrf": [
                {
                    "id": 1,
                    "title": "Request Vector Identified",
                    "description": "Find where application accepts URLs or makes HTTP requests",
                    "required": True,
                    "evidence_types": ["screenshot", "http_request"],
                    "expected_findings": [
                        "URL parameter or API endpoint identified",
                        "Request method documented",
                        "Feature purpose (proxy, fetch, webhook, etc) documented"
                    ]
                },
                {
                    "id": 2,
                    "title": "Server Makes External Request",
                    "description": "Verify server actually makes requests to attacker-controlled URL",
                    "required": True,
                    "evidence_types": ["http_request", "log_output"],
                    "expected_findings": [
                        "Request sent to attacker-controlled test domain",
                        "Server connection logged",
                        "Response time indicates server contacted URL"
                    ]
                },
                {
                    "id": 3,
                    "title": "Internal System Access Tested",
                    "description": "Verify if internal systems are accessible (in safe test environment)",
                    "required": False,
                    "evidence_types": ["analysis_notes", "http_request"],
                    "expected_findings": [
                        "Localhost/127.0.0.1 request results documented",
                        "Internal IP range accessibility (10.x.x.x, 172.16.x.x, 192.168.x.x)",
                        "Response time/error patterns analyzed"
                    ]
                },
                {
                    "id": 4,
                    "title": "Internal Services Mapped",
                    "description": "Document what internal services could be accessed",
                    "required": True,
                    "evidence_types": ["analysis_notes"],
                    "expected_findings": [
                        "Accessible internal services identified",
                        "Potential for credential theft assessed",
                        "Lateral movement risk documented"
                    ]
                },
                {
                    "id": 5,
                    "title": "Impact Quantified",
                    "description": "Assess business impact of internal access",
                    "required": True,
                    "evidence_types": ["analysis_notes"],
                    "expected_findings": [
                        "Credential exposure risk documented",
                        "Internal system compromise scenarios described",
                        "Data sensitivity of accessible systems assessed"
                    ]
                }
            ],
            "auth_bypass": [
                {
                    "id": 1,
                    "title": "Authentication Mechanism Documented",
                    "description": "Understand how application authenticates users",
                    "required": True,
                    "evidence_types": ["screenshot", "analysis_notes"],
                    "expected_findings": [
                        "Authentication method identified (form, API, OAuth, etc)",
                        "Session/token mechanism documented",
                        "Protected endpoints identified"
                    ]
                },
                {
                    "id": 2,
                    "title": "Authentication Bypass Attempted",
                    "description": "Test if protected functionality is accessible without auth",
                    "required": True,
                    "evidence_types": ["http_request", "http_response"],
                    "expected_findings": [
                        "Request without authentication headers/tokens",
                        "Protected functionality accessible (HTTP 200, not 401/403)",
                        "Sensitive data or actions available without auth"
                    ]
                },
                {
                    "id": 3,
                    "title": "Account Compromise Verified",
                    "description": "Verify if other accounts can be accessed/compromised",
                    "required": True,
                    "evidence_types": ["http_request", "http_response"],
                    "expected_findings": [
                        "Other user account accessed from different account",
                        "Authorization check bypassed",
                        "Cross-account data access documented"
                    ]
                },
                {
                    "id": 4,
                    "title": "Bypass Technique Documented",
                    "description": "Clearly explain the bypass method",
                    "required": True,
                    "evidence_types": ["analysis_notes", "screenshot"],
                    "expected_findings": [
                        "Exact bypass technique explained",
                        "Step-by-step reproduction documented",
                        "Root cause identified (missing check, weak validation, etc)"
                    ]
                },
                {
                    "id": 5,
                    "title": "Scope Assessed",
                    "description": "Evaluate how many users/systems are affected",
                    "required": True,
                    "evidence_types": ["analysis_notes"],
                    "expected_findings": [
                        "Number of affected accounts quantified",
                        "All affected functionality documented",
                        "Admin access compromise considered"
                    ]
                }
            ],
            "api": [
                {
                    "id": 1,
                    "title": "API Endpoints Mapped",
                    "description": "Document all relevant API endpoints and their functionality",
                    "required": True,
                    "evidence_types": ["http_request", "analysis_notes"],
                    "expected_findings": [
                        "Endpoint URL and HTTP method documented",
                        "Required parameters identified",
                        "Request/response format documented"
                    ]
                },
                {
                    "id": 2,
                    "title": "Authentication Tested",
                    "description": "Verify API respects authentication requirements",
                    "required": True,
                    "evidence_types": ["http_request", "http_response"],
                    "expected_findings": [
                        "Endpoint accessible without authentication",
                        "HTTP 200 response instead of 401/403",
                        "Sensitive data returned without proper auth"
                    ]
                },
                {
                    "id": 3,
                    "title": "Authorization Verified",
                    "description": "Check if API enforces authorization/permissions",
                    "required": True,
                    "evidence_types": ["http_request", "http_response"],
                    "expected_findings": [
                        "Other user's data accessible",
                        "Admin endpoints accessible from regular account",
                        "Permission bypass documented"
                    ]
                },
                {
                    "id": 4,
                    "title": "Data Exposure Assessed",
                    "description": "Document what sensitive data is exposed in API responses",
                    "required": True,
                    "evidence_types": ["api_response", "analysis_notes"],
                    "expected_findings": [
                        "Sensitive fields visible in responses (emails, IDs, etc)",
                        "User enumeration possible",
                        "Data leak severity quantified"
                    ]
                },
                {
                    "id": 5,
                    "title": "Abuse Potential Documented",
                    "description": "Assess how API could be abused (rate limiting, etc)",
                    "required": False,
                    "evidence_types": ["analysis_notes"],
                    "expected_findings": [
                        "Rate limiting status documented",
                        "Bulk data access possible through pagination",
                        "Denial of service risk assessed"
                    ]
                }
            ]
        }

    def start_verification_workflow(
        self,
        finding_id: str,
        vulnerability_type: str,
        severity: str
    ) -> VerificationWorkflow:
        """
        Initialize a new verification workflow for a finding.
        
        Args:
            finding_id: ID of the finding
            vulnerability_type: Type of vulnerability
            severity: Severity level
            
        Returns:
            VerificationWorkflow with checkpoints
        """
        import uuid
        
        # Get checkpoint template
        vulnerability_type_lower = vulnerability_type.lower().replace(" ", "_")
        template_checkpoints = self.checkpoint_templates.get(
            vulnerability_type_lower,
            self.checkpoint_templates.get("api", [])  # Default to API template
        )
        
        # Convert template to checkpoint objects
        checkpoints = []
        for cp_data in template_checkpoints:
            checkpoint = VerificationCheckpoint(
                checkpoint_id=cp_data["id"],
                title=cp_data["title"],
                description=cp_data["description"],
                required=cp_data.get("required", True),
                required_evidence_types=[
                    EvidenceType(et) for et in cp_data.get("evidence_types", [])
                ],
                expected_findings=cp_data.get("expected_findings", [])
            )
            checkpoints.append(checkpoint)
        
        workflow = VerificationWorkflow(
            finding_id=finding_id,
            vulnerability_type=vulnerability_type,
            severity=severity,
            workflow_id=str(uuid.uuid4()),
            status=VerificationStatus.STARTED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            checkpoints=checkpoints,
            overall_evidence_quality=0.0,
            completeness_score=0.0
        )
        
        return workflow

    def generate_verification_steps(
        self,
        vulnerability_type: str,
        finding_description: str
    ) -> List[Dict]:
        """
        Generate specific verification steps for a finding.
        
        Args:
            vulnerability_type: Type of vulnerability
            finding_description: Description of the finding
            
        Returns:
            List of verification steps with guidance
        """
        vulnerability_type_lower = vulnerability_type.lower().replace(" ", "_")
        template_checkpoints = self.checkpoint_templates.get(
            vulnerability_type_lower,
            self.checkpoint_templates.get("api", [])
        )
        
        steps = []
        for checkpoint in template_checkpoints:
            step = {
                "step_number": checkpoint["id"],
                "title": checkpoint["title"],
                "description": checkpoint["description"],
                "required": checkpoint.get("required", True),
                "expected_findings": checkpoint.get("expected_findings", []),
                "evidence_needed": [et for et in checkpoint.get("evidence_types", [])],
                "guidance": self._generate_step_guidance(
                    vulnerability_type_lower,
                    checkpoint["id"]
                )
            }
            steps.append(step)
        
        return steps

    def _generate_step_guidance(self, vulnerability_type: str, step_id: int) -> str:
        """Generate detailed guidance for a specific step"""
        guidance_map = {
            "xss": {
                1: "Look for form fields, URL parameters like ?search=, ?q=, ?comment=, ?name=, or API endpoints that accept text input",
                2: "Try simple payloads like <img src=x> or <svg onload=alert('test')> to see if they appear in page source",
                3: "Check browser console for errors. Use developer tools to see if JavaScript executed",
                4: "Reflected appears once, Stored persists across reloads, DOM executes even without reflection",
                5: "Consider what user data JavaScript can access - cookies, form data, localStorage, sessionStorage"
            },
            "idor": {
                1: "Look for numeric IDs (123, 456), UUIDs, or usernames in URLs or responses",
                2: "Use test accounts if available. Document your own resource ID",
                3: "Increment/decrement IDs or try completely different IDs from other users",
                4: "The vulnerability is when no permission check happens",
                5: "Consider PII (names, emails, phone), financial data, private messages, uploaded files"
            },
            "ssrf": {
                1: "Look for URL parameters, image proxies, file downloads, webhook features",
                2: "Use a domain you control (webhook.site, burpcollaborator, etc) to see if server connects",
                3: "Try http://127.0.0.1:8080 or http://192.168.1.1 (be careful not to attack real systems)",
                4: "Common services: Redis (6379), MongoDB (27017), MySQL (3306), HTTP admin panels",
                5: "Consider data that could be accessed internally - API keys, configs, databases"
            },
            "auth_bypass": {
                1: "Document login form, session cookies, JWT tokens, API keys - whatever is used",
                2: "Try accessing /admin without logging in, or /api/users without auth header",
                3: "Use different test accounts if available",
                4: "Document exactly how you bypassed it (removed header, modified token, etc)",
                5: "Check if all users are affected or just some roles"
            },
            "api": {
                1: "Open browser DevTools Network tab and use the application - capture API calls",
                2: "Try calling the endpoint without Authorization header",
                3: "Try calling the endpoint with a different user's token or without token",
                4: "Look at response data - is there PII, emails, IDs, etc?",
                5: "Try rapid requests to see if there's rate limiting, or large requests to see dos potential"
            }
        }
        
        default_guidance = "Follow the step description carefully. Reference the expected findings to ensure completeness."
        return guidance_map.get(vulnerability_type, {}).get(step_id, default_guidance)

    def collect_verification_notes(
        self,
        workflow: VerificationWorkflow,
        checkpoint_id: int,
        evidence_items: List[EvidenceItem],
        notes: str
    ) -> VerificationWorkflow:
        """
        Add evidence and notes to a verification checkpoint.
        
        Args:
            workflow: Current verification workflow
            checkpoint_id: ID of checkpoint to update
            evidence_items: List of evidence items collected
            notes: Hunter's notes for this checkpoint
            
        Returns:
            Updated workflow
        """
        for checkpoint in workflow.checkpoints:
            if checkpoint.checkpoint_id == checkpoint_id:
                checkpoint.evidence_collected.extend(evidence_items)
                checkpoint.notes = notes
                checkpoint.completed = True
                checkpoint.updated_at = datetime.utcnow()
                
                # Auto-score evidence quality
                checkpoint.quality_assessment = self._assess_evidence_quality(
                    checkpoint,
                    evidence_items
                )
        
        # Update workflow timestamps and calculate scores
        workflow.updated_at = datetime.utcnow()
        workflow.completeness_score = self._calculate_completeness(workflow)
        workflow.overall_evidence_quality = self._calculate_evidence_quality(workflow)
        
        return workflow

    def _assess_evidence_quality(
        self,
        checkpoint: VerificationCheckpoint,
        evidence_items: List[EvidenceItem]
    ) -> str:
        """Assess quality of evidence collected"""
        if not evidence_items:
            return "No evidence collected"
        
        # Check evidence types
        provided_types = set(e.type for e in evidence_items)
        required_types = set(checkpoint.required_evidence_types)
        
        if required_types.issubset(provided_types):
            return "High quality - All required evidence types provided"
        elif provided_types & required_types:  # Some overlap
            return "Medium quality - Some required evidence types missing"
        else:
            return "Low quality - Wrong evidence types provided"

    def validate_evidence_quality(
        self,
        workflow: VerificationWorkflow
    ) -> Tuple[bool, List[str]]:
        """
        Validate if evidence collected is sufficient.
        
        Args:
            workflow: Verification workflow to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required checkpoints are completed
        for checkpoint in workflow.checkpoints:
            if checkpoint.required and not checkpoint.completed:
                issues.append(f"Required: {checkpoint.title} - not completed")
            
            if checkpoint.completed:
                # Check evidence quantity
                if not checkpoint.evidence_collected:
                    issues.append(f"{checkpoint.title} - no evidence collected")
                
                # Check evidence types
                provided_types = set(e.type for e in checkpoint.evidence_collected)
                required_types = set(checkpoint.required_evidence_types)
                missing_types = required_types - provided_types
                
                if missing_types:
                    issues.append(
                        f"{checkpoint.title} - missing evidence types: "
                        f"{', '.join(str(t) for t in missing_types)}"
                    )
        
        is_valid = len(issues) == 0
        return is_valid, issues

    def _calculate_completeness(self, workflow: VerificationWorkflow) -> float:
        """Calculate verification workflow completeness (0.0-1.0)"""
        if not workflow.checkpoints:
            return 0.0
        
        required_checkpoints = [cp for cp in workflow.checkpoints if cp.required]
        if not required_checkpoints:
            return 0.0
        
        completed_required = sum(1 for cp in required_checkpoints if cp.completed)
        return completed_required / len(required_checkpoints)

    def _calculate_evidence_quality(self, workflow: VerificationWorkflow) -> float:
        """Calculate overall evidence quality (0.0-1.0)"""
        if not workflow.checkpoints:
            return 0.0
        
        quality_scores = []
        for checkpoint in workflow.checkpoints:
            if not checkpoint.evidence_collected:
                quality_scores.append(0.0)
                continue
            
            # Assess this checkpoint's quality
            provided_types = set(e.type for e in checkpoint.evidence_collected)
            required_types = set(checkpoint.required_evidence_types)
            
            if required_types.issubset(provided_types):
                quality_scores.append(0.9)  # All required evidence present
            elif provided_types & required_types:
                quality_scores.append(0.6)  # Some required evidence
            else:
                quality_scores.append(0.2)  # Wrong evidence types
        
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    def generate_verification_summary(
        self,
        workflow: VerificationWorkflow
    ) -> Dict:
        """
        Generate comprehensive verification summary.
        
        Args:
            workflow: Completed verification workflow
            
        Returns:
            Dictionary with verification summary
        """
        is_valid, issues = self.validate_evidence_quality(workflow)
        
        summary = {
            "finding_id": workflow.finding_id,
            "vulnerability_type": workflow.vulnerability_type,
            "severity": workflow.severity,
            "workflow_id": workflow.workflow_id,
            "status": workflow.status.value,
            "completeness": f"{workflow.completeness_score * 100:.1f}%",
            "evidence_quality": f"{workflow.overall_evidence_quality * 100:.1f}%",
            "is_valid": is_valid,
            "validation_issues": issues,
            "checkpoints_completed": sum(1 for cp in workflow.checkpoints if cp.completed),
            "total_checkpoints": len(workflow.checkpoints),
            "evidence_count": sum(len(cp.evidence_collected) for cp in workflow.checkpoints),
            "recommendations": self._generate_recommendations(workflow)
        }
        
        return summary

    def _generate_recommendations(self, workflow: VerificationWorkflow) -> List[str]:
        """Generate recommendations for verification improvement"""
        recommendations = []
        
        if workflow.completeness_score < 1.0:
            incomplete = [cp.title for cp in workflow.checkpoints if cp.required and not cp.completed]
            recommendations.append(f"Complete required checkpoints: {', '.join(incomplete)}")
        
        if workflow.overall_evidence_quality < 0.7:
            recommendations.append("Collect more evidence and use recommended evidence types")
        
        low_quality_checkpoints = [
            cp for cp in workflow.checkpoints
            if cp.completed and len(cp.evidence_collected) < 2
        ]
        if low_quality_checkpoints:
            recommendations.append(
                f"Add more evidence to: {', '.join(cp.title for cp in low_quality_checkpoints)}"
            )
        
        if not recommendations:
            recommendations.append("Verification workflow appears complete. Ready for reporting.")
        
        return recommendations
