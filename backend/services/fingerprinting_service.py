"""
Passive technology fingerprinting service.
Detects frameworks, servers, and technologies from HTTP responses.
"""
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.exposure import AssetFingerprint, ExposureType


class FingerprintingService:
    """
    Passive fingerprinting of web technologies.
    Analyzes HTTP responses, headers, and content for technology detection.
    """

    # Technology fingerprint signatures (passive patterns only)
    FRAMEWORK_SIGNATURES = {
        "django": {
            "headers": [r"Server.*Django"],
            "body_patterns": [r"csrftoken", r"django\.static"],
            "confidence": 0.9,
        },
        "fastapi": {
            "headers": [r"Server.*Starlette"],
            "body_patterns": [r"swagger", r"/docs"],
            "confidence": 0.85,
        },
        "flask": {
            "headers": [r"Server.*Werkzeug"],
            "body_patterns": [r"__flask"],
            "confidence": 0.8,
        },
        "laravel": {
            "headers": [r"Set-Cookie.*laravel"],
            "body_patterns": [r"laravel", r"_token"],
            "confidence": 0.85,
        },
        "rails": {
            "headers": [r"Server.*Ruby"],
            "body_patterns": [r"csrf-param", r"csrf-token"],
            "confidence": 0.8,
        },
        "react": {
            "body_patterns": [r"__react", r"__webpack", r"react"],
            "confidence": 0.75,
        },
        "vue": {
            "body_patterns": [r"__vue", r"Vue"],
            "confidence": 0.75,
        },
        "angular": {
            "body_patterns": [r"ng-", r"angular"],
            "confidence": 0.75,
        },
        "wordpress": {
            "body_patterns": [r"wp-content", r"wp-includes", r"wordpress"],
            "confidence": 0.9,
        },
        "joomla": {
            "body_patterns": [r"joomla", r"index\.php\?option=com"],
            "confidence": 0.85,
        },
    }

    SERVER_SIGNATURES = {
        "nginx": {
            "headers": [r"Server.*nginx"],
            "confidence": 0.95,
        },
        "apache": {
            "headers": [r"Server.*Apache"],
            "confidence": 0.95,
        },
        "iis": {
            "headers": [r"Server.*IIS", r"X-Powered-By.*ASP\.NET"],
            "confidence": 0.9,
        },
        "caddy": {
            "headers": [r"Server.*Caddy"],
            "confidence": 0.95,
        },
        "cloudflare": {
            "headers": [r"Server.*cloudflare", r"CF-Ray"],
            "confidence": 0.95,
        },
    }

    CMS_SIGNATURES = {
        "wordpress": {
            "patterns": [r"wp-content", r"wp-includes", r"/wp-json"],
            "confidence": 0.9,
        },
        "joomla": {
            "patterns": [r"joomla", r"/index\.php\?option"],
            "confidence": 0.85,
        },
        "drupal": {
            "patterns": [r"drupal", r"/modules/", r"/themes/"],
            "confidence": 0.8,
        },
        "shopify": {
            "patterns": [r"myshopify\.com", r"Shopify\."],
            "confidence": 0.95,
        },
        "magento": {
            "patterns": [r"magento", r"/skin/", r"/media/"],
            "confidence": 0.8,
        },
    }

    # Security headers
    SECURITY_HEADERS = {
        "content-security-policy": "csp",
        "strict-transport-security": "hsts",
        "x-frame-options": "x_frame_options",
        "x-content-type-options": "x_content_type_options",
        "referrer-policy": "referrer_policy",
    }

    def __init__(self, db: AsyncSession):
        """Initialize fingerprinting service."""
        self.db = db

    async def detect_technologies(
        self,
        response_headers: dict,
        response_body: str,
        status_code: int,
    ) -> dict:
        """
        Detect technologies from HTTP response.

        Args:
            response_headers: HTTP response headers (lowercased keys)
            response_body: HTTP response body
            status_code: HTTP status code

        Returns:
            dict: {
                frameworks: [{name, confidence}],
                servers: [{name, confidence}],
                cms: [{name, confidence}],
                technologies: [{name, category, confidence}],
                has_issues: bool
            }
        """
        technologies = {
            "frameworks": [],
            "servers": [],
            "cms": [],
            "technologies": [],
            "has_issues": False,
        }

        # Detect frameworks
        for framework, sig in self.FRAMEWORK_SIGNATURES.items():
            if self._match_signatures(
                response_headers, response_body, sig.get("headers", []), sig.get("body_patterns", [])
            ):
                technologies["frameworks"].append(
                    {
                        "name": framework,
                        "confidence": sig["confidence"],
                    }
                )

        # Detect servers
        for server, sig in self.SERVER_SIGNATURES.items():
            if self._match_signatures(
                response_headers,
                response_body,
                sig.get("headers", []),
                sig.get("body_patterns", []),
            ):
                technologies["servers"].append(
                    {
                        "name": server,
                        "confidence": sig["confidence"],
                    }
                )

        # Detect CMS
        for cms, sig in self.CMS_SIGNATURES.items():
            if self._match_patterns(response_body, sig.get("patterns", [])):
                technologies["cms"].append(
                    {
                        "name": cms,
                        "confidence": sig["confidence"],
                    }
                )

        return technologies

    async def fingerprint_framework(
        self,
        response_headers: dict,
        response_body: str,
    ) -> tuple[str | None, float]:
        """
        Identify specific framework from response.

        Args:
            response_headers: HTTP response headers
            response_body: HTTP response body

        Returns:
            tuple: (framework_name, confidence_score)
        """
        best_match = None
        best_confidence = 0.0

        for framework, sig in self.FRAMEWORK_SIGNATURES.items():
            if self._match_signatures(
                response_headers, response_body, sig.get("headers", []), sig.get("body_patterns", [])
            ):
                if sig["confidence"] > best_confidence:
                    best_match = framework
                    best_confidence = sig["confidence"]

        return (best_match, best_confidence) if best_match else (None, 0.0)

    async def analyze_headers(
        self,
        response_headers: dict,
    ) -> dict:
        """
        Analyze HTTP security headers.

        Args:
            response_headers: HTTP response headers (lowercased keys)

        Returns:
            dict: {
                has_csp, has_hsts, has_x_frame_options,
                has_x_content_type_options, has_referrer_policy,
                missing_headers: [list],
                weak_headers: [list]
            }
        """
        analysis = {
            "has_csp": False,
            "has_hsts": False,
            "has_x_frame_options": False,
            "has_x_content_type_options": False,
            "has_referrer_policy": False,
            "missing_headers": [],
            "weak_headers": [],
        }

        # Check presence of security headers
        for header_name, short_name in self.SECURITY_HEADERS.items():
            if header_name in response_headers:
                analysis[f"has_{short_name}"] = True
            else:
                analysis["missing_headers"].append(header_name)

        # Check for weak header values
        if "strict-transport-security" in response_headers:
            hsts_value = response_headers["strict-transport-security"]
            if "max-age" in hsts_value:
                # Extract max-age
                match = re.search(r"max-age=(\d+)", hsts_value)
                if match:
                    max_age = int(match.group(1))
                    if max_age < 31536000:  # Less than 1 year
                        analysis["weak_headers"].append(
                            f"HSTS max-age too low: {max_age}s"
                        )

        if "content-security-policy" in response_headers:
            csp_value = response_headers["content-security-policy"]
            if "unsafe-inline" in csp_value:
                analysis["weak_headers"].append("CSP allows unsafe-inline")
            if "unsafe-eval" in csp_value:
                analysis["weak_headers"].append("CSP allows unsafe-eval")

        return analysis

    async def categorize_service(
        self,
        response_headers: dict,
        response_body: str,
        status_code: int,
    ) -> dict:
        """
        Categorize service type from response.

        Args:
            response_headers: HTTP response headers
            response_body: HTTP response body
            status_code: HTTP status code

        Returns:
            dict: {
                service_type, confidence, categories: [],
                is_api, is_cms, is_framework, indicators: []
            }
        """
        result = {
            "service_type": "unknown",
            "confidence": 0.0,
            "categories": [],
            "is_api": False,
            "is_cms": False,
            "is_framework": False,
            "indicators": [],
        }

        # Detect API patterns
        api_patterns = [
            r"/api/",
            r"/v\d+/",
            r"application/json",
            r"swagger",
            r"openapi",
        ]
        if self._match_patterns(
            f"{' '.join(response_headers.values())} {response_body}",
            api_patterns,
        ):
            result["is_api"] = True
            result["categories"].append("api")
            result["indicators"].append("API endpoints detected")

        # Detect CMS
        technologies = await self.detect_technologies(
            response_headers, response_body, status_code
        )
        if technologies["cms"]:
            result["is_cms"] = True
            result["categories"].append("cms")
            cms_names = [cms["name"] for cms in technologies["cms"]]
            result["indicators"].append(f"CMS detected: {', '.join(cms_names)}")

        # Detect framework
        if technologies["frameworks"]:
            result["is_framework"] = True
            result["categories"].append("framework")
            framework_names = [f["name"] for f in technologies["frameworks"]]
            result["indicators"].append(
                f"Framework detected: {', '.join(framework_names)}"
            )

        # Determine primary service type
        if result["is_api"]:
            result["service_type"] = "api"
            result["confidence"] = 0.9
        elif result["is_cms"]:
            result["service_type"] = "cms"
            result["confidence"] = 0.85
        elif result["is_framework"]:
            result["service_type"] = "web_application"
            result["confidence"] = 0.8
        else:
            result["service_type"] = "web_server"
            result["confidence"] = 0.6

        return result

    async def detect_exposures_from_fingerprint(
        self,
        technologies: dict,
        headers_analysis: dict,
        status_code: int,
    ) -> list[tuple[str, str, float]]:
        """
        Detect exposures based on fingerprinted technologies.

        Args:
            technologies: Technologies dict from detect_technologies()
            headers_analysis: Headers analysis dict from analyze_headers()
            status_code: HTTP status code

        Returns:
            list: [(exposure_type, description, confidence)]
        """
        exposures = []

        # Weak headers exposure
        if len(headers_analysis["missing_headers"]) >= 3:
            exposures.append(
                (
                    "weak_headers",
                    f"Missing {len(headers_analysis['missing_headers'])} security headers",
                    0.8,
                )
            )

        # Debug interface
        if status_code == 200:
            body_lower = ""  # Would have response body
            if any(
                pattern in body_lower
                for pattern in [
                    "debug=true",
                    "debuginfo",
                    "debug_mode",
                    "development",
                ]
            ):
                exposures.append(
                    ("debug_interface", "Debug mode appears to be enabled", 0.85)
                )

        return exposures

    @staticmethod
    def _match_signatures(
        headers: dict,
        body: str,
        header_patterns: list[str],
        body_patterns: list[str],
    ) -> bool:
        """Match against multiple signature patterns."""
        # Check header patterns
        for pattern in header_patterns:
            for header_value in headers.values():
                if re.search(pattern, str(header_value), re.IGNORECASE):
                    return True

        # Check body patterns
        for pattern in body_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def _match_patterns(text: str, patterns: list[str]) -> bool:
        """Match text against multiple patterns."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
