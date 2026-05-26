"""
Secure plugin loading and manifest validation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_MANIFEST_KEYS = {"name", "version", "permissions"}


def validate_plugin_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    if missing:
        raise ValueError(f"Plugin manifest missing keys: {missing}")
    if not isinstance(manifest.get("permissions"), list):
        raise ValueError("Plugin manifest permissions must be a list")
    return {
        "name": str(manifest["name"]),
        "version": str(manifest["version"]),
        "permissions": [str(permission) for permission in manifest.get("permissions", [])],
        "description": str(manifest.get("description") or ""),
        "hooks": manifest.get("hooks") or {},
        "dependencies": manifest.get("dependencies") or [],
        "marketplace_id": manifest.get("marketplace_id"),
    }


def verify_plugin_signature(manifest: dict[str, Any], signature: str, public_key: str) -> bool:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(public_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def load_plugin(plugin_source: dict[str, Any], signature: str | None = None, public_key: str | None = None) -> dict[str, Any]:
    manifest = validate_plugin_manifest(plugin_source.get("manifest") or plugin_source)
    if signature and public_key and not verify_plugin_signature(manifest, signature, public_key):
        raise ValueError("Invalid plugin signature")
    return {
        "manifest": manifest,
        "signature_verified": bool(signature and public_key),
        "source": plugin_source.get("source") or "marketplace",
    }
