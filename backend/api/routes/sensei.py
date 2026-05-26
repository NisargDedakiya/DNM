"""
Sensei API Routes
FastAPI endpoints for AI-powered hunter mentorship system.
All endpoints require JWT authentication and organization context.
"""

import logging
from typing import Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body

from backend.auth.dependencies import get_current_user, verify_organization
from backend.auth.jwt_handler import verify_jwt_token
from backend.core.permissions import Permission, require_permission
from backend.services.sensei_service import SenseiService
from backend.ai.client import ClaudeClient
from backend.database.session import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Initialize router and service
router = APIRouter(prefix="/sensei", tags=["Sensei Mentorship"])
sensei_service = SenseiService(claude_client=ClaudeClient())


# ==================== LEARNING & GUIDANCE ====================

@router.post("/guide")
async def get_verification_guide(
    request: Dict = Body(...),
    current_user: Dict = Depends(get_current_user),
    organization_id: str = Query(...),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Generate step-by-step verification guide for a vulnerability type.
    Educational content to teach proper validation methodology.
    
    Args:
        request: {
            "vulnerability_type": "xss|idor|ssrf|auth_bypass|api|file_upload|logic_flaw",
            "finding_description": "Description of the vulnerability",
            "user_level": "beginner|intermediate|advanced" (optional, defaults to intermediate)
        }
        current_user: Authenticated user
        organization_id: Organization context
        db: Database session
        
    Returns:
        Verification guide with step-by-step instructions, checks, evidence types, safety notes
        
    Raises:
        401: Unauthorized
        403: Forbidden (organization mismatch)
        422: Invalid request
    """
    try:
        # Verify organization
        verify_organization(current_user, organization_id, db)
        
        # Extract request parameters
        vulnerability_type = request.get("vulnerability_type", "").lower()
        finding_description = request.get("finding_description", "")
        user_level = request.get("user_level", "intermediate").lower()
        
        if not vulnerability_type or not finding_description:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="vulnerability_type and finding_description are required"
            )
        
        # Generate guidance
        guidance = await sensei_service.generate_learning_guidance(
            vulnerability_type=vulnerability_type,
            finding_description=finding_description,
            user_level=user_level,
            organization_id=organization_id
        )
        
        logger.info(f"Generated verification guide for {vulnerability_type} (org: {organization_id})")
        
        return {
            "success": True,
            "data": guidance,
            "message": f"Verification guide generated for {vulnerability_type}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating verification guide: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification guide"
        )


# ==================== VERIFICATION WORKFLOWS ====================

@router.post("/verify")
async def start_verification_workflow(
    request: Dict = Body(...),
    current_user: Dict = Depends(get_current_user),
    organization_id: str = Query(...),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Initialize guided verification workflow for a finding.
    Provides step-by-step verification checkpoints and evidence tracking.
    
    Args:
        request: {
            "finding_id": "UUID of finding",
            "vulnerability_type": "Type of vulnerability",
            "finding_description": "Description"
        }
        current_user: Authenticated user
        organization_id: Organization context
        db: Database session
        
    Returns:
        Verification workflow with checkpoints and guidance
        
    Raises:
        401: Unauthorized
        403: Forbidden
        404: Finding not found
        422: Invalid request
    """
    try:
        # Verify organization
        verify_organization(current_user, organization_id, db)
        
        # Extract parameters
        finding_id = request.get("finding_id")
        vulnerability_type = request.get("vulnerability_type", "").lower()
        finding_description = request.get("finding_description", "")
        
        if not finding_id or not vulnerability_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="finding_id and vulnerability_type are required"
            )
        
        # Verify finding exists and belongs to organization
        finding = db.query(Finding).filter(
            Finding.id == finding_id,
            Finding.organization_id == organization_id
        ).first()
        
        if not finding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding not found or unauthorized"
            )
        
        # Start verification workflow
        workflow = await sensei_service.assist_manual_verification(
            finding_id=finding_id,
            vulnerability_type=vulnerability_type,
            finding_description=finding_description,
            organization_id=organization_id
        )
        
        logger.info(f"Started verification workflow for finding {finding_id} (org: {organization_id})")
        
        return {
            "success": True,
            "data": workflow,
            "message": "Verification workflow started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting verification workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start verification workflow"
        )


# ==================== MISTAKE ANALYSIS ====================

@router.post("/analyze-mistake")
async def analyze_rejection(
    request: Dict = Body(...),
    current_user: Dict = Depends(get_current_user),
    organization_id: str = Query(...),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Analyze a report rejection to help hunter improve.
    Educational feedback on what went wrong and how to fix it.
    
    Args:
        request: {
            "rejection_reason": "Reason provided by program",
            "finding_details": {
                "finding_id": "ID",
                "title": "Finding title",
                "severity": "Severity",
                "description": "Description",
                "...": "Other fields"
            }
        }
        current_user: Authenticated user
        organization_id: Organization context
        db: Database session
        
    Returns:
        Rejection analysis with identified mistakes and improvements
        
    Raises:
        401: Unauthorized
        403: Forbidden
        422: Invalid request
    """
    try:
        # Verify organization
        verify_organization(current_user, organization_id, db)
        
        # Extract parameters
        rejection_reason = request.get("rejection_reason", "")
        finding_details = request.get("finding_details", {})
        
        if not rejection_reason or not finding_details:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="rejection_reason and finding_details are required"
            )
        
        # Analyze rejection
        analysis = sensei_service.analyze_rejection(
            rejection_reason=rejection_reason,
            finding_details=finding_details,
            organization_id=organization_id
        )
        
        logger.info(f"Analyzed rejection for organization {organization_id}")
        
        return {
            "success": True,
            "data": analysis,
            "message": "Rejection analysis complete - review recommendations to improve future reports"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing rejection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze rejection"
        )


# ==================== OUTPUT EXPLANATION ====================

@router.post("/explain-output")
async def explain_tool_output(
    request: Dict = Body(...),
    current_user: Dict = Depends(get_current_user),
    organization_id: str = Query(...),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Explain security tool output in hunter-friendly language.
    Helps hunters understand what tools found and what it means.
    
    Args:
        request: {
            "tool_type": "nuclei|dalfox|sqlmap|ffuf|burp|nmap|manual",
            "output": {
                "finding_type": "xss|sqli|etc",
                "severity": "High",
                "...": "Other tool-specific fields"
            },
            "raw_output": "Raw tool output text (optional)"
        }
        current_user: Authenticated user
        organization_id: Organization context
        db: Database session
        
    Returns:
        Hunter-friendly explanation of tool findings
        
    Raises:
        401: Unauthorized
        403: Forbidden
        422: Invalid request
    """
    try:
        # Verify organization
        verify_organization(current_user, organization_id, db)
        
        # Extract parameters
        tool_type = request.get("tool_type", "").lower()
        output = request.get("output", {})
        raw_output = request.get("raw_output", None)
        
        if not tool_type or not output:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tool_type and output are required"
            )
        
        # Explain output
        explanation = sensei_service.explain_tool_output(
            tool_type=tool_type,
            output=output,
            raw_output=raw_output,
            organization_id=organization_id
        )
        
        logger.info(f"Explained {tool_type} output for organization {organization_id}")
        
        return {
            "success": True,
            "data": explanation,
            "message": f"Explanation of {tool_type} findings generated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error explaining tool output: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to explain tool output"
        )


# ==================== FINDING EXPLANATION ====================

@router.post("/explain-finding")
async def explain_finding(
    finding_id: str = Query(...),
    current_user: Dict = Depends(get_current_user),
    organization_id: str = Query(...),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get comprehensive explanation of a finding.
    Helps hunter understand why it's a vulnerability and how to validate it.
    
    Args:
        finding_id: UUID of finding to explain
        current_user: Authenticated user
        organization_id: Organization context
        db: Database session
        
    Returns:
        Comprehensive finding explanation
        
    Raises:
        401: Unauthorized
        403: Forbidden
        404: Finding not found
    """
    try:
        # Verify organization
        verify_organization(current_user, organization_id, db)
        
        # Get finding from database
        finding = db.query(Finding).filter(
            Finding.id == finding_id,
            Finding.organization_id == organization_id
        ).first()
        
        if not finding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding not found or unauthorized"
            )
        
        # Prepare finding data
        finding_data = {
            "id": finding.id,
            "title": finding.title,
            "description": finding.description,
            "vulnerability_type": finding.vulnerability_type,
            "severity": finding.severity,
            "tool_evidence": finding.tool_evidence or {},
            "tool_output": finding.tool_output or {}
        }
        
        # Explain finding
        explanation = await sensei_service.explain_finding(
            finding=finding_data,
            organization_id=organization_id
        )
        
        logger.info(f"Explained finding {finding_id} for organization {organization_id}")
        
        return {
            "success": True,
            "data": explanation,
            "message": "Finding explanation generated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error explaining finding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to explain finding"
        )


# ==================== REPORT QUALITY ANALYSIS ====================

@router.post("/analyze-report-quality")
async def analyze_report_quality(
    request: Dict = Body(...),
    current_user: Dict = Depends(get_current_user),
    organization_id: str = Query(...),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Analyze report for quality issues before submission.
    Proactive feedback to improve report quality and acceptance probability.
    
    Args:
        request: {
            "title": "Report title",
            "content": "Full report text",
            "vulnerability_type": "Type",
            "severity": "Severity",
            "metadata": {...}
        }
        current_user: Authenticated user
        organization_id: Organization context
        db: Database session
        
    Returns:
        Quality analysis with improvements and acceptance probability
        
    Raises:
        401: Unauthorized
        403: Forbidden
        422: Invalid request
    """
    try:
        # Verify organization
        verify_organization(current_user, organization_id, db)
        
        # Extract parameters
        report_data = request.get("report_data", {})
        
        if not report_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="report_data is required"
            )
        
        # Analyze quality
        quality_analysis = await sensei_service.analyze_report_quality_issues(
            report_data=report_data,
            organization_id=organization_id
        )
        
        logger.info(f"Analyzed report quality for organization {organization_id}")
        
        return {
            "success": True,
            "data": quality_analysis,
            "message": "Report quality analysis complete"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing report quality: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze report quality"
        )


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def health_check(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Health check for Sensei service.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "sensei_mentorship",
        "version": "1.0.0"
    }


@router.get("/verify/{finding_id}")
async def get_verification_wizard(
    finding_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
        
    org_id = str(finding.organization_id) if finding.organization_id else ""
    if not org_id:
        from backend.models.program import Program
        program = db.query(Program).filter(Program.id == finding.program_id).first()
        org_id = str(program.organization_id) if program else ""
        
    vuln_type = getattr(finding, 'vulnerability_type', None) or "xss"
    
    workflow = await sensei_service.assist_manual_verification(
        finding_id=finding_id,
        vulnerability_type=vuln_type,
        finding_description=finding.description or "",
        organization_id=org_id
    )
    return workflow


class ManualGuideRequest(Body):
    bug_type: str
    program_id: UUID


class ExplainRequest(Body):
    lines: list[str]
    tool: str


@router.post("/verify/{finding_id}")
async def generate_verification_recipe(
    finding_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from backend.ai.sensei.verification_wizard import verification_wizard
    try:
        res = await verification_wizard.generate(db, finding_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual-guide")
async def generate_manual_guide(
    body: Dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bug_type = body.get("bug_type")
    program_id = body.get("program_id")
    if not bug_type or not program_id:
        raise HTTPException(status_code=422, detail="bug_type and program_id are required")
    from backend.ai.sensei.manual_guide import manual_guide
    try:
        res = await manual_guide.generate(db, bug_type, UUID(program_id))
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain")
async def explain_tool_output(
    body: Dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    lines = body.get("lines")
    tool = body.get("tool")
    if not isinstance(lines, list) or not tool:
        raise HTTPException(status_code=422, detail="lines (list) and tool (str) are required")
    from backend.ai.sensei.output_explainer import output_explainer
    try:
        res = await output_explainer.explain(lines, tool)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Make sure Finding model is imported (add at top if needed)
from backend.models import Finding
from backend.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


