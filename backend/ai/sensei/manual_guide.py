"""
Manual Verification Guide Module
Generates step-by-step verification guides for different vulnerability types.
Educational, not exploitative - focuses on methodology and signal validation.
"""

from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# Supported vulnerability categories
class VulnerabilityType(str, Enum):
    XSS = "xss"
    SSRF = "ssrf"
    IDOR = "idor"
    AUTH_BYPASS = "auth_bypass"
    GRAPHQL = "graphql"
    FILE_UPLOAD = "file_upload"
    OPEN_REDIRECT = "open_redirect"
    API = "api"
    ACCESS_CONTROL = "access_control"
    CLOUD_EXPOSURE = "cloud_exposure"
    SQL_INJECTION = "sql_injection"
    XXE = "xxe"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    COMMAND_INJECTION = "command_injection"
    LOGIC_FLAW = "logic_flaw"


@dataclass
class VerificationStep:
    """Single verification step with guidance"""
    step_number: int
    title: str
    description: str
    key_checks: List[str]
    evidence_to_collect: List[str]
    common_mistakes: List[str]
    safety_notes: List[str]


@dataclass
class VerificationGuide:
    """Complete verification guide for a vulnerability"""
    vulnerability_type: str
    severity: str
    steps: List[VerificationStep]
    impact_explanation: str
    business_impact: str
    validation_tips: List[str]
    evidence_quality_guide: str
    report_tips: List[str]


class ManualGuide:
    """
    Generates educational verification guides for different vulnerability types.
    Focuses on methodology, evidence quality, and high-signal verification.
    """

    def __init__(self):
        """Initialize guide templates"""
        self.guides = self._initialize_guides()

    def _initialize_guides(self) -> Dict[VulnerabilityType, Dict]:
        """Initialize comprehensive vulnerability type guides"""
        return {
            VulnerabilityType.XSS: {
                "title": "Cross-Site Scripting (XSS)",
                "severity": "High",
                "impact": "Attackers can inject malicious scripts to steal user sessions, capture credentials, or modify page content",
                "business_impact": "User account compromise, data theft, brand reputation damage, potential regulatory violations",
                "steps": [
                    {
                        "number": 1,
                        "title": "Identify Input Vector",
                        "description": "Find where user input is accepted (URL parameters, form fields, file uploads, API endpoints)",
                        "checks": [
                            "Document the exact parameter/field accepting input",
                            "Note any input validation or filtering visible",
                            "Identify how input is processed (immediately reflected, stored, delayed)",
                            "Check for content-type handling"
                        ],
                        "evidence": [
                            "Screenshot of input field with parameter name visible",
                            "HTTP request showing the parameter and payload",
                            "Documentation of input acceptance"
                        ],
                        "mistakes": [
                            "Testing without noting exact parameter location",
                            "Assuming validation exists without testing",
                            "Not checking all input vectors"
                        ],
                        "safety": [
                            "Use test payloads in safe environments",
                            "Test with non-malicious probe strings first",
                            "Alert users only about findings, not how to exploit them"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Test Basic XSS",
                        "description": "Test if JavaScript context is accessible without encoding",
                        "checks": [
                            "Submit simple probe: <img src=x onerror=alert('xss')>",
                            "Check for script tag reflection",
                            "Look for event handler reflection",
                            "Check HTML comment handling"
                        ],
                        "evidence": [
                            "Screenshot showing payload reflected in HTML",
                            "HTTP response with payload in page source",
                            "Browser console showing no CSP errors or encoding"
                        ],
                        "mistakes": [
                            "Using real exploitation payloads instead of probes",
                            "Not checking page source vs rendered output",
                            "Ignoring browser developer tools information"
                        ],
                        "safety": [
                            "Use non-functional test payloads",
                            "Test in isolated browser tab",
                            "Document findings without providing full PoC"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Determine XSS Type",
                        "description": "Identify if vulnerability is Reflected, Stored, or DOM-based",
                        "checks": [
                            "Reflected: Does it only appear when you submit the payload?",
                            "Stored: Does it persist across page reloads and for other users?",
                            "DOM: Does it execute even when server doesn't reflect it (check JS code)?",
                            "Test in different browsers/contexts"
                        ],
                        "evidence": [
                            "Browser network tab showing payload in request",
                            "Response HTML with payload visible",
                            "Evidence of type (reflection, persistence, or DOM execution)",
                            "JavaScript source code if DOM-based"
                        ],
                        "mistakes": [
                            "Not confirming type before reporting",
                            "Missing DOM-based XSS by only testing reflection",
                            "Assuming sanitization on client means it's safe"
                        ],
                        "safety": [
                            "Document finding type clearly",
                            "Explain exploitation risk without detailed PoC",
                            "Focus on impact, not exploitation steps"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Evaluate Impact",
                        "description": "Assess what sensitive data or actions can be affected",
                        "checks": [
                            "Can attacker steal session cookies?",
                            "Can attacker capture user keystrokes?",
                            "Can attacker perform actions as the user?",
                            "What data is accessible to JavaScript?",
                            "Are CSRF tokens or sensitive headers accessible?"
                        ],
                        "evidence": [
                            "Documentation of accessible data",
                            "List of possible attacker actions",
                            "Browser console capabilities analysis",
                            "Screenshot showing sensitive data accessibility"
                        ],
                        "mistakes": [
                            "Reporting XSS without explaining impact",
                            "Assuming impact without checking accessibility",
                            "Not considering token/session security"
                        ],
                        "safety": [
                            "Explain impact without weaponizing information",
                            "Focus on data privacy and user security",
                            "Recommend fixes, not exploitation techniques"
                        ]
                    }
                ]
            },
            VulnerabilityType.IDOR: {
                "title": "Insecure Direct Object Reference (IDOR)",
                "severity": "High",
                "impact": "Attackers can access or modify resources they shouldn't have permission to (other users' data, files, accounts)",
                "business_impact": "Privacy violations, data breaches, unauthorized data modification, compliance violations (GDPR, CCPA, HIPAA)",
                "steps": [
                    {
                        "number": 1,
                        "title": "Identify Object Reference",
                        "description": "Find where the application accesses resources by ID or reference",
                        "checks": [
                            "Look for numeric IDs in URLs (e.g., /user/123)",
                            "Find object references in API responses",
                            "Check headers for resource identifiers",
                            "Look for UUIDs or string-based IDs",
                            "Identify object types (users, documents, orders, etc.)"
                        ],
                        "evidence": [
                            "Screenshot of URL with object ID highlighted",
                            "HTTP request showing resource reference",
                            "Documentation of object ID format",
                            "List of accessed resource types"
                        ],
                        "mistakes": [
                            "Not documenting where IDs appear",
                            "Testing only one ID change",
                            "Assuming IDs are random without verification"
                        ],
                        "safety": [
                            "Document ID patterns without exploiting them",
                            "Use only accessible test data initially",
                            "Note security implications of ID patterns"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Test Authorization",
                        "description": "Verify if your account can access other users' resources",
                        "checks": [
                            "Access own resource first - note the ID",
                            "Attempt to access different ID while logged in as different user",
                            "Check if application validates ownership",
                            "Test with IDs from error messages or logs",
                            "Try accessing other resource types"
                        ],
                        "evidence": [
                            "HTTP request to other user's resource",
                            "Response showing unauthorized access",
                            "Comparison of owned vs accessed resource data",
                            "Screenshot showing authorization bypass"
                        ],
                        "mistakes": [
                            "Testing without proper account setup",
                            "Not checking both read and write permissions",
                            "Missing that only certain operations are unprotected"
                        ],
                        "safety": [
                            "Create test accounts specifically for this",
                            "Document findings without modifying data",
                            "Focus on unauthorized access, not data theft"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Identify Exposed Data",
                        "description": "Determine what sensitive data is accessible through IDOR",
                        "checks": [
                            "What fields are returned? (PII, emails, phone numbers, etc.)",
                            "Can you access payment information?",
                            "Can you access private communications?",
                            "What administrative data is exposed?",
                            "Is sensitive data in API responses?"
                        ],
                        "evidence": [
                            "Screenshot of accessible data fields",
                            "HTTP response showing sensitive information",
                            "Documentation of data types accessible",
                            "Comparison of expected vs actual permissions"
                        ],
                        "mistakes": [
                            "Not documenting what data is exposed",
                            "Assuming all data accessible has same sensitivity",
                            "Not checking for pagination/bulk access"
                        ],
                        "safety": [
                            "Explain sensitivity of exposed data",
                            "Don't leak actual user data in reports",
                            "Describe data types instead of examples"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Test Write Permissions",
                        "description": "Verify if you can modify other users' resources (if applicable)",
                        "checks": [
                            "Can you modify other users' data?",
                            "Can you delete other users' resources?",
                            "Can you change ownership/permissions?",
                            "Are there any restrictions on modifications?",
                            "What operations are affected?"
                        ],
                        "evidence": [
                            "HTTP request attempting modification",
                            "Before/after state comparison",
                            "Documentation of what could be changed",
                            "Screenshot of unauthorized modification"
                        ],
                        "mistakes": [
                            "Actually modifying production data",
                            "Not reverting test changes immediately",
                            "Not testing all modification operations"
                        ],
                        "safety": [
                            "Use test/sandbox environments only",
                            "Revert all changes immediately",
                            "Document capability without actually exploiting"
                        ]
                    }
                ]
            },
            VulnerabilityType.SSRF: {
                "title": "Server-Side Request Forgery (SSRF)",
                "severity": "High",
                "impact": "Application makes HTTP requests to attacker-controlled URLs, potentially accessing internal systems, cloud metadata, or services",
                "business_impact": "Internal system exposure, cloud credential theft, lateral movement, RCE potential, compliance violations",
                "steps": [
                    {
                        "number": 1,
                        "title": "Identify Request Generation Points",
                        "description": "Find where application accepts URLs or makes external requests",
                        "checks": [
                            "Look for URL parameters (e.g., ?url=, ?redirect=, ?fetch=)",
                            "Check file download/upload features",
                            "Identify API endpoints that accept external URLs",
                            "Look for image proxy or content fetching features",
                            "Check webhook or URL callback functionality"
                        ],
                        "evidence": [
                            "Screenshot of URL parameter visible",
                            "HTTP request showing URL parameter",
                            "Documentation of request features",
                            "List of URL-accepting endpoints"
                        ],
                        "mistakes": [
                            "Not identifying all request generation points",
                            "Assuming SSRF only in obvious places",
                            "Missing indirect request generation"
                        ],
                        "safety": [
                            "Document parameters without testing URLs yet",
                            "Research typical SSRF patterns",
                            "Plan safe testing approach first"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Test Basic SSRF",
                        "description": "Verify if server makes requests to attacker-provided URLs",
                        "checks": [
                            "Set up controlled test server/domain",
                            "Submit test URL to parameter",
                            "Check if server connects (HTTP logs)",
                            "Look for timeouts or error messages",
                            "Test with different protocols (http, https, ftp)"
                        ],
                        "evidence": [
                            "Web server logs showing connection from target server",
                            "HTTP request with test URL",
                            "Response indicating connection attempt",
                            "Evidence of protocol support"
                        ],
                        "mistakes": [
                            "Not setting up controlled testing environment",
                            "Trying real URLs instead of test domains",
                            "Not checking server logs for connection evidence"
                        ],
                        "safety": [
                            "Use controlled test environment only",
                            "Don't access real internal systems",
                            "Document connection capability safely"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Test Internal Access",
                        "description": "Determine if server can access internal systems (in safe test environment)",
                        "checks": [
                            "Attempt localhost/127.0.0.1 requests",
                            "Try internal IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)",
                            "Check for cloud metadata endpoints (AWS: 169.254.169.254)",
                            "Test common internal ports (admin panels, databases)",
                            "Document access patterns"
                        ],
                        "evidence": [
                            "Documentation of which internal systems are accessible",
                            "HTTP response times indicating responses",
                            "Error messages revealing internal system info",
                            "Evidence of internal system responses"
                        ],
                        "mistakes": [
                            "Actually accessing production internal systems",
                            "Not being aware of metadata endpoint risks",
                            "Not documenting internal system exposure"
                        ],
                        "safety": [
                            "Only test in authorized test environments",
                            "Don't actually access sensitive internal systems",
                            "Be especially careful with cloud metadata endpoints",
                            "Immediately stop if accessing real sensitive data"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Assess Impact",
                        "description": "Evaluate what internal systems and data are at risk",
                        "checks": [
                            "What internal services are accessible?",
                            "Can you reach database servers?",
                            "Can you access admin panels?",
                            "Is cloud metadata available?",
                            "What's the potential for lateral movement?",
                            "Could this lead to credential theft?"
                        ],
                        "evidence": [
                            "Documentation of accessible internal systems",
                            "Analysis of credential/metadata exposure risk",
                            "Potential attack chains documented",
                            "Impact assessment on business systems"
                        ],
                        "mistakes": [
                            "Not assessing full impact",
                            "Underestimating metadata endpoint risk",
                            "Not considering attacker goals"
                        ],
                        "safety": [
                            "Explain risk without detailed exploitation path",
                            "Emphasize security implications",
                            "Recommend filtering/validation fixes"
                        ]
                    }
                ]
            },
            VulnerabilityType.AUTH_BYPASS: {
                "title": "Authentication Bypass",
                "severity": "Critical",
                "impact": "Attackers can access protected functionality without proper authentication or with another user's credentials",
                "business_impact": "Complete system compromise, all user data accessible, unauthorized actions, regulatory violations, business continuity risk",
                "steps": [
                    {
                        "number": 1,
                        "title": "Identify Authentication Mechanisms",
                        "description": "Understand how the application authenticates users",
                        "checks": [
                            "Document login flow (form, API, OAuth, etc.)",
                            "Identify authentication headers/tokens",
                            "Check for session cookie usage",
                            "Look for API keys or authentication methods",
                            "Document logout/session expiration behavior"
                        ],
                        "evidence": [
                            "Screenshots of login page/flow",
                            "HTTP headers showing authentication mechanism",
                            "Session cookie analysis",
                            "Documentation of auth methods"
                        ],
                        "mistakes": [
                            "Not fully understanding auth flow",
                            "Testing only obvious auth bypass",
                            "Missing secondary auth mechanisms"
                        ],
                        "safety": [
                            "Document auth mechanisms without attempting bypass",
                            "Use created test accounts for testing",
                            "Don't target production accounts"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Test Authentication Bypass",
                        "description": "Attempt to bypass authentication mechanisms",
                        "checks": [
                            "Try accessing protected endpoints without auth",
                            "Test with invalid/empty credentials",
                            "Check for JWT manipulation vulnerabilities",
                            "Test session token validity",
                            "Look for timing-based authentication bypasses",
                            "Check for default credentials"
                        ],
                        "evidence": [
                            "HTTP request without authentication headers",
                            "Response showing unauthorized access",
                            "Comparison of auth vs no-auth responses",
                            "Documentation of bypass method"
                        ],
                        "mistakes": [
                            "Only testing obvious bypasses",
                            "Not checking all protected endpoints",
                            "Assuming same bypass works everywhere"
                        ],
                        "safety": [
                            "Use test accounts only",
                            "Test one bypass at a time",
                            "Document findings immediately",
                            "Stop testing once vulnerability confirmed"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Test Account Compromise",
                        "description": "Determine if you can access other users' accounts",
                        "checks": [
                            "Can you login as different users?",
                            "Can you manipulate user IDs to access others?",
                            "Are there broken session controls?",
                            "Can you re-use other users' tokens?",
                            "Is there account enumeration possible?"
                        ],
                        "evidence": [
                            "Documentation of account access capability",
                            "HTTP request accessing different user data",
                            "Response showing unauthorized account access",
                            "Evidence of failed vs successful access patterns"
                        ],
                        "mistakes": [
                            "Actually modifying other users' accounts",
                            "Not reverting unauthorized access tests",
                            "Not documenting compromised user accounts"
                        ],
                        "safety": [
                            "Only test with controlled accounts",
                            "Revert all changes immediately",
                            "Don't access real user data if possible",
                            "Focus on demonstrating vulnerability, not exploitation"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Assess Scope and Impact",
                        "description": "Evaluate how many users/systems are affected",
                        "checks": [
                            "Is bypass applicable to all users?",
                            "Can you access all user accounts?",
                            "Are admin accounts affected?",
                            "What functionality becomes accessible?",
                            "What data is exposed?",
                            "Can you perform unauthorized actions?"
                        ],
                        "evidence": [
                            "Documentation of affected user count",
                            "List of accessible functionality",
                            "Data exposure analysis",
                            "Business impact assessment"
                        ],
                        "mistakes": [
                            "Not assessing full scope",
                            "Assuming bypass affects all users without testing",
                            "Underestimating impact"
                        ],
                        "safety": [
                            "Provide clear scope and impact",
                            "Explain risk without detailed exploitation",
                            "Recommend immediate mitigation"
                        ]
                    }
                ]
            },
            VulnerabilityType.API: {
                "title": "API Vulnerabilities",
                "severity": "High/Critical",
                "impact": "Broken authentication, excessive data exposure, lack of rate limiting, unsafe deserialization, or API logic flaws",
                "business_impact": "Data breaches, API abuse, unauthorized actions, resource exhaustion, business logic compromise",
                "steps": [
                    {
                        "number": 1,
                        "title": "Map API Endpoints",
                        "description": "Document all API endpoints and their functionality",
                        "checks": [
                            "Use browser DevTools to capture API calls",
                            "Document request/response format",
                            "Identify required parameters and headers",
                            "Map authentication mechanisms",
                            "Document all HTTP methods (GET, POST, PUT, DELETE, PATCH)"
                        ],
                        "evidence": [
                            "List of API endpoints",
                            "Request/response examples",
                            "Documentation of parameters",
                            "Authentication requirements"
                        ],
                        "mistakes": [
                            "Not mapping all endpoints before testing",
                            "Missing OPTIONS/HEAD methods",
                            "Not documenting response formats"
                        ],
                        "safety": [
                            "Document endpoints without making requests yet",
                            "Use production monitoring responsibly",
                            "Plan testing approach for each endpoint"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Test Authentication & Authorization",
                        "description": "Verify API respects authentication and authorization",
                        "checks": [
                            "Test endpoints without authentication",
                            "Test with invalid/expired tokens",
                            "Test accessing other users' data",
                            "Check permission enforcement",
                            "Test token manipulation"
                        ],
                        "evidence": [
                            "API response without authentication",
                            "Unauthorized access examples",
                            "Permission bypass examples",
                            "Authorization flaw documentation"
                        ],
                        "mistakes": [
                            "Only testing obvious authentication flaws",
                            "Not checking authorization for each endpoint",
                            "Missing that endpoints are protected but exposed"
                        ],
                        "safety": [
                            "Test with your own data first",
                            "Use dedicated test accounts",
                            "Document findings without exploitation"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Test Data Exposure",
                        "description": "Identify excessive or sensitive data in API responses",
                        "checks": [
                            "What fields are returned in responses?",
                            "Are PII or sensitive data exposed?",
                            "Can you enumerate users via API?",
                            "Are there data leaks in error messages?",
                            "Can you trigger verbose error responses?"
                        ],
                        "evidence": [
                            "API response showing sensitive data",
                            "Examples of exposed fields",
                            "Data enumeration examples",
                            "Error message examples with sensitive info"
                        ],
                        "mistakes": [
                            "Not checking all API responses",
                            "Missing verbose error modes",
                            "Not considering indirect data exposure"
                        ],
                        "safety": [
                            "Capture data exposure without storing sensitive info",
                            "Focus on data types not actual values",
                            "Document exposure pattern"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Test Rate Limiting & Resource Exhaustion",
                        "description": "Verify API protects against abuse and resource exhaustion",
                        "checks": [
                            "Test rapid requests to endpoints",
                            "Check for rate limiting headers",
                            "Look for query complexity attacks (GraphQL)",
                            "Test large data request payloads",
                            "Check for denial of service vulnerabilities"
                        ],
                        "evidence": [
                            "Rate limiting header analysis",
                            "Response times for rapid requests",
                            "Documentation of unprotected endpoints",
                            "Resource exhaustion examples"
                        ],
                        "mistakes": [
                            "Actually causing denial of service",
                            "Not backing off when seeing issues",
                            "Not documenting rate limit findings"
                        ],
                        "safety": [
                            "Use light testing only",
                            "Stop if causing actual DoS",
                            "Document findings responsibly",
                            "Coordinate with program for testing"
                        ]
                    }
                ]
            },
            VulnerabilityType.FILE_UPLOAD: {
                "title": "Insecure File Upload",
                "severity": "High/Critical",
                "impact": "Uploading malicious files that execute on server or are served to users",
                "business_impact": "Remote code execution, malware distribution, cross-site scripting, website defacement, compliance violations",
                "steps": [
                    {
                        "number": 1,
                        "title": "Identify Upload Functionality",
                        "description": "Find all file upload features in the application",
                        "checks": [
                            "Locate file upload forms",
                            "Check accepted file types",
                            "Look for drag-drop upload",
                            "Identify upload API endpoints",
                            "Note upload location/URL patterns"
                        ],
                        "evidence": [
                            "Screenshot of upload form",
                            "List of upload endpoints",
                            "Accepted file types documentation",
                            "Upload URL pattern documentation"
                        ],
                        "mistakes": [
                            "Not finding all upload endpoints",
                            "Missing multiple upload features",
                            "Not noting upload location"
                        ],
                        "safety": [
                            "Map upload functionality without uploading yet",
                            "Plan test files in advance",
                            "Use non-malicious test files"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Test File Type Validation",
                        "description": "Verify application validates uploaded file types",
                        "checks": [
                            "Upload file with wrong extension (.php as .jpg)",
                            "Try double extension (.php.jpg)",
                            "Test null byte injection (.php%00.jpg)",
                            "Try alternate MIME types",
                            "Upload polyglot files (both image and code)",
                            "Test case variations (.PHP, .PhP)"
                        ],
                        "evidence": [
                            "Successful upload of non-image file",
                            "Uploaded file stored with executable extension",
                            "File served with executable MIME type",
                            "Documentation of validation bypass"
                        ],
                        "mistakes": [
                            "Only testing obvious file types",
                            "Not trying encoding bypasses",
                            "Not checking stored vs served file types"
                        ],
                        "safety": [
                            "Use test files with no actual code",
                            "Don't actually execute uploaded files",
                            "Document findings without creating exploits"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Test File Content Validation",
                        "description": "Check if application validates file content (magic bytes)",
                        "checks": [
                            "Upload file with image extension but text content",
                            "Check if application reads file headers",
                            "Try uploading archives (.zip, .tar.gz)",
                            "Test archive extraction behavior",
                            "Look for serialization handling"
                        ],
                        "evidence": [
                            "Non-image file accepted as image",
                            "Archive extraction examples",
                            "File content validation bypass documentation",
                            "Dangerous content type handling"
                        ],
                        "mistakes": [
                            "Only testing file extensions",
                            "Not checking actual file content",
                            "Missing archive attack vectors"
                        ],
                        "safety": [
                            "Use safe test content",
                            "Don't create actual malicious files",
                            "Document validation gaps safely"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Test Execution & Serving",
                        "description": "Verify uploaded files can't be executed",
                        "checks": [
                            "Can uploaded files be accessed via web?",
                            "Are files executed by server?",
                            "Can files be used for XSS?",
                            "Is upload directory web-accessible?",
                            "Can you chain with other vulnerabilities?"
                        ],
                        "evidence": [
                            "Uploaded file URL accessible",
                            "File execution demonstration",
                            "XSS or code execution evidence",
                            "Upload directory permissions analysis"
                        ],
                        "mistakes": [
                            "Actually executing code on server",
                            "Not documenting execution path",
                            "Missing XSS via uploaded files"
                        ],
                        "safety": [
                            "Don't create working exploits",
                            "Document vulnerability without executing",
                            "Focus on implications not actual exploitation"
                        ]
                    }
                ]
            },
            VulnerabilityType.LOGIC_FLAW: {
                "title": "Business Logic Flaw",
                "severity": "High/Medium",
                "impact": "Application allows unintended business outcomes (price manipulation, unauthorized actions, state bypasses)",
                "business_impact": "Financial loss, unauthorized transactions, privilege escalation, regulatory violations",
                "steps": [
                    {
                        "number": 1,
                        "title": "Understand Business Logic",
                        "description": "Map the intended business workflow and rules",
                        "checks": [
                            "Document complete user workflows",
                            "Identify business rules and constraints",
                            "Note state transitions and validations",
                            "Check for approval workflows",
                            "Document access controls per role"
                        ],
                        "evidence": [
                            "Workflow documentation",
                            "Business rule documentation",
                            "State transition diagrams",
                            "Approval workflow documentation"
                        ],
                        "mistakes": [
                            "Not fully understanding business workflow",
                            "Assuming rules are enforced correctly",
                            "Missing hidden constraints"
                        ],
                        "safety": [
                            "Learn workflows from documentation/help",
                            "Use application normally first",
                            "Identify patterns before testing"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Identify Logic Flaws",
                        "description": "Find places where business logic can be bypassed",
                        "checks": [
                            "Can you skip required steps?",
                            "Can you reverse state transitions?",
                            "Can you access unachievable states?",
                            "Are there timing-based bypasses?",
                            "Can you manipulate conditional logic?"
                        ],
                        "evidence": [
                            "Demonstration of skipped workflow steps",
                            "Evidence of unauthorized state access",
                            "Documentation of conditional bypass",
                            "Examples of broken business logic"
                        ],
                        "mistakes": [
                            "Not fully testing logic flows",
                            "Assuming safeguards exist without testing",
                            "Missing multi-step bypasses"
                        ],
                        "safety": [
                            "Test carefully to avoid real business impact",
                            "Use test data/environment when possible",
                            "Revert any state changes immediately"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Test Impact",
                        "description": "Assess potential business impact of logic flaw",
                        "checks": [
                            "What unauthorized actions become possible?",
                            "Can you manipulate values (prices, quantities)?",
                            "Can you bypass security controls?",
                            "What data could be accessed/modified?",
                            "What's the financial impact?"
                        ],
                        "evidence": [
                            "Documentation of possible unauthorized actions",
                            "Impact assessment per business outcome",
                            "Financial impact calculation (if applicable)",
                            "Examples of exploited logic"
                        ],
                        "mistakes": [
                            "Not assessing full impact",
                            "Only testing obvious logic flows",
                            "Missing cumulative impact"
                        ],
                        "safety": [
                            "Don't actually exploit for financial gain",
                            "Use test transactions/data",
                            "Document capability without actual exploitation"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Document Findings",
                        "description": "Create clear reproduction steps and impact documentation",
                        "checks": [
                            "Write step-by-step reproduction steps",
                            "Explain what should happen vs what does happen",
                            "Quantify business impact",
                            "Suggest remediation approaches",
                            "Note affected user roles/scenarios"
                        ],
                        "evidence": [
                            "Clear reproduction steps",
                            "Before/after state comparison",
                            "Impact documentation",
                            "Suggested fixes"
                        ],
                        "mistakes": [
                            "Vague reproduction steps",
                            "Not explaining expected vs actual behavior",
                            "Underestimating impact"
                        ],
                        "safety": [
                            "Provide clear documentation",
                            "Explain risk to business",
                            "Recommend secure alternatives"
                        ]
                    }
                ]
            }
        }

    def generate_verification_guide(
        self,
        vulnerability_type: str,
        finding_title: str,
        finding_description: str,
        severity: str = "High"
    ) -> VerificationGuide:
        """
        Generate a complete verification guide for a finding.
        
        Args:
            vulnerability_type: Type of vulnerability
            finding_title: Title of the finding
            finding_description: Description of the vulnerability
            severity: Severity level
            
        Returns:
            VerificationGuide with step-by-step instructions
        """
        try:
            vuln_type = VulnerabilityType(vulnerability_type.lower())
        except ValueError:
            vuln_type = VulnerabilityType.API  # Default to API

        template = self.guides.get(vuln_type, self.guides[VulnerabilityType.API])
        
        steps = []
        for step_data in template.get("steps", []):
            step = VerificationStep(
                step_number=step_data["number"],
                title=step_data["title"],
                description=step_data["description"],
                key_checks=step_data["checks"],
                evidence_to_collect=step_data["evidence"],
                common_mistakes=step_data["mistakes"],
                safety_notes=step_data["safety"]
            )
            steps.append(step)

        guide = VerificationGuide(
            vulnerability_type=vuln_type.value,
            severity=severity,
            steps=steps,
            impact_explanation=template["impact"],
            business_impact=template["business_impact"],
            validation_tips=self._generate_validation_tips(vuln_type),
            evidence_quality_guide=self._generate_evidence_guide(vuln_type),
            report_tips=self._generate_report_tips(vuln_type)
        )
        
        return guide

    def _generate_validation_tips(self, vuln_type: VulnerabilityType) -> List[str]:
        """Generate validation tips for vulnerability type"""
        tips = {
            VulnerabilityType.XSS: [
                "Always validate both reflected and stored XSS",
                "Check for DOM-based XSS by examining JavaScript code",
                "Test CSP bypass techniques for common scenarios",
                "Verify cookie accessibility from JavaScript context",
                "Test in multiple browsers for consistent behavior"
            ],
            VulnerabilityType.SSRF: [
                "Test with controlled external domain (not production)",
                "Check internal IP ranges systematically",
                "Be cautious with cloud metadata endpoints",
                "Verify server actually makes external connections",
                "Document internal system exposure clearly"
            ],
            VulnerabilityType.IDOR: [
                "Create multiple test accounts to verify authorization",
                "Test both read and write operations",
                "Check all resource types, not just obvious ones",
                "Verify pagination/bulk operations aren't bypassed",
                "Document exact user role and object accessed"
            ],
            VulnerabilityType.AUTH_BYPASS: [
                "Test all authentication mechanisms (form, API, OAuth)",
                "Check for default credentials in code/config",
                "Verify session token validation on every request",
                "Test token manipulation (expiration, user ID, role)",
                "Confirm logout actually invalidates sessions"
            ],
            VulnerabilityType.FILE_UPLOAD: [
                "Test both client and server-side validation",
                "Try multiple bypass techniques systematically",
                "Check if uploaded files are accessible/executable",
                "Verify proper access controls on uploaded files",
                "Test archive extraction and symlink attacks"
            ],
            VulnerabilityType.API: [
                "Map all API endpoints before testing",
                "Test each endpoint with no authentication first",
                "Verify authorization for each endpoint independently",
                "Check response data for sensitive information",
                "Test parameter tampering and manipulation"
            ],
            VulnerabilityType.LOGIC_FLAW: [
                "Fully understand intended business workflow first",
                "Test state transitions from multiple entry points",
                "Check for race conditions in critical workflows",
                "Verify all required validations are enforced",
                "Test with various user roles and permissions"
            ]
        }
        return tips.get(vuln_type, ["Carefully test each step", "Document findings thoroughly", "Focus on impact assessment"])

    def _generate_evidence_guide(self, vuln_type: VulnerabilityType) -> str:
        """Generate evidence quality guidance for vulnerability type"""
        guides = {
            VulnerabilityType.XSS: "Include: 1) Screenshot of payload in browser, 2) HTTP request/response showing reflection, 3) Browser console showing execution, 4) Explanation of impact (what could be stolen/modified)",
            VulnerabilityType.SSRF: "Include: 1) HTTP request with attacker-controlled URL, 2) Server logs showing connection from target, 3) Response indicating internal access, 4) Documentation of accessed internal systems",
            VulnerabilityType.IDOR: "Include: 1) HTTP request to owned resource (with ID), 2) HTTP request to other user's resource, 3) Response showing unauthorized data, 4) Clear comparison of permissions",
            VulnerabilityType.AUTH_BYPASS: "Include: 1) Request without authentication headers, 2) Response showing protected access, 3) Comparison of authenticated vs unauthenticated access, 4) Documentation of bypass technique",
            VulnerabilityType.FILE_UPLOAD: "Include: 1) Original file being uploaded, 2) HTTP request showing file upload, 3) Screenshot showing file stored/accessible, 4) Evidence of execution/serving",
            VulnerabilityType.API: "Include: 1) API endpoint and request format, 2) Response showing flaw, 3) Request without authentication/authorization, 4) Documentation of exposed/manipulated data",
            VulnerabilityType.LOGIC_FLAW: "Include: 1) Documentation of intended business logic, 2) Step-by-step bypass demonstration, 3) Before/after state comparison, 4) Impact quantification"
        }
        return guides.get(vuln_type, "Include: 1) Clear HTTP request/response examples, 2) Screenshots of vulnerability manifestation, 3) Explanation of impact, 4) Proof of concept without actual exploitation")

    def _generate_report_tips(self, vuln_type: VulnerabilityType) -> List[str]:
        """Generate report writing tips for vulnerability type"""
        tips = {
            VulnerabilityType.XSS: [
                "Clearly state XSS type (Reflected/Stored/DOM)",
                "Explain what data could be stolen",
                "Describe how attacker would deliver payload",
                "Note browser/CSP restrictions that might apply",
                "Suggest Content-Security-Policy as remediation"
            ],
            VulnerabilityType.SSRF: [
                "List specific internal systems that can be accessed",
                "Explain cloud metadata endpoint risks clearly",
                "Document lateral movement potential",
                "Suggest URL allowlist as remediation",
                "Note credential exposure risks"
            ],
            VulnerabilityType.IDOR: [
                "Specify exact authorization check that's missing",
                "List all resource types affected",
                "Explain scope (read-only vs read-write)",
                "Quantify user data exposure",
                "Suggest role-based access control implementation"
            ],
            VulnerabilityType.AUTH_BYPASS: [
                "Clearly describe bypass method",
                "List all affected functionality",
                "Quantify user accounts at risk",
                "Explain business impact",
                "Provide implementation recommendations"
            ],
            VulnerabilityType.FILE_UPLOAD: [
                "Describe file type validation bypass used",
                "Explain execution/serving scenario",
                "Note if payload was actually executed",
                "Quantify user impact (malware distribution, etc)",
                "Recommend proper file validation implementation"
            ],
            VulnerabilityType.API: [
                "Specify affected endpoint(s)",
                "Explain authentication/authorization flaw",
                "Document exposed/manipulated data",
                "Suggest API security best practices",
                "Note impact on API consumers"
            ],
            VulnerabilityType.LOGIC_FLAW: [
                "Clearly explain intended business logic",
                "Document exact bypass steps",
                "Quantify business impact (financial, etc)",
                "Provide remediation suggestions",
                "Note if exploit is easily repeatable"
            ]
        }
        return tips.get(vuln_type, ["Be clear and specific", "Focus on impact", "Provide actionable recommendations"])

    def explain_bug_category(self, vulnerability_type: str) -> Dict:
        """
        Provide educational explanation of vulnerability category.
        
        Args:
            vulnerability_type: Type of vulnerability
            
        Returns:
            Dictionary with explanation, examples, and prevention methods
        """
        try:
            vuln_type = VulnerabilityType(vulnerability_type.lower())
        except ValueError:
            return {"error": "Unknown vulnerability type"}

        template = self.guides.get(vuln_type, {})
        
        return {
            "type": vuln_type.value,
            "title": template.get("title", ""),
            "severity": template.get("severity", ""),
            "what_is_it": template.get("impact", ""),
            "why_matters": template.get("business_impact", ""),
            "how_to_test": self._get_first_step_summary(template),
            "common_mistakes": self._get_common_mistakes(template)
        }

    def _get_first_step_summary(self, template: Dict) -> str:
        """Get summary of first testing step"""
        steps = template.get("steps", [])
        if steps and steps[0]:
            return f"{steps[0].get('title', '')}: {steps[0].get('description', '')}"
        return "Test vulnerability systematically"

    def _get_common_mistakes(self, template: Dict) -> List[str]:
        """Extract common mistakes across all steps"""
        mistakes = []
        for step in template.get("steps", []):
            mistakes.extend(step.get("mistakes", [])[:2])  # Get top 2 mistakes per step
        return mistakes[:5]  # Return top 5 unique mistakes

    def recommend_manual_checks(self, vulnerability_type: str) -> List[Dict]:
        """
        Get recommended manual checks for thorough validation.
        
        Args:
            vulnerability_type: Type of vulnerability
            
        Returns:
            List of recommended checks with explanation
        """
        try:
            vuln_type = VulnerabilityType(vulnerability_type.lower())
        except ValueError:
            return []

        template = self.guides.get(vuln_type, {})
        checks = []
        
        for step in template.get("steps", []):
            for check in step.get("checks", [])[:2]:  # Top 2 checks per step
                checks.append({
                    "step": step.get("title", ""),
                    "check": check,
                    "why_important": self._explain_check_importance(check, vuln_type)
                })
        
        return checks

    def _explain_check_importance(self, check: str, vuln_type: VulnerabilityType) -> str:
        """Explain why a check is important"""
        explanations = {
            VulnerabilityType.IDOR: "Authorization checks prevent users from accessing data they shouldn't see",
            VulnerabilityType.XSS: "Script execution context indicates JavaScript can be injected and run",
            VulnerabilityType.SSRF: "Internal network access reveals potential for lateral movement",
            VulnerabilityType.FILE_UPLOAD: "File type validation bypass allows malicious file execution",
            VulnerabilityType.API: "Endpoint accessibility without auth indicates complete exposure",
            VulnerabilityType.AUTH_BYPASS: "Authentication mechanism verification ensures identity verification",
            VulnerabilityType.LOGIC_FLAW: "State transition testing reveals broken business logic"
        }
        return explanations.get(vuln_type, "This check helps validate the vulnerability findings")
