"""
ASN intelligence helpers for provider attribution and infrastructure ownership.
"""
from __future__ import annotations

from typing import Any
import ipaddress


def resolve_asn(ip_address: str, asn_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve ASN information from a supplied context payload."""
    asn_context = asn_context or {}
    try:
        ipaddress.ip_address(ip_address)
    except ValueError:
        return {
            "ip_address": ip_address,
            "valid": False,
            "asn": None,
            "owner": None,
            "provider": None,
        }

    return {
        "ip_address": ip_address,
        "valid": True,
        "asn": asn_context.get("asn"),
        "owner": asn_context.get("owner") or asn_context.get("organization"),
        "provider": asn_context.get("provider") or asn_context.get("cloud_provider"),
        "country": asn_context.get("country"),
        "rir": asn_context.get("rir"),
    }


def analyze_infrastructure_owner(asn_record: dict[str, Any]) -> dict[str, Any]:
    """Derive ownership and hosting traits for the ASN record."""
    owner = str(asn_record.get("owner") or asn_record.get("provider") or "unknown")
    provider = str(asn_record.get("provider") or owner).lower()
    cloud_keywords = {"aws", "amazon", "azure", "microsoft", "gcp", "google", "cloudflare", "digitalocean"}
    ownership_type = "cloud" if any(keyword in provider for keyword in cloud_keywords) else "enterprise"

    return {
        **asn_record,
        "ownership_type": ownership_type,
        "provider_intelligence": {
            "is_major_cloud": ownership_type == "cloud",
            "provider_name": owner,
        },
    }


def correlate_provider_exposure(exposures: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate exposure by provider for cross-asset correlation."""
    provider_counts: dict[str, int] = {}
    for exposure in exposures:
        provider = str(exposure.get("provider") or exposure.get("owner") or "unknown")
        provider_counts[provider] = provider_counts.get(provider, 0) + 1

    hot_providers = sorted(provider_counts.items(), key=lambda item: item[1], reverse=True)
    severity = "high" if any(count >= 3 for _, count in hot_providers) else "medium" if hot_providers else "info"

    return {
        "provider_counts": provider_counts,
        "hot_providers": hot_providers,
        "severity": severity,
        "summary": f"{len(hot_providers)} providers correlated across exposure set.",
    }