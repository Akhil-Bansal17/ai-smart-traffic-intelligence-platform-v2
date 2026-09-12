"""
Pydantic schemas for video upload and metadata responses.

Rule: Server-side filesystem paths (storage_path) are strictly private
and never exposed in response models.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    duration_seconds: float
    fps: float
    resolution: str
    frame_count: int
    status: str
    source_type: str = "unknown"
    source_reference: Optional[str] = None
    license_reference: Optional[str] = None
    provenance_note: Optional[str] = None
    provenance_verified: bool = False
    captured_at: Optional[datetime] = None
    uploaded_at: datetime


class VideoUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    duration_seconds: float
    fps: float
    resolution: str
    frame_count: int
    status: str
    source_type: str = "unknown"
    source_reference: Optional[str] = None
    license_reference: Optional[str] = None
    provenance_note: Optional[str] = None
    provenance_verified: bool = False
    captured_at: Optional[datetime] = None
    uploaded_at: datetime


class VideoListResponse(BaseModel):
    total: int
    limit: Optional[int] = None
    offset: Optional[int] = None
    videos: List[VideoResponse]

