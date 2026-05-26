"""
Shodan-style enrichment helpers for public service exposure analysis.
"""
from __future__ import annotations

from typing import Any
import re


PUBLIC_PORTS = {21, 22, 25, 53, 80, 110, 143, 443, 445, 465, 587, 8080, 8443, 9200, 3306, 5432}
SENSITIVE_KEYWORDS = {"admin", "graphql", "login", "auth", "swagger", "kibana", "jenkins", "dashboard"}


def _sanitize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def detect_public_services(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify internet-facing services from service banners and ports."""
    public_services: list[dict[str, Any]] = []
    for service in services:
        port = int(service.get("port") or 0)
        banner = _sanitize(service.get("banner") or service.get("title") or service.get("product"))
        scheme = _sanitize(service.get("scheme") or ("https" if port in {443, 8443} else "http"))
        confidence = 0.35

        if port in PUBLIC_PORTS:
            confidence += 0.35
        if banner:
            confidence += 0.1
        if any(keyword in banner.lower() for keyword in SENSITIVE_KEYWORDS):
            confidence += 0.2

        public_services.append(
            {
                "port": port or None,
                "scheme": scheme,
                "banner": banner or None,
                "is_public": confidence >= 0.6,
                "confidence": round(min(confidence, 1.0), 3),
            }
        )

    return public_services


def correlate_shodan_exposure(enriched_services: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate public-service findings into an exposure summary."""
    public_services = [service for service in enriched_services if service.get("is_public")]
    exposed_ports = [service.get("port") for service in public_services if service.get("port")]
    risky_banners = [service.get("banner") for service in public_services if service.get("banner")]

    severity = "low"
    if len(public_services) >= 5 or any(port in {22, 23, 2375, 3306, 5432} for port in exposed_ports):
        severity = "high"
    elif len(public_services) >= 2 or any(port in {80, 443, 8080, 8443} for port in exposed_ports):
        severity = "medium"

    return {
        "public_service_count": len(public_services),
        "exposed_ports": exposed_ports,
        "risky_banners": risky_banners,
        "severity": severity,
        "summary": f"Detected {len(public_services)} public services with {len(exposed_ports)} exposed ports.",
    }


def enrich_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Return a Shodan-style exposure view for one asset."""
    services = detect_public_services(asset.get("services", []))
    exposure = correlate_shodan_exposure(services)
    return {
        "asset": {
            "hostname": _sanitize(asset.get("hostname")),
            "ip_address": _sanitize(asset.get("ip_address")),
        },
        "services": services,
        "exposure": exposure,
    }