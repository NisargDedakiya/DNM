"""
Dashboard analytics service.

Provides async aggregation queries and analytics per user.
"""
from __future__ import annotations

import logging
from typing import Dict, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.program import Program
from backend.models.scan import Scan, ScanStatus, ScanType
from backend.models.finding import Finding
from backend.models.report import Report

logger = logging.getLogger(__name__)


async def get_dashboard_stats(db: AsyncSession, user_id: str) -> Dict:
    # totals
    total_programs_q = select(func.count()).select_from(Program).where(Program.created_by == user_id)
    total_scans_q = select(func.count()).select_from(Scan).join(Program).where(Program.created_by == user_id)
    total_findings_q = select(func.count()).select_from(Finding).join(Program).where(Program.created_by == user_id)
    total_reports_q = select(func.count()).select_from(Report).join(Finding).join(Program).where(Program.created_by == user_id)

    res_prog = await db.execute(total_programs_q)
    res_scans = await db.execute(total_scans_q)
    res_find = await db.execute(total_findings_q)
    res_rep = await db.execute(total_reports_q)

    total_programs = int(res_prog.scalar() or 0)
    total_scans = int(res_scans.scalar() or 0)
    total_findings = int(res_find.scalar() or 0)
    total_reports = int(res_rep.scalar() or 0)

    # findings by severity
    sev_q = select(Finding.severity, func.count()).where(Finding.program.has(created_by == user_id)).group_by(Finding.severity)
    # Because of name collision, build with string compare
    sev_q = select(Finding.severity, func.count()).where(Finding.program.has(Program.created_by == user_id)).group_by(Finding.severity)
    sev_res = await db.execute(sev_q)
    rows = sev_res.all()
    findings_by_severity = {str(k.value if hasattr(k, 'value') else k): int(v) for k, v in rows}

    # active scans (pending/running)
    active_q = select(func.count()).select_from(Scan).join(Program).where(Program.created_by == user_id, Scan.status.in_([ScanStatus.pending, ScanStatus.running]))
    active_res = await db.execute(active_q)
    active_scans = int(active_res.scalar() or 0)

    # recent activity: latest findings and scans
    findings_q = select(Finding).where(Finding.program.has(Program.created_by == user_id)).order_by(Finding.created_at.desc()).limit(10)
    scans_q = select(Scan).join(Program).where(Program.created_by == user_id).order_by(Scan.created_at.desc()).limit(10)

    f_res = await db.execute(findings_q)
    s_res = await db.execute(scans_q)
    findings = f_res.scalars().all()
    scans = s_res.scalars().all()

    recent: List[Dict] = []
    for f in findings:
        recent.append({"type": "finding", "id": f.id, "title": f.title, "meta": {"severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity)}, "created_at": f.created_at})
    for s in scans:
        recent.append({"type": "scan", "id": s.id, "title": None, "meta": {"status": s.status.value if hasattr(s.status, 'value') else str(s.status), "type": s.scan_type.value if hasattr(s.scan_type, 'value') else str(s.scan_type)}, "created_at": s.created_at})

    # sort recent by created_at desc and trim
    recent_sorted = sorted(recent, key=lambda x: x["created_at"], reverse=True)[:20]

    return {
        "total_programs": total_programs,
        "total_scans": total_scans,
        "total_findings": total_findings,
        "total_reports": total_reports,
        "findings_by_severity": findings_by_severity,
        "active_scans": active_scans,
        "recent_activity": recent_sorted,
    }


async def get_findings_breakdown(db: AsyncSession, user_id: str) -> Dict[str, int]:
    q = select(Finding.severity, func.count()).where(Finding.program.has(Program.created_by == user_id)).group_by(Finding.severity)
    res = await db.execute(q)
    rows = res.all()
    return {str(k.value if hasattr(k, 'value') else k): int(v) for k, v in rows}


async def get_recent_activity(db: AsyncSession, user_id: str, limit: int = 20) -> List[Dict]:
    findings_q = select(Finding).where(Finding.program.has(Program.created_by == user_id)).order_by(Finding.created_at.desc()).limit(limit)
    scans_q = select(Scan).join(Program).where(Program.created_by == user_id).order_by(Scan.created_at.desc()).limit(limit)

    f_res = await db.execute(findings_q)
    s_res = await db.execute(scans_q)
    findings = f_res.scalars().all()
    scans = s_res.scalars().all()

    recent: List[Dict] = []
    for f in findings:
        recent.append({"type": "finding", "id": f.id, "title": f.title, "meta": {"severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity)}, "created_at": f.created_at})
    for s in scans:
        recent.append({"type": "scan", "id": s.id, "title": None, "meta": {"status": s.status.value if hasattr(s.status, 'value') else str(s.status), "type": s.scan_type.value if hasattr(s.scan_type, 'value') else str(s.scan_type)}, "created_at": s.created_at})

    recent_sorted = sorted(recent, key=lambda x: x["created_at"], reverse=True)[:limit]
    return recent_sorted


async def get_scan_statistics(db: AsyncSession, user_id: str) -> Dict:
    # counts by status
    q_status = select(Scan.status, func.count()).join(Program).where(Program.created_by == user_id).group_by(Scan.status)
    res_status = await db.execute(q_status)
    status_rows = res_status.all()
    counts_by_status = {str(k.value if hasattr(k, 'value') else k): int(v) for k, v in status_rows}

    # counts by type
    q_type = select(Scan.scan_type, func.count()).join(Program).where(Program.created_by == user_id).group_by(Scan.scan_type)
    res_type = await db.execute(q_type)
    type_rows = res_type.all()
    counts_by_type = {str(k.value if hasattr(k, 'value') else k): int(v) for k, v in type_rows}

    # avg duration for completed scans (seconds)
    # Use extract epoch over interval (completed_at - started_at)
    duration_expr = func.avg(func.extract('epoch', Scan.completed_at - Scan.started_at))
    q_avg = select(duration_expr).join(Program).where(Program.created_by == user_id, Scan.completed_at.isnot(None), Scan.started_at.isnot(None))
    res_avg = await db.execute(q_avg)
    avg_val = res_avg.scalar()
    avg_seconds = float(avg_val) if avg_val is not None else None

    return {
        "counts_by_status": counts_by_status,
        "counts_by_type": counts_by_type,
        "avg_duration_seconds": avg_seconds,
    }
