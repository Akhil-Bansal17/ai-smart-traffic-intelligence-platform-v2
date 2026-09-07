"""
Pydantic schemas for video upload and metadata responses.

Rule: Server-side filesystem paths (storage_path) are strictly private
and never exposed in response models.
"""
from datetime import datetime
from typing import List

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
    source_type: str = "real_world"
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
    source_type: str = "real_world"
    uploaded_at: datetime


class VideoListResponse(BaseModel):
    total: int
    videos: List[VideoResponse]
