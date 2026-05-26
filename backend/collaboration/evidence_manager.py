"""
Evidence artifact management for investigations.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events import EventType
from backend.models.evidence_item import EvidenceItem
from backend.models.investigation import Investigation
from backend.services.event_service import event_service


async def upload_evidence(
    db: AsyncSession,
    investigation_id: UUID,
    file_path: str,
    description: str,
    uploaded_by: UUID,
    evidence_type: str = "note",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a new evidence artifact and compute an integrity checksum."""
    investigation = await db.get(Investigation, investigation_id)
    if not investigation:
        raise ValueError("investigation not found")

    checksum = _checksum_for_path(file_path)
    current_version = await _next_version(db, investigation_id)
    evidence = EvidenceItem(
        investigation_id=investigation_id,
        file_path=file_path,
        description=description,
        uploaded_by=uploaded_by,
        evidence_type=evidence_type,
        checksum=checksum,
        version=current_version,
        metadata_=metadata or {},
    )
    db.add(evidence)
    await db.flush()

    payload = {
        "investigation_id": str(investigation_id),
        "evidence_id": str(evidence.id),
        "file_path": file_path,
        "description": description,
        "uploaded_by": str(uploaded_by),
        "evidence_type": evidence_type,
        "checksum": checksum,
        "version": current_version,
    }
    await event_service.emit_event(EventType.INVESTIGATION_EVIDENCE_UPLOADED, str(investigation.organization_id), payload)
    return payload


async def attach_evidence(
    db: AsyncSession,
    investigation_id: UUID,
    evidence_id: UUID,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a versioned attachment record from an existing evidence item."""
    source = await db.get(EvidenceItem, evidence_id)
    if not source:
        raise ValueError("evidence not found")

    current_version = await _next_version(db, investigation_id)
    attached = EvidenceItem(
        investigation_id=investigation_id,
        file_path=source.file_path,
        description=description or source.description,
        uploaded_by=source.uploaded_by,
        evidence_type=source.evidence_type,
        checksum=source.checksum,
        version=current_version,
        parent_evidence_id=source.id,
        metadata_=metadata or source.metadata_ or {},
    )
    db.add(attached)
    await db.flush()
    return {
        "evidence_id": str(attached.id),
        "parent_evidence_id": str(source.id),
        "investigation_id": str(investigation_id),
        "version": current_version,
        "checksum": attached.checksum,
    }


async def retrieve_evidence(db: AsyncSession, investigation_id: UUID) -> list[dict[str, Any]]:
    """Return versioned evidence artifacts for an investigation."""
    result = await db.execute(
        select(EvidenceItem).where(EvidenceItem.investigation_id == investigation_id).order_by(EvidenceItem.version.asc(), EvidenceItem.created_at.asc())
    )
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "investigation_id": str(item.investigation_id),
            "file_path": item.file_path,
            "description": item.description,
            "uploaded_by": str(item.uploaded_by),
            "evidence_type": item.evidence_type,
            "checksum": item.checksum,
            "version": item.version,
            "parent_evidence_id": str(item.parent_evidence_id) if item.parent_evidence_id else None,
            "metadata": item.metadata_ or {},
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


def _checksum_for_path(file_path: str) -> str:
    path = Path(file_path)
    if path.exists() and path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()
    return hashlib.sha256(file_path.encode("utf-8")).hexdigest()


async def _next_version(db: AsyncSession, investigation_id: UUID) -> int:
    result = await db.execute(select(EvidenceItem.version).where(EvidenceItem.investigation_id == investigation_id).order_by(EvidenceItem.version.desc()).limit(1))
    latest = result.scalar_one_or_none()
    return int(latest or 0) + 1
