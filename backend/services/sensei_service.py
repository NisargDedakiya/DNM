"""
Sensei Service
Orchestrates AI mentorship workflows for hunter education and verification.
Main service integrating all sensei modules.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from backend.ai.client import ClaudeClient
from backend.ai.sensei.manual_guide import ManualGuide
from backend.ai.sensei.verification_wizard import VerificationWizard
from backend.ai.sensei.mistake_analyzer import MistakeAnalyzer
from backend.ai.sensei.output_explainer import OutputExplainer
from backend.core.permissions import Permission
from backend.models import Finding, Organization

logger = logging.getLogger(__name__)


class SenseiService:
    """
    AI-powered mentorship service for bug bounty hunters.
    Provides guidance, verification assistance, mistake analysis, and tool explanations.
    """

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        """
        Initialize Sensei service.
        
        Args:
            claude_client: Claude AI client for advanced guidance
        """
        self.claude_client = claude_client
        self.manual_guide = ManualGuide()
        self.verification_wizard = VerificationWizard()
        self.mistake_analyzer = MistakeAnalyzer()
        self.output_explainer = OutputExplainer()

    async def generate_learning_guidance(
        self,
        vulnerability_type: str,
        finding_description: str,
        user_level: str = "intermediate",
        organization_id: Optional[str] = None
    ) -> Dict:
        """
        Generate learning guidance for a vulnerability type.
        Educational content to help hunters understand and validate findings.
        
        Args:
            vulnerability_type: Type of vulnerability
            finding_description: Description of the finding
            user_level: Hunter skill level (beginner/intermediate/advanced)
            organization_id: Organization context for isolation
            
        Returns:
            Dictionary with comprehensive learning guidance
        """
        logger.info(f"Generating learning guidance for {vulnerability_type}")
        
        # Generate verification guide
        verification_guide = self.manual_guide.generate_verification_guide(
            vulnerability_type,
            finding_description,
            finding_description,
            "High"
        )
        
        # Generate vulnerability explanation
        vuln_explanation = self.manual_guide.explain_bug_category(vulnerability_type)
        
        # Generate manual checks
        manual_checks = self.manual_guide.recommend_manual_checks(vulnerability_type)
        
        # Tailor guidance to skill level
        guidance_level = self._tailor_guidance_to_level(user_level, verification_guide)
        
        # Use Claude for enhanced explanation if available
        claude_enhancement = None
        if self.claude_client:
            try:
                claude_enhancement = await self._get_claude_learning_enhancement(
                    vulnerability_type,
                    finding_description,
                    user_level
                )
            except Exception as e:
                logger.warning(f"Claude enhancement failed: {e}")
        
        return {
            "vulnerability_type": vulnerability_type,
            "user_level": user_level,
            "organization_id": organization_id,
            "verification_guide": {
                "title": verification_guide.vulnerability_type,
                "severity": verification_guide.severity,
                "impact": verification_guide.impact_explanation,
                "business_impact": verification_guide.business_impact,
                "steps": [
                    {
                        "step": step.step_number,
                        "title": step.title,
                        "description": step.description,
                        "key_checks": step.key_checks,
                        "evidence_to_collect": step.evidence_to_collect,
                        "common_mistakes": step.common_mistakes,
                        "safety_notes": step.safety_notes
                    }
                    for step in verification_guide.steps
                ],
                "validation_tips": verification_guide.validation_tips,
                "evidence_quality_guide": verification_guide.evidence_quality_guide,
                "report_tips": verification_guide.report_tips
            },
            "vulnerability_explanation": vuln_explanation,
            "manual_checks": manual_checks,
            "claude_enhancement": claude_enhancement,
            "generated_at": datetime.utcnow().isoformat()
        }

    async def assist_manual_verification(
        self,
        finding_id: str,
        vulnerability_type: str,
        finding_description: str,
        organization_id: str
    ) -> Dict:
        """
        Initiate guided manual verification workflow.
        
        Args:
            finding_id: ID of finding to verify
            vulnerability_type: Type of vulnerability
            finding_description: Description of finding
            organization_id: Organization context
            
        Returns:
            Dictionary with verification workflow
        """
        logger.info(f"Starting verification workflow for finding {finding_id}")
        
        # Initialize verification workflow
        workflow = self.verification_wizard.start_verification_workflow(
            finding_id,
            vulnerability_type,
            "High"  # Default severity
        )
        
        # Generate verification steps
        steps = self.verification_wizard.generate_verification_steps(
            vulnerability_type,
            finding_description
        )
        
        return {
            "workflow_id": workflow.workflow_id,
            "finding_id": finding_id,
            "status": workflow.status.value,
            "vulnerability_type": vulnerability_type,
            "organization_id": organization_id,
            "checkpoints_total": len(workflow.checkpoints),
            "checkpoints": [
                {
                    "id": cp.checkpoint_id,
                    "title": cp.title,
                    "description": cp.description,
                    "required": cp.required,
                    "expected_findings": cp.expected_findings,
                    "evidence_needed": [et.value for et in cp.required_evidence_types]
                }
                for cp in workflow.checkpoints
            ],
            "verification_steps": steps,
            "completeness": f"{workflow.completeness_score * 100:.1f}%"
        }

    async def explain_finding(
        self,
        finding: Dict,
        organization_id: str
    ) -> Dict:
        """
        Provide AI-assisted explanation of a finding.
        Helps hunter understand why it's a vulnerability.
        
        Args:
            finding: Finding details
            organization_id: Organization context
            
        Returns:
            Dictionary with comprehensive explanation
        """
        logger.info(f"Explaining finding: {finding.get('title', 'unknown')}")
        
        vulnerability_type = finding.get("vulnerability_type", "unknown")
        
        # Get reasoning
        reasoning = self.output_explainer.explain_finding_reasoning(
            vulnerability_type,
            finding.get("tool_evidence", {})
        )
        
        # Use Claude for advanced explanation if available
        claude_explanation = None
        if self.claude_client:
            try:
                claude_explanation = await self._get_claude_finding_explanation(finding)
            except Exception as e:
                logger.warning(f"Claude explanation failed: {e}")
        
        return {
            "finding_id": finding.get("id"),
            "vulnerability_type": vulnerability_type,
            "organization_id": organization_id,
            "reasoning": reasoning,
            "claude_explanation": claude_explanation,
            "validation_approach": self.output_explainer.suggest_validation_approach(
                vulnerability_type,
                finding.get("tool_output", {})
            ),
            "generated_at": datetime.utcnow().isoformat()
        }

    async def analyze_report_quality_issues(
        self,
        report_data: Dict,
        organization_id: str
    ) -> Dict:
        """
        Analyze report for quality issues before submission.
        Proactive mistake prevention.
        
        Args:
            report_data: Report content and metadata
            organization_id: Organization context
            
        Returns:
            Dictionary with quality analysis and recommendations
        """
        logger.info(f"Analyzing report quality for organization {organization_id}")
        
        # Get improvement recommendations
        improvements = self.mistake_analyzer.recommend_improvements(report_data)
        
        # Detect common mistakes
        mistakes = self.mistake_analyzer.detect_common_mistakes(
            report_data.get("content", ""),
            report_data.get("metadata", {})
        )
        
        # Use Claude for advanced feedback if available
        claude_feedback = None
        if self.claude_client:
            try:
                claude_feedback = await self._get_claude_report_feedback(report_data)
            except Exception as e:
                logger.warning(f"Claude feedback failed: {e}")
        
        return {
            "organization_id": organization_id,
            "quality_improvements": improvements,
            "common_mistakes_detected": mistakes,
            "claude_feedback": claude_feedback,
            "estimated_acceptance_probability": self._estimate_acceptance_probability(
                improvements,
                mistakes
            ),
            "ready_to_submit": mistakes["ready_for_submission"],
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

    def analyze_rejection(
        self,
        rejection_reason: str,
        finding_details: Dict,
        organization_id: str
    ) -> Dict:
        """
        Analyze a report rejection to help hunter improve.
        Educational feedback on what went wrong.
        
        Args:
            rejection_reason: Reason provided by program
            finding_details: Details of the rejected finding
            organization_id: Organization context
            
        Returns:
            Dictionary with rejection analysis and improvement guidance
        """
        logger.info(f"Analyzing rejection for organization {organization_id}")
        
        # Analyze rejection
        analysis = self.mistake_analyzer.analyze_rejection_reason(
            rejection_reason,
            finding_details
        )
        
        return {
            "finding_id": analysis.finding_id,
            "organization_id": organization_id,
            "original_title": analysis.original_title,
            "rejection_reason": analysis.rejection_reason,
            "detected_mistakes": [m.value for m in analysis.detected_mistakes],
            "mistake_explanations": analysis.mistake_explanations,
            "improvements_recommended": analysis.improvements_recommended,
            "severity_estimate": analysis.severity_estimate,
            "resubmission_guidance": analysis.resubmission_guidance,
            "learning_resources": self._generate_learning_resources(analysis),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

    def explain_tool_output(
        self,
        tool_type: str,
        output: Dict,
        raw_output: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Dict:
        """
        Explain tool output in hunter-friendly language.
        
        Args:
            tool_type: Type of security tool
            output: Parsed tool output
            raw_output: Raw tool output text
            organization_id: Organization context
            
        Returns:
            Dictionary with hunter-friendly explanation
        """
        logger.info(f"Explaining {tool_type} output for organization {organization_id}")
        
        # Get explanation
        explanation = self.output_explainer.explain_scan_output(
            tool_type,
            output,
            raw_output
        )
        
        # Get summary
        summary = self.output_explainer.summarize_tool_output(
            tool_type,
            raw_output or ""
        )
        
        return {
            "tool_type": tool_type,
            "organization_id": organization_id,
            "finding_type": explanation.finding_type,
            "severity": explanation.severity,
            "explanation": explanation.explanation,
            "what_it_means": explanation.what_it_means,
            "why_it_matters": explanation.why_it_matters,
            "next_steps": explanation.next_steps,
            "validation_guidance": explanation.validation_guidance,
            "report_tips": explanation.report_tips,
            "summary": summary,
            "generated_at": datetime.utcnow().isoformat()
        }

    async def _get_claude_learning_enhancement(
        self,
        vulnerability_type: str,
        finding_description: str,
        user_level: str
    ) -> Optional[Dict]:
        """Get Claude AI enhancement for learning guidance"""
        if not self.claude_client:
            return None
        
        prompt = f"""
        Provide learning enhancement for a bug bounty hunter learning about {vulnerability_type}.
        
        Finding: {finding_description}
        Hunter skill level: {user_level}
        
        Provide:
        1. Real-world example of how this vulnerability was exploited
        2. Key validation technique this hunter might miss
        3. Common false positive with this vulnerability type
        4. One pro tip for efficient testing
        
        Keep response concise and educational, not exploitative.
        """
        
        try:
            response = await self.claude_client.create_message(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                temperature=0.7,
                system="You are an expert bug bounty mentor teaching secure vulnerability testing and validation.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "enhancement": response,
                "source": "claude_ai"
            }
        except Exception as e:
            logger.error(f"Claude enhancement error: {e}")
            return None

    async def _get_claude_finding_explanation(self, finding: Dict) -> Optional[Dict]:
        """Get Claude AI explanation for a finding"""
        if not self.claude_client:
            return None
        
        prompt = f"""
        Explain why this is a security vulnerability and what an attacker could do with it.
        
        Finding: {finding.get('title', 'Unknown')}
        Type: {finding.get('vulnerability_type', 'Unknown')}
        Description: {finding.get('description', '')}
        
        Explain:
        1. Why this is a vulnerability (technical reason)
        2. Real-world business impact
        3. What data/systems are at risk
        4. What the attacker's goal would be
        
        Keep explanation educational and security-focused, not exploitative.
        """
        
        try:
            response = await self.claude_client.create_message(
                model="claude-3-5-sonnet-20241022",
                max_tokens=600,
                temperature=0.5,
                system="You are a security expert explaining vulnerabilities clearly and accurately.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "explanation": response,
                "source": "claude_ai"
            }
        except Exception as e:
            logger.error(f"Claude explanation error: {e}")
            return None

    async def _get_claude_report_feedback(self, report_data: Dict) -> Optional[Dict]:
        """Get Claude AI feedback on report quality"""
        if not self.claude_client:
            return None
        
        prompt = f"""
        Review this bug bounty report for quality and completeness.
        
        Title: {report_data.get('title', 'Unknown')}
        Type: {report_data.get('vulnerability_type', 'Unknown')}
        Content Preview: {report_data.get('content', '')[:500]}...
        
        Provide:
        1. Overall quality assessment (1-10)
        2. Strongest part of the report
        3. Weakest part of the report
        4. One key improvement needed
        5. Probability of acceptance (percentage)
        
        Keep feedback constructive and specific.
        """
        
        try:
            response = await self.claude_client.create_message(
                model="claude-3-5-sonnet-20241022",
                max_tokens=400,
                temperature=0.5,
                system="You are an experienced bug bounty program manager reviewing vulnerability reports.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "feedback": response,
                "source": "claude_ai"
            }
        except Exception as e:
            logger.error(f"Claude feedback error: {e}")
            return None

    def _tailor_guidance_to_level(self, user_level: str, guide) -> Dict:
        """Tailor guidance content to user skill level"""
        if user_level == "beginner":
            return {
                "complexity": "simplified",
                "steps_to_include": 3,  # First 3 steps only
                "include_definitions": True,
                "include_common_mistakes": True
            }
        elif user_level == "advanced":
            return {
                "complexity": "detailed",
                "steps_to_include": len(guide.steps),  # All steps
                "include_definitions": False,
                "include_advanced_techniques": True
            }
        else:  # intermediate
            return {
                "complexity": "balanced",
                "steps_to_include": len(guide.steps),
                "include_definitions": False,
                "include_common_mistakes": True
            }

    def _estimate_acceptance_probability(
        self,
        improvements: Dict,
        mistakes: Dict
    ) -> float:
        """Estimate probability of acceptance based on analysis"""
        issues_count = len(improvements.get("improvements", []))
        mistakes_count = mistakes.get("mistakes_detected", 0)
        
        # Start at 85% if no issues
        probability = 85.0
        
        # Deduct for issues
        probability -= (issues_count * 10)
        probability -= (mistakes_count * 15)
        
        # Ensure within 0-100 range
        return max(0, min(100, probability))

    def _generate_learning_resources(self, analysis) -> List[str]:
        """Generate learning resources based on mistakes"""
        resources = []
        
        for mistake in analysis.detected_mistakes:
            if "duplicate" in mistake.value:
                resources.append("Resource: How to search for duplicate reports")
            elif "impact" in mistake.value:
                resources.append("Resource: Explaining business impact effectively")
            elif "reproduction" in mistake.value:
                resources.append("Resource: Writing clear reproduction steps")
            elif "evidence" in mistake.value:
                resources.append("Resource: Collecting sufficient evidence")
        
        return resources if resources else ["Resource: General report improvement guide"]
