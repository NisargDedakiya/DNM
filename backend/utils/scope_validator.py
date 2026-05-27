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
    def _to_domain(target: str) -> str:
        if '://' not in target:
            target = 'https://' + target
        try:
            return urlparse(target).netloc or target
        except Exception:
            return target

    @staticmethod
    def _wildcard(domain: str, pattern: str) -> bool:
        # *.example.com matches sub.example.com but NOT example.com
        if pattern.startswith('*.'):
            suffix = pattern[2:]
            return domain.endswith('.' + suffix)
        return fnmatch.fnmatch(domain.lower(), pattern.lower())

    @staticmethod
    def _in_cidr(addr: str, cidr: str) -> bool:
        try:
            return ipaddress.ip_address(addr) in ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return False

    @classmethod
    def check(cls, target: str, scope_json: dict) -> tuple[bool, str]:
        # scope_json from H1 client:
        # {in_scope: [{asset_identifier, asset_type}], out_of_scope: [...], no_auto_scan: bool}
        if scope_json.get('no_auto_scan'):
            return False, 'Program prohibits automated scanning'
        domain = cls._to_domain(target)
        # ALWAYS check out_of_scope first
        for item in scope_json.get('out_of_scope', []):
            pat = item.get('asset_identifier', '')
            if cls._wildcard(domain, pat) or cls._in_cidr(domain, pat):
                return False, f'Matches out-of-scope pattern: {pat}'
        # Then check in_scope
        for item in scope_json.get('in_scope', []):
            pat = item.get('asset_identifier', '')
            if cls._wildcard(domain, pat) or cls._in_cidr(domain, pat):
                return True, 'In scope'
        return False, 'Not found in in-scope list'

    @classmethod
    def validate_or_raise(cls, target: str, scope_json: dict):
        ok, reason = cls.check(target, scope_json)
        if not ok:
            raise ScopeViolationError(target, reason)

    @classmethod
    def filter_valid(cls, targets: list[str], scope_json: dict):
        # Returns (valid_list, invalid_list_with_reasons)
        valid, invalid = [], []
        for t in targets:
            ok, reason = cls.check(t, scope_json)
            if ok:
                valid.append(t)
            else:
                invalid.append({'target': t, 'reason': reason})
        return valid, invalid
