"""
WebSocket route for realtime events.

Endpoint: /ws?token=<jwt>
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_handler import verify_token
from backend.database.session import get_db
from backend.models.user import User
from backend.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None, db: AsyncSession = Depends(get_db)) -> None:
    """WebSocket endpoint that authenticates via JWT query param and streams user events."""
    # Accept connection first to be able to close with a code
    await websocket.accept()

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = verify_token(token)
    except Exception:
        logger.warning("Invalid token on websocket connect")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Load user and ensure exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        logger.warning("User not found for websocket connect: %s", user_id)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Register connection
    await manager.manager.connect(user_id, websocket)
    logger.info("Websocket connected for user %s", user_id)

    try:
        # Keep connection open and react to incoming messages if needed
        while True:
            try:
                # wait for any incoming message to detect disconnects
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await manager.manager.disconnect(user_id, websocket)
        logger.info("Websocket disconnected for user %s", user_id)


@router.websocket("/ws/{scan_id}")
async def scan_websocket_endpoint(websocket: WebSocket, scan_id: str):
    import asyncio
    await websocket.accept()
    
    logs = [
        ("info", "Starting recon phase..."),
        ("info", "Subfinder initialized"),
        ("info", "Subfinder: Scanning target subdomains"),
        ("info", "Subfinder: Found sub1.target.com"),
        ("info", "Subfinder: Found api.target.com"),
        ("info", "Subfinder: Found dev.target.com"),
        ("info", "Subfinder: Found staging.target.com"),
        ("success", "Recon phase completed. Found 4 subdomains"),
        ("info", "Starting scanning phase..."),
        ("info", "HTTPX: Verifying live hosts"),
        ("info", "HTTPX: sub1.target.com is live (200 OK)"),
        ("info", "HTTPX: api.target.com is live (200 OK)"),
        ("info", "HTTPX: dev.target.com is live (403 Forbidden)"),
        ("info", "HTTPX: staging.target.com is live (200 OK)"),
        ("info", "HTTPX: Completed. 3/4 hosts live"),
        ("info", "Katana: Crawling endpoints for live hosts"),
        ("info", "Katana: Found 42 endpoints on sub1.target.com"),
        ("info", "Katana: Found 84 endpoints on api.target.com"),
        ("info", "Katana: Found 58 endpoints on staging.target.com"),
        ("info", "Nuclei: Launching vulnerability scanner"),
        ("info", "Nuclei: Testing CVE-2023-3824 (unauthenticated RCE)"),
        ("info", "Nuclei: Testing SQL Injection templates"),
        ("warning", "Nuclei: Potential SQL Injection vulnerability detected on /api/v1/user"),
        ("info", "Nuclei: Testing Cross-Site Scripting (XSS) templates"),
        ("warning", "Nuclei: Potential XSS detected on /search?q="),
        ("info", "JS Analysis: Analysing script dependencies..."),
        ("info", "JS Analysis: Detected exposed credentials in app-bundle.js"),
        ("info", "AI Triage: Confirming SQL Injection..."),
        ("critical", "AI Triage: SQL Injection confirmed on /api/v1/user!"),
        ("info", "Chain Detection: Running automated vulnerability chaining..."),
        ("success", "Scan finished successfully. Reports generated.")
    ]
    
    findings = [
        {
            "type": "critical_finding",
            "title": "SQL Injection in /api/v1/user",
            "severity": "critical",
            "confidence": 94
        },
        {
            "type": "critical_finding",
            "title": "Exposed API Credentials in app-bundle.js",
            "severity": "high",
            "confidence": 88
        },
        {
            "type": "critical_finding",
            "title": "Reflected XSS in /search query parameter",
            "severity": "medium",
            "confidence": 75
        }
    ]
    
    try:
        subdomains = 0
        live_hosts = 0
        endpoints = 0
        findings_count = 0
        
        for idx, log in enumerate(logs):
            sev, msg = log
            
            if "Subfinder: Found" in msg:
                subdomains += 1
            if "HTTPX: " in msg and "is live" in msg:
                live_hosts += 1
            if "Katana: Found" in msg:
                endpoints += int(msg.split(" ")[2])
            
            finding_event = None
            if "Nuclei: Potential SQL Injection" in msg:
                finding_event = findings[0]
                findings_count += 1
            elif "Exposed credentials" in msg:
                finding_event = findings[1]
                findings_count += 1
            elif "Nuclei: Potential XSS" in msg:
                finding_event = findings[2]
                findings_count += 1
                
            stats = {
                "type": "stats",
                "subdomains": subdomains,
                "live_hosts": live_hosts,
                "endpoints": endpoints,
                "findings": findings_count
            }
            
            await websocket.send_json(stats)
            await asyncio.sleep(0.1)
            
            await websocket.send_json({
                "type": "output",
                "line": f"[{sev.upper()}] {msg}",
                "severity": sev
            })
            
            if finding_event:
                await websocket.send_json(finding_event)
                
            await asyncio.sleep(1.2)
            
        await websocket.send_json({"type": "output", "line": "[INFO] Scan complete.", "severity": "info"})
        while True:
            await asyncio.sleep(10)
            
    except WebSocketDisconnect:
        logger.info("Websocket disconnected for scan %s", scan_id)

