import fnmatch
import ipaddress
import re
from urllib.parse import urlparse

def normalize_target(target: str) -> str:
    target = target.strip()
    target = re.sub(r"^(https?://)", "", target, flags=re.IGNORECASE)
    target = re.sub(r"^www\.", "", target, flags=re.IGNORECASE)
    target = target.rstrip("/")
    if any(c.isalpha() for c in target):
        target = target.lower()
    return target

class ScopeViolationError(Exception):
    def __init__(self, target: str, reason: str):
        super().__init__(f'Out of scope: {target} — {reason}')
        self.target = target
        self.reason = reason

class ScopeValidator:

    @staticmethod
    def _domain(target: str) -> str:
        try:
            p = urlparse(target if '://' in target else 'https://'+target)
            return p.netloc or p.path.split('/')[0]
        except Exception:
            return target

    @staticmethod
    def _wildcard_match(domain: str, pattern: str) -> bool:
        # *.example.com matches sub.example.com but NOT example.com
        if pattern.startswith('*.'):
            suffix = pattern[2:]
            return domain.endswith('.'+suffix) or domain == suffix
        return fnmatch.fnmatch(domain.lower(), pattern.lower())

    @staticmethod
    def _cidr_match(addr: str, cidr: str) -> bool:
        try:
            return ipaddress.ip_address(addr) in ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return False

    @classmethod
    def check(cls, target: str, scope_json: dict) -> tuple[bool, str]:
        # Returns (ok, reason)
        # scope_json format from your H1 client:
        # {in_scope: [{asset_identifier, asset_type}], out_of_scope: [...], no_auto_scan: bool}
        if scope_json.get('no_auto_scan'):
            return False, 'Program prohibits automated scanning'
        d = cls._domain(target)
        # Check out of scope FIRST
        for item in scope_json.get('out_of_scope', []):
            pat = item.get('asset_identifier', '')
            if cls._wildcard_match(d, pat) or cls._cidr_match(d, pat):
                return False, f'Matches out-of-scope: {pat}'
        # Check in scope
        for item in scope_json.get('in_scope', []):
            pat = item.get('asset_identifier', '')
            if cls._wildcard_match(d, pat) or cls._cidr_match(d, pat):
                return True, 'In scope'
        return False, 'Not found in any in-scope pattern'

    @classmethod
    def validate_or_raise(cls, target: str, scope_json: dict):
        ok, reason = cls.check(target, scope_json)
        if not ok:
            raise ScopeViolationError(target, reason)

    @classmethod
    def filter_valid(cls, targets: list[str], scope_json: dict) -> tuple[list, list]:
        # Returns (valid_targets, invalid_targets_with_reasons)
        valid, invalid = [], []
        for t in targets:
            ok, reason = cls.check(t, scope_json)
            (valid if ok else invalid).append(t if ok else {'target': t, 'reason': reason})
        return valid, invalid
