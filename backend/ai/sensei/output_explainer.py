"""
Output Explainer Module
Explains scanner outputs, tool findings, and technical results in hunter-friendly language.
Helps hunters understand what tools found and why it matters.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ToolType(str, Enum):
    """Types of security tools"""
    NUCLEI = "nuclei"
    DALFOX = "dalfox"
    SQLMAP = "sqlmap"
    FFUF = "ffuf"
    BURP = "burp"
    NMAP = "nmap"
    MANUAL = "manual"


@dataclass
class ExplanationResult:
    """Result of explaining tool output"""
    tool_type: str
    finding_type: str
    severity: str
    explanation: str  # Hunter-friendly explanation
    what_it_means: str  # Business impact
    why_it_matters: str  # Security implications
    next_steps: List[str]  # What to do next
    validation_guidance: str  # How to manually verify
    report_tips: List[str]  # Tips for including in report


class OutputExplainer:
    """
    Explains technical tool outputs in hunter-friendly language.
    Helps hunters understand findings and validates findings.
    """

    def __init__(self):
        """Initialize explanation templates"""
        self.tool_patterns = self._initialize_tool_patterns()

    def _initialize_tool_patterns(self) -> Dict:
        """Initialize detection patterns for different tools"""
        return {
            "nuclei": {
                "xss": {
                    "severity": "High",
                    "explanation": "Nuclei found a potential JavaScript injection point where user input can be injected into the page",
                    "what_it_means": "Attackers could run JavaScript in other users' browsers",
                    "why_it_matters": "JavaScript access means stealing cookies, capturing keystrokes, defacing pages, or spreading malware",
                    "validation": "Manually test the exact parameter nuclei found. Verify payload appears in page source without encoding.",
                    "report_tips": [
                        "Specify exact template nuclei used",
                        "Provide proof nuclei alert was triggered",
                        "Add manual verification showing unencoded reflection",
                        "Explain impact clearly"
                    ]
                },
                "sqli": {
                    "severity": "Critical",
                    "explanation": "Nuclei found evidence of SQL injection - where database queries might be vulnerable to manipulation",
                    "what_it_means": "Database queries might be vulnerable to manipulation",
                    "why_it_matters": "SQL injection can leak all user data, modify database, potentially execute system commands",
                    "validation": "Manually test with SQL injection payloads. Check error messages or response differences.",
                    "report_tips": [
                        "Include specific SQL injection payload that worked",
                        "Show HTTP request/response demonstrating the injection",
                        "Document what data or functionality is accessible",
                        "Provide step-by-step reproduction"
                    ]
                },
                "cve": {
                    "severity": "Medium to Critical",
                    "explanation": "Nuclei detected a known vulnerability (CVE) in software running on the target",
                    "what_it_means": "The system is running vulnerable software with a publicly known flaw",
                    "why_it_matters": "Public exploits exist and system is vulnerable to automated attacks",
                    "validation": "Verify target is actually running the vulnerable version. Check version numbers.",
                    "report_tips": [
                        "Include CVE number and link",
                        "Show evidence of vulnerable version",
                        "Explain what an attacker could do",
                        "Note if fix/upgrade is available"
                    ]
                }
            },
            "dalfox": {
                "xss": {
                    "severity": "High",
                    "explanation": "Dalfox found a parameter where JavaScript injection may be possible",
                    "what_it_means": "User input might be reflected in a way that allows script execution",
                    "why_it_matters": "JavaScript execution in browser context allows cookie theft, session hijacking, defacement",
                    "validation": "Test the parameter manually with the payloads dalfox used. Check both HTML and browser execution.",
                    "report_tips": [
                        "Verify dalfox findings are accurate (false positives exist)",
                        "Add manual validation evidence",
                        "Document what data is accessible",
                        "Provide clear reproduction steps"
                    ]
                }
            },
            "sqlmap": {
                "sqli": {
                    "severity": "Critical",
                    "explanation": "SQLMap confirmed SQL injection vulnerability - confirmed exploitation of database query",
                    "what_it_means": "Database queries are vulnerable to manipulation through user input",
                    "why_it_matters": "Attacker can extract data, modify records, potentially execute commands",
                    "validation": "SQLMap already provided detailed proof. Document the data extracted.",
                    "report_tips": [
                        "Include specific parameter and injection technique",
                        "Show data SQLMap extracted",
                        "Explain data sensitivity",
                        "Note if admin/sensitive functions affected"
                    ]
                }
            },
            "ffuf": {
                "directory": {
                    "severity": "Low to Medium",
                    "explanation": "FFUF found a hidden or unlinked directory/endpoint",
                    "what_it_means": "Directory exists and is accessible but not commonly known",
                    "why_it_matters": "Depends on what's in the directory (admin panels, debug endpoints, sensitive data)",
                    "validation": "Manually access the URL to confirm it exists and what's inside",
                    "report_tips": [
                        "Check what the directory contains",
                        "If it's admin/debug/internal, explain risk",
                        "If it's already linked elsewhere, probably not a finding",
                        "Explain what's at risk if exposed"
                    ]
                },
                "file": {
                    "severity": "Low to High (varies)",
                    "explanation": "FFUF found a hidden file",
                    "what_it_means": "File is accessible but not publicly linked",
                    "why_it_matters": "Depends on file type (.bak, .config, .env, .git, etc)",
                    "validation": "Manually access file and examine contents",
                    "report_tips": [
                        ".env files = critical (credentials exposed)",
                        ".git files = medium (source code exposed)",
                        ".bak files = medium (backup data exposed)",
                        "Explain what data is exposed"
                    ]
                }
            }
        }

    def explain_scan_output(
        self,
        tool_type: str,
        output: Dict,
        raw_output: Optional[str] = None
    ) -> ExplanationResult:
        """
        Explain scanner output in hunter-friendly language.
        
        Args:
            tool_type: Type of tool (nuclei, dalfox, sqlmap, etc)
            output: Parsed output from tool
            raw_output: Raw output text for reference
            
        Returns:
            ExplanationResult with clear explanation
        """
        finding_type = output.get("finding_type", "unknown")
        
        # Get pattern from templates
        tool_patterns = self.tool_patterns.get(tool_type.lower(), {})
        pattern = tool_patterns.get(finding_type.lower(), {})
        
        if not pattern:
            # Generate generic explanation
            return self._generate_generic_explanation(tool_type, output, raw_output)
        
        result = ExplanationResult(
            tool_type=tool_type,
            finding_type=finding_type,
            severity=pattern.get("severity", "Medium"),
            explanation=pattern.get("explanation", ""),
            what_it_means=pattern.get("what_it_means", ""),
            why_it_matters=pattern.get("why_it_matters", ""),
            next_steps=self._generate_next_steps(tool_type, finding_type),
            validation_guidance=pattern.get("validation", ""),
            report_tips=pattern.get("report_tips", [])
        )
        
        return result

    def _generate_generic_explanation(
        self,
        tool_type: str,
        output: Dict,
        raw_output: Optional[str]
    ) -> ExplanationResult:
        """Generate generic explanation for unknown findings"""
        return ExplanationResult(
            tool_type=tool_type,
            finding_type=output.get("finding_type", "unknown"),
            severity=output.get("severity", "Medium"),
            explanation=f"{tool_type} found a potential security issue. Review the tool output carefully.",
            what_it_means="The tool detected something that might be a vulnerability",
            why_it_matters="Tool-detected issues need manual validation before reporting",
            next_steps=[
                "Examine the tool's full output",
                "Manually verify the finding exists",
                "Determine actual impact and severity",
                "Document with manual evidence"
            ],
            validation_guidance="Manually test and verify this is a real vulnerability, not a false positive",
            report_tips=[
                "Include tool output in report",
                "Add manual validation evidence",
                "Explain why tool finding is accurate",
                "Don't rely solely on tool detection"
            ]
        )

    def _generate_next_steps(self, tool_type: str, finding_type: str) -> List[str]:
        """Generate next steps for hunter"""
        return [
            "Understand what the tool found",
            f"Manually verify this is a real {finding_type}",
            "Document your validation findings",
            "Assess business impact",
            "Prepare reproduction steps",
            "Create detailed proof of concept",
            "Write clear report with evidence",
            "Submit to bug bounty program"
        ]

    def explain_finding_reasoning(
        self,
        vulnerability_type: str,
        tool_evidence: Dict
    ) -> Dict:
        """
        Explain the reasoning behind a specific finding.
        
        Args:
            vulnerability_type: Type of vulnerability
            tool_evidence: Evidence from tool
            
        Returns:
            Dictionary with detailed reasoning
        """
        reasoning = {
            "vulnerability_type": vulnerability_type,
            "why_its_a_vulnerability": self._get_vulnerability_explanation(vulnerability_type),
            "how_tool_detected_it": self._get_detection_method(vulnerability_type, tool_evidence),
            "why_its_important": self._get_importance(vulnerability_type),
            "how_to_validate": self._get_validation_steps(vulnerability_type),
            "what_attacker_could_do": self._get_attacker_capabilities(vulnerability_type),
            "how_to_explain_in_report": self._get_report_explanation(vulnerability_type)
        }
        return reasoning

    def _get_vulnerability_explanation(self, vuln_type: str) -> str:
        """Get explanation of why something is a vulnerability"""
        explanations = {
            "xss": "XSS is a vulnerability because JavaScript has access to all browser data and can perform actions on behalf of users. An attacker can steal cookies, capture input, modify pages, or redirect users.",
            "sqli": "SQL Injection is critical because it allows attackers to manipulate database queries. They can extract all data, modify records, delete data, or potentially execute system commands.",
            "idor": "IDOR is dangerous because it bypasses authorization checks. Attackers can access data they shouldn't have permission for, affecting all users of the system.",
            "auth_bypass": "Authentication bypass completely defeats security controls. Attackers can access the system as anyone, including administrators, compromising all user data.",
            "ssrf": "SSRF is critical because it allows the server to make requests to internal systems. This can expose cloud credentials, internal services, or enable lateral movement.",
            "file_upload": "Insecure file upload can lead to remote code execution if attackers upload malicious code that gets executed by the server.",
            "api": "API vulnerabilities expose data or functionality to unauthorized access. Without proper authentication/authorization, all data is exposed."
        }
        return explanations.get(vuln_type.lower(), f"{vuln_type} is a security vulnerability that could be exploited by attackers")

    def _get_detection_method(self, vuln_type: str, evidence: Dict) -> str:
        """Get explanation of how tool detected vulnerability"""
        return f"Tool detected {vuln_type} by analyzing {evidence.get('method', 'the target')} and finding {evidence.get('indicator', 'security weakness')}"

    def _get_importance(self, vuln_type: str) -> str:
        """Get explanation of why vulnerability is important"""
        importance = {
            "xss": "Very important - allows account takeover and data theft",
            "sqli": "Critical - allows complete database access",
            "idor": "Very important - affects all users",
            "auth_bypass": "Critical - compromises all accounts",
            "ssrf": "Very important - enables internal system access",
            "file_upload": "Very important - can lead to code execution",
            "api": "Important - exposes sensitive data or functionality"
        }
        return importance.get(vuln_type.lower(), f"{vuln_type} is an important security issue")

    def _get_validation_steps(self, vuln_type: str) -> List[str]:
        """Get steps to manually validate vulnerability"""
        validation = {
            "xss": [
                "Test the vulnerable parameter with a simple probe",
                "Verify JavaScript executes in browser",
                "Check if payload is encoded or filtered",
                "Determine if vulnerability is persistent"
            ],
            "sqli": [
                "Test with SQL injection payload",
                "Observe error message or response difference",
                "Determine what data is accessible",
                "Test with different payloads"
            ],
            "idor": [
                "Access own resource first",
                "Try accessing other users' resources",
                "Verify authorization is bypassed",
                "Document exact permission bypass"
            ]
        }
        return validation.get(vuln_type.lower(), ["Manually verify the vulnerability exists", "Document evidence"])

    def _get_attacker_capabilities(self, vuln_type: str) -> str:
        """Explain what attackers could do with vulnerability"""
        capabilities = {
            "xss": "Steal user sessions, capture credentials, spread malware, modify page content, redirect users, steal sensitive data",
            "sqli": "Extract all user data, modify database records, delete data, potentially execute system commands",
            "idor": "Access all users' data, modify or delete others' data, potentially escalate privileges",
            "auth_bypass": "Impersonate any user, access admin functions, access all data, modify system settings",
            "ssrf": "Access internal systems, steal cloud credentials, perform lateral movement, access databases",
            "file_upload": "Execute code on server, create backdoors, modify website content",
            "api": "Access all exposed data, manipulate functionality, potentially abuse system"
        }
        return capabilities.get(vuln_type.lower(), "Exploit the system in harmful ways")

    def _get_report_explanation(self, vuln_type: str) -> str:
        """Get guidance on explaining vulnerability in report"""
        explanations = {
            "xss": "Explain which parameter is vulnerable, show that JavaScript executes, explain what data could be stolen (cookies, sessionStorage, etc)",
            "sqli": "Show the vulnerable parameter, explain which query is affected, show what data can be extracted",
            "idor": "Show you can access other users' data, explain which authorization check is missing",
            "auth_bypass": "Explain how authentication is bypassed, show what you can access without auth",
            "ssrf": "Show server makes requests to attacker URLs, explain internal systems that could be accessed",
            "file_upload": "Show files can be uploaded with wrong types, explain if they execute",
            "api": "Show endpoints accessible without auth/authorization, explain what data is exposed"
        }
        return explanations.get(vuln_type.lower(), "Clearly explain the vulnerability and its impact")

    def summarize_tool_output(
        self,
        tool_type: str,
        raw_output: str,
        max_lines: int = 100
    ) -> str:
        """
        Summarize tool output for hunter-friendly digest.
        
        Args:
            tool_type: Type of tool
            raw_output: Raw tool output
            max_lines: Maximum lines to keep
            
        Returns:
            Hunter-friendly summary
        """
        lines = raw_output.split('\n')
        
        # Extract key findings
        key_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in [
                "found", "vulnerable", "alert", "error", "critical", 
                "high", "xss", "sqli", "idor", "auth", "bypass"
            ]):
                key_lines.append(line.strip())
        
        # Create summary
        summary = f"=== {tool_type.upper()} Output Summary ===\n"
        summary += f"Total output lines: {len(lines)}\n"
        summary += f"Key findings: {len(key_lines)}\n\n"
        summary += "Key Information:\n"
        summary += "\n".join(key_lines[:20])  # Top 20 key lines
        
        return summary

    def suggest_validation_approach(
        self,
        finding_type: str,
        tool_output: Dict
    ) -> Dict:
        """
        Suggest how to manually validate tool findings.
        
        Args:
            finding_type: Type of finding
            tool_output: Tool output data
            
        Returns:
            Validation approach with specific steps
        """
        return {
            "finding_type": finding_type,
            "tool_confidence": tool_output.get("confidence", "unknown"),
            "false_positive_risk": self._assess_false_positive_risk(finding_type),
            "validation_difficulty": self._assess_validation_difficulty(finding_type),
            "validation_steps": self._get_validation_steps(finding_type),
            "what_to_capture": self._get_evidence_guidance(finding_type),
            "ready_to_report": self._should_report_immediately(finding_type)
        }

    def _assess_false_positive_risk(self, finding_type: str) -> str:
        """Assess likelihood of false positive"""
        high_fp_risk = ["xss", "generic_error"]
        medium_fp_risk = ["file_found", "directory"]
        low_fp_risk = ["sqli", "rce", "auth_bypass"]
        
        if finding_type.lower() in high_fp_risk:
            return "High - Manual verification strongly recommended"
        elif finding_type.lower() in medium_fp_risk:
            return "Medium - Manual verification recommended"
        else:
            return "Low - Tool finding likely accurate"

    def _assess_validation_difficulty(self, finding_type: str) -> str:
        """Assess how hard it is to validate manually"""
        easy = ["directory", "file_found", "version_detected"]
        medium = ["xss", "open_redirect"]
        hard = ["sqli", "race_condition"]
        
        if finding_type.lower() in easy:
            return "Easy - Just access the URL"
        elif finding_type.lower() in medium:
            return "Medium - Requires testing skills"
        else:
            return "Hard - May require specialized knowledge"

    def _get_evidence_guidance(self, finding_type: str) -> List[str]:
        """Get guidance on what evidence to capture"""
        guidance = {
            "xss": ["HTTP request", "HTTP response", "Browser screenshot", "Console output"],
            "sqli": ["HTTP request", "Error message", "Database response", "Data extracted"],
            "directory": ["URL", "Screenshot", "Content listing if available"],
            "file_found": ["File URL", "File contents", "Sensitivity assessment"]
        }
        return guidance.get(finding_type.lower(), ["Screenshot", "HTTP request", "Response data"])

    def _should_report_immediately(self, finding_type: str) -> bool:
        """Should this be reported immediately or validated first?"""
        report_immediately = ["auth_bypass", "rce", "sqli"]
        return finding_type.lower() in report_immediately
