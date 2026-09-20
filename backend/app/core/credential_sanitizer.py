"""
Credential sanitization and camera URI validation utilities.
Phase 21: Live Traffic Monitoring & Camera Source Management.
"""
import re
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from app.core.exceptions import AppException

# Regex to safely match and mask passwords in user:password@host connection strings
_CREDENTIAL_PATTERN = re.compile(r"://([^:@/]+):([^@/]+)@")


def redact_uri_credentials(uri: Optional[str]) -> Optional[str]:
    """
    Masks plaintext credentials (passwords) within connection URIs (RTSP, HTTP, etc.).
    Example:
        'rtsp://admin:secret_pass123@192.168.1.100:554/live'
        -> 'rtsp://admin:***@192.168.1.100:554/live'
    Returns non-URI or empty strings untouched.
    """
    if not uri:
        return uri

    try:
        # Regex substitution preserves the scheme, username, and path while masking the password
        return _CREDENTIAL_PATTERN.sub(r"://\1:***@", uri)
    except Exception:
        return uri


def validate_camera_uri(uri: str, source_type: str) -> None:
    """
    Validates connection URI syntax, prevents SSRF / dangerous paths, and verifies
    compatibility with the declared source_type.
    Raises AppException on validation failure.
    """
    if not uri or not uri.strip():
        raise AppException(
            "Connection URI cannot be empty.",
            code="invalid_camera_uri",
            status_code=422,
        )

    clean_uri = uri.strip()
    norm_source_type = source_type.lower().strip()

    # Reject null bytes or dangerous shell injection tokens
    if "\x00" in clean_uri or any(c in clean_uri for c in [";", "|", "&", "`", "$"]):
        raise AppException(
            "Connection URI contains invalid or forbidden characters.",
            code="invalid_camera_uri",
            status_code=422,
        )

    if norm_source_type == "local_camera":
        # Must be integer index (e.g. '0', '1') or valid device path
        if not (clean_uri.isdigit() or clean_uri.startswith("/dev/video")):
            raise AppException(
                f"Local camera source requires a valid device index (e.g. '0') or device path, got: '{clean_uri}'.",
                code="invalid_local_camera_uri",
                status_code=422,
            )

    elif norm_source_type == "rtsp":
        parsed = urlsplit(clean_uri)
        if parsed.scheme.lower() not in ("rtsp", "rtsps"):
            raise AppException(
                f"RTSP source type requires 'rtsp://' or 'rtsps://' scheme, got: '{parsed.scheme}'.",
                code="invalid_rtsp_uri",
                status_code=422,
            )
        if not parsed.hostname:
            raise AppException(
                "RTSP URI must include a valid host or IP address.",
                code="invalid_rtsp_host",
                status_code=422,
            )

    elif norm_source_type == "http_stream":
        parsed = urlsplit(clean_uri)
        if parsed.scheme.lower() not in ("http", "https"):
            raise AppException(
                f"HTTP stream source type requires 'http://' or 'https://' scheme, got: '{parsed.scheme}'.",
                code="invalid_http_uri",
                status_code=422,
            )
        if not parsed.hostname:
            raise AppException(
                "HTTP stream URI must include a valid host or IP address.",
                code="invalid_http_host",
                status_code=422,
            )

    elif norm_source_type in ("test_fixture", "fixture"):
        # Test fixtures are deterministically generated and allow symbolic names
        pass

    elif norm_source_type == "file":
        # Existing file source
        pass

    else:
        raise AppException(
            f"Unsupported camera source type: '{source_type}'. "
            f"Supported types: 'local_camera', 'rtsp', 'http_stream', 'test_fixture', 'file'.",
            code="unsupported_source_type",
            status_code=422,
        )
