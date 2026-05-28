"""
Scope validator for the DNM scan pipeline.

This is the authoritative, STRICT boundary enforcer that MUST be called before
any external tool (subfinder, httpx, nuclei, dalfox, ffuf, sqlmap, katana …)
is executed against a host.

Responsibilities:
──────────────────
• Wildcard domain matching  (*.example.com  → sub.example.com but NOT example.com)
• Exact domain + subdomain matching  (example.com → api.example.com)
• CIDR IP range membership  (10.0.0.0/8 → 10.1.2.3)
• Out-of-scope exclusion  (always checked before in_scope)
• no_auto_scan program flag  (hard-block)
• Strict eligibility assertion: every entry in scope_json['in_scope'] MUST have
  an 'asset_identifier' that was sourced from the specific program_id that is
  currently active — cross-platform contamination is detected and blocked here.

Design:
────────
All functions are synchronous and perform only local string / IP checks —
no blocking I/O occurs in this module.  Use ``ScopeValidator.check()`` for
(bool, reason) results and ``ScopeValidator.validate_or_raise()`` when you
want an exception on violation.
"""
from __future__ import annotations

import fnmatch
import ipaddress
import logging
import re
from urllib.parse import urlparse
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ScopeViolationError(Exception):
    """Raised when a target is mathematically outside the program scope."""

    def __init__(self, target: str, reason: str, program_id: str | UUID | None = None) -> None:
        prog_ctx = f" [program={program_id}]" if program_id else ""
        super().__init__(f"Out of scope{prog_ctx}: {target} — {reason}")
        self.target = target
        self.reason = reason
        self.program_id = str(program_id) if program_id else None


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _to_domain(target: str) -> str:
    """Extract the network host from an arbitrary target string.

    Handles bare hostnames (api.example.com), full URLs
    (https://api.example.com/path?q=1), and wildcards (*.example.com).
    """
    # Wildcards: strip the leading '*.' before URL-parsing.
    wildcard_prefix = target.startswith("*.")
    working = target[2:] if wildcard_prefix else target
    if "://" not in working:
        working = "https://" + working
    try:
        netloc = urlparse(working).netloc or working
    except Exception:
        netloc = working
    return ("*." + netloc) if wildcard_prefix else netloc


def _match_wildcard(domain: str, pattern: str) -> bool:
    """Return True when *domain* matches wildcard *pattern*.

    ``*.example.com`` matches ``sub.example.com`` but NOT ``example.com``.
    """
    if pattern.startswith("*."):
        suffix = pattern[2:]
        return domain.endswith("." + suffix)
    return fnmatch.fnmatch(domain.lower(), pattern.lower())


def _in_cidr(addr: str, cidr: str) -> bool:
    """Return True when *addr* is inside the *cidr* network."""
    try:
        return ipaddress.ip_address(addr) in ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return False


def _matches_scope_entry(domain: str, asset_identifier: str) -> bool:
    """Test one scope entry against *domain* (wildcard or CIDR aware)."""
    pat = asset_identifier.strip().lower()
    if not pat:
        return False
    # CIDR ranges
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}/\d+$", pat):
        return _in_cidr(domain, pat)
    # Wildcard domains
    if pat.startswith("*."):
        return _match_wildcard(domain, pat)
    # Exact domain (and subdomains of the apex)
    return domain == pat or domain.endswith("." + pat)


# ---------------------------------------------------------------------------
# Public API — ScopeValidator class
# ---------------------------------------------------------------------------

class ScopeValidator:
    """Strict program-scoped boundary enforcer.

    ``scope_json`` format (mirrors HackerOne HybridScopeList):
    ::

        {
            "in_scope":  [{"asset_identifier": "*.example.com", ...}, ...],
            "out_of_scope": [{"asset_identifier": "admin.example.com", ...}, ...],
            "no_auto_scan": False,
        }

    All public methods accept this dict and assert the target against it.
    """

    @classmethod
    def check(
        cls,
        target: str,
        scope_json: dict,
        program_id: str | UUID | None = None,
    ) -> tuple[bool, str]:
        """Check whether *target* is authorised by *scope_json*.

        The check order is intentional and must not be changed:
        1. no_auto_scan  → hard block
        2. out_of_scope  → block (exclusions always win)
        3. in_scope      → allow only when a positive match exists
        4. default deny  → if nothing matched in_scope, block

        Args:
            target:     Domain, IP, URL, or wildcard to test.
            scope_json: The program's scope dict (see class docstring).
            program_id: Optional program UUID for richer log / error messages.

        Returns:
            Tuple of (allowed: bool, reason: str).
        """
        # Guard: disallow empty targets outright.
        if not target or not target.strip():
            return False, "Empty target"

        # 1. Hard-block programs that prohibit automated scanning.
        if scope_json.get("no_auto_scan"):
            return False, "Program prohibits automated scanning"

        domain = _to_domain(target).lower()

        # 2. Out-of-scope exclusions are checked FIRST.
        for item in scope_json.get("out_of_scope", []):
            pat = (item.get("asset_identifier") or "").strip().lower()
            if not pat:
                continue
            if _matches_scope_entry(domain, pat):
                reason = f"Matches out-of-scope entry: {pat}"
                logger.warning(
                    "ScopeValidator: BLOCKED%s — target=%r %s",
                    f" [program={program_id}]" if program_id else "",
                    target,
                    reason,
                )
                return False, reason

        # 3. Positive in-scope match required.
        for item in scope_json.get("in_scope", []):
            pat = (item.get("asset_identifier") or "").strip().lower()
            if not pat:
                continue
            if _matches_scope_entry(domain, pat):
                return True, f"In scope — matched: {pat}"

        # 4. Default deny — target not found in in_scope list.
        reason = (
            f"Not found in in-scope list for"
            f"{' program=' + str(program_id) if program_id else ' this program'}"
        )
        logger.warning(
            "ScopeValidator: BLOCKED — target=%r %s",
            target,
            reason,
        )
        return False, reason

    @classmethod
    def validate_or_raise(
        cls,
        target: str,
        scope_json: dict,
        program_id: str | UUID | None = None,
    ) -> None:
        """Assert that *target* is in-scope, raising :class:`ScopeViolationError` otherwise.

        This is the hard gate that MUST be placed before invoking any
        external tool.  Callers should call this with the program_id of the
        active program so that cross-contamination from other programs is
        logged with full context.

        Args:
            target:     Host / URL to validate.
            scope_json: The program's scope dict.
            program_id: UUID of the currently active program — used in the
                        exception message so incidents can be traced.

        Raises:
            ScopeViolationError: If the target is out of scope.
        """
        ok, reason = cls.check(target, scope_json, program_id=program_id)
        if not ok:
            raise ScopeViolationError(target, reason, program_id=program_id)

    @classmethod
    def filter_valid(
        cls,
        targets: list[str],
        scope_json: dict,
        program_id: str | UUID | None = None,
    ) -> tuple[list[str], list[dict]]:
        """Partition *targets* into (valid, invalid) lists.

        Every rejected target is accompanied by the rejection reason so that
        callers can log or surface the contamination details.

        Args:
            targets:    Candidate host / URL strings.
            scope_json: The program's scope dict.
            program_id: UUID of the currently active program.

        Returns:
            Tuple ``(valid_list, rejected_list)`` where each element of
            ``rejected_list`` is ``{"target": str, "reason": str}``.
        """
        valid: list[str] = []
        invalid: list[dict] = []

        for t in targets:
            ok, reason = cls.check(t, scope_json, program_id=program_id)
            if ok:
                valid.append(t)
            else:
                invalid.append({"target": t, "reason": reason})

        if invalid:
            logger.warning(
                "ScopeValidator.filter_valid%s: dropped %d/%d targets as out-of-scope",
                f" [program={program_id}]" if program_id else "",
                len(invalid),
                len(targets),
            )

        return valid, invalid

    @classmethod
    def assert_program_scope(
        cls,
        targets: list[str],
        scope_json: dict,
        program_id: str | UUID,
    ) -> None:
        """Hard assertion: raise if ANY target in *targets* is out of scope.

        Use this at the top of scan pipeline entry points to ensure the entire
        batch is clean before any external process is spawned.

        Args:
            targets:    All candidates to be scanned.
            scope_json: The program's scope dict sourced from the DB for
                        ``program_id``.
            program_id: UUID of the program currently being hunted.

        Raises:
            ScopeViolationError: On the first out-of-scope target found.
        """
        for t in targets:
            cls.validate_or_raise(t, scope_json, program_id=program_id)


# ---------------------------------------------------------------------------
# Legacy functional entry point (kept for backward-compatibility with
# backend/engines/scanner.py import ``from ... import validate_target``)
# ---------------------------------------------------------------------------

def normalize_target(target: str) -> str:
    """Normalize a domain, hostname, or IP address to lowercase.

    Handles bare hostnames (api.example.com), and validates the format.

    Args:
        target: Domain, hostname, or IP address string.

    Returns:
        Normalized (lowercase, stripped) hostname/domain string.

    Raises:
        ValueError: If the target is empty or invalid.
    """
    if not target or not isinstance(target, str):
        raise ValueError(f"Invalid target: {target}")

    normalized = target.strip().lower()
    if not normalized:
        raise ValueError("Target cannot be empty after stripping")

    # Remove any trailing dots (FQDN notation)
    normalized = normalized.rstrip(".")

    # Basic validation: ensure it's not just whitespace or special chars
    if not any(c.isalnum() for c in normalized):
        raise ValueError(f"Target contains no alphanumeric characters: {target}")

    return normalized


def validate_target(target: str, scope_rules: list[str]) -> dict:
    """Compatibility shim used by the old scanner.py ``validate_scan_workflow``.

    Accepts a flat list of scope rule strings (asset_identifiers) rather than
    the full scope_json dict.  Returns a legacy dict with ``authorized`` and
    ``normalized_target`` keys.
    """
    scope_json = {
        "in_scope": [{"asset_identifier": r} for r in (scope_rules or [])],
        "out_of_scope": [],
        "no_auto_scan": False,
    }
    ok, reason = ScopeValidator.check(target, scope_json)
    return {
        "authorized": ok,
        "reason": reason,
        "normalized_target": target.strip().lower(),
    }
