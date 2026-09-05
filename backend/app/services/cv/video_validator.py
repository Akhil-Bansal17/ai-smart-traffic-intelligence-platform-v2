"""
Video upload validation, sanitization, and secure storage service.

Enforces:
- Extension whitelist
- Content-level magic byte container validation (anti-spoofing)
- Filename sanitization & path-traversal prevention
- Server-side size limits with chunked stream counting
- Automated cleanup of partial / rejected uploads
"""
import os
import re
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile, status

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)

# Video container signatures (magic bytes)
# MP4 / QuickTime: Offset 4 contains 'ftyp' or starts with valid box markers
# AVI: Starts with 'RIFF' and offset 8 contains 'AVI '
VIDEO_SIGNATURES = {
    ".mp4": [b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide"],
    ".mov": [b"ftyp", b"moov", b"mdat", b"free", b"wide", b"pnot", b"skip"],
    ".avi": [b"RIFF"],
}


def sanitize_filename(filename: str) -> tuple[str, str]:
    """
    Sanitize client-provided filename and extract clean extension.
    Strips path separators, null bytes, and traversal tokens.
    """
    if not filename or not filename.strip():
        raise AppException("Filename cannot be empty.", code="invalid_filename", status_code=status.HTTP_400_BAD_REQUEST)

    # Strip null bytes
    cleaned = filename.replace("\x00", "")
    
    # Strip directory components
    basename = Path(cleaned).name

    # Remove non-alphanumeric characters except basic separators
    safe_name = re.sub(r"[^a-zA-Z0-9_.\- ]", "_", basename).strip()
    if not safe_name or safe_name in {".", ".."}:
        safe_name = "unnamed_video"

    ext = Path(safe_name).suffix.lower()
    return safe_name, ext


def validate_extension(extension: str) -> None:
    """Validate that the file extension is in the allowed list."""
    allowed_exts = [e.strip().lower() for e in settings.allowed_video_extensions.split(",") if e.strip()]
    if not extension or extension not in allowed_exts:
        raise AppException(
            f"Unsupported video format '{extension}'. Allowed formats: {', '.join(allowed_exts)}",
            code="unsupported_format",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


def validate_magic_bytes(file_header: bytes, extension: str) -> bool:
    """
    Verify that the initial file bytes match the expected video container structure.
    Protects against extension and MIME type spoofing.
    """
    if len(file_header) < 12:
        return False

    ext = extension.lower()

    if ext in {".mp4", ".mov"}:
        # Check for 'ftyp' at offset 4
        if file_header[4:8] == b"ftyp":
            return True
        # Check for other ISO BMFF/QuickTime top-level box types at offset 4
        box_type = file_header[4:8]
        if box_type in VIDEO_SIGNATURES.get(ext, []):
            return True
        # Check start of file
        if any(file_header.startswith(sig) for sig in [b"\x00\x00\x00", b"moov", b"mdat"]):
            return True
        return False

    if ext == ".avi":
        # AVI starts with RIFF....AVI
        return file_header.startswith(b"RIFF") and file_header[8:12] == b"AVI "

    return False


def get_secure_storage_path(extension: str) -> Path:
    """
    Generate an isolated, collision-safe destination path for the uploaded file.
    Guarantees the path is safely enclosed inside UPLOAD_DIR.
    """
    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}{extension}"
    dest_path = (upload_dir / unique_filename).resolve()

    # Path traversal assertion
    if not str(dest_path).startswith(str(upload_dir)):
        raise AppException(
            "Security violation: Illegal upload destination path.",
            code="path_traversal_violation",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return dest_path


async def save_and_validate_upload(file: UploadFile) -> tuple[str, Path, int]:
    """
    Stream upload file to disk while validating size, extension, and content headers.
    Returns (sanitized_original_filename, destination_path, file_size_bytes).
    Cleans up destination file if any validation fails.
    """
    original_name, ext = sanitize_filename(file.filename or "")
    validate_extension(ext)

    dest_path = get_secure_storage_path(ext)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    total_bytes = 0
    header_bytes = bytearray()

    try:
        with open(dest_path, "wb") as out_file:
            while chunk := await file.read(65536):  # 64 KB chunk
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise AppException(
                        f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB.",
                        code="file_too_large",
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413,
                    )

                if len(header_bytes) < 64:
                    header_bytes.extend(chunk[: 64 - len(header_bytes)])

                out_file.write(chunk)

        if total_bytes == 0:
            raise AppException("Uploaded file is empty (0 bytes).", code="empty_file", status_code=status.HTTP_400_BAD_REQUEST)

        # Validate content header bytes
        if not validate_magic_bytes(bytes(header_bytes), ext):
            raise AppException(
                "Uploaded file content does not match expected video container format.",
                code="invalid_video_content",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Successfully received and stored video '%s' (%d bytes) at safe location", original_name, total_bytes)
        return original_name, dest_path, total_bytes

    except Exception:
        # Guarantee no orphaned partial files
        if dest_path.exists():
            try:
                dest_path.unlink()
                logger.debug("Cleaned up rejected upload file: %s", dest_path.name)
            except OSError as err:
                logger.warning("Failed to clean up file %s: %s", dest_path.name, err)
        raise
