"""
Camera source management and live monitoring endpoints: /api/v1/camera-sources.
Phase 21: Live Traffic Monitoring & Camera Source Management.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.credential_sanitizer import redact_uri_credentials, validate_camera_uri
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.camera_source import CameraSource, CameraSourceStatus, CameraSourceType
from app.schemas.analysis_job import AnalysisJobResponse
from app.schemas.camera_source import (
    CameraSourceCreateRequest,
    CameraSourceListResponse,
    CameraSourceResponse,
    CameraSourceTestResponse,
    CameraSourceUpdateRequest,
    LiveMonitoringStartRequest,
    LiveMonitoringStatusResponse,
)
from app.services.cv.camera_source_adapter import create_camera_source
from app.services.cv.job_manager import AnalysisJobManager, get_analysis_job_manager

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "",
    response_model=CameraSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new camera or stream source",
    description="Adds a camera stream configuration (local camera, RTSP, HTTP, or test fixture) with validated URI.",
)
def create_camera_source_endpoint(
    payload: CameraSourceCreateRequest,
    db: Session = Depends(get_db),
) -> CameraSourceResponse:
    validate_camera_uri(payload.connection_uri, payload.source_type)

    source = CameraSource(
        name=payload.name,
        description=payload.description,
        source_type=payload.source_type,
        connection_uri=payload.connection_uri,
        enabled=payload.enabled,
        location_name=payload.location_name,
        status=CameraSourceStatus.DISCONNECTED.value,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    logger.info("Registered camera source '%s' (id=%s, type=%s)", source.name, source.id, source.source_type)
    return CameraSourceResponse.model_validate(source)


@router.get(
    "",
    response_model=CameraSourceListResponse,
    summary="List all registered camera sources",
    description="Returns all camera sources with credentials safely redacted in URIs.",
)
def list_camera_sources_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source_type: Optional[str] = Query(default=None),
    enabled: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
) -> CameraSourceListResponse:
    query = db.query(CameraSource)
    if source_type:
        query = query.filter(CameraSource.source_type == source_type)
    if enabled is not None:
        query = query.filter(CameraSource.enabled == enabled)

    total = query.count()
    items = query.order_by(CameraSource.created_at.desc()).offset(offset).limit(limit).all()

    return CameraSourceListResponse(
        total=total,
        items=[CameraSourceResponse.model_validate(s) for s in items],
    )


@router.get(
    "/{camera_id}",
    response_model=CameraSourceResponse,
    summary="Get camera source by ID",
)
def get_camera_source_endpoint(
    camera_id: str,
    db: Session = Depends(get_db),
) -> CameraSourceResponse:
    source = db.query(CameraSource).filter(CameraSource.id == camera_id).first()
    if not source:
        raise AppException(
            f"Camera source '{camera_id}' not found.",
            code="camera_source_not_found",
            status_code=404,
        )
    return CameraSourceResponse.model_validate(source)


@router.patch(
    "/{camera_id}",
    response_model=CameraSourceResponse,
    summary="Update camera source configuration",
)
def update_camera_source_endpoint(
    camera_id: str,
    payload: CameraSourceUpdateRequest,
    db: Session = Depends(get_db),
) -> CameraSourceResponse:
    source = db.query(CameraSource).filter(CameraSource.id == camera_id).first()
    if not source:
        raise AppException(
            f"Camera source '{camera_id}' not found.",
            code="camera_source_not_found",
            status_code=404,
        )

    if payload.connection_uri is not None:
        effective_type = payload.source_type or source.source_type
        validate_camera_uri(payload.connection_uri, effective_type)
        source.connection_uri = payload.connection_uri

    if payload.name is not None:
        source.name = payload.name
    if payload.description is not None:
        source.description = payload.description
    if payload.source_type is not None:
        source.source_type = payload.source_type
    if payload.enabled is not None:
        source.enabled = payload.enabled
    if payload.location_name is not None:
        source.location_name = payload.location_name

    db.commit()
    db.refresh(source)
    return CameraSourceResponse.model_validate(source)


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete camera source",
)
def delete_camera_source_endpoint(
    camera_id: str,
    db: Session = Depends(get_db),
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> None:
    source = db.query(CameraSource).filter(CameraSource.id == camera_id).first()
    if not source:
        raise AppException(
            f"Camera source '{camera_id}' not found.",
            code="camera_source_not_found",
            status_code=404,
        )

    # If active job exists, stop it first
    try:
        manager.stop_live_job(db, camera_id)
    except Exception:
        pass

    db.delete(source)
    db.commit()
    logger.info("Deleted camera source '%s' (id=%s)", source.name, camera_id)


@router.post(
    "/{camera_id}/test",
    response_model=CameraSourceTestResponse,
    summary="Probe camera connection",
    description="Tests source connectivity, measures latency, and extracts resolution/FPS without starting monitoring.",
)
def test_camera_connection_endpoint(
    camera_id: str,
    db: Session = Depends(get_db),
) -> CameraSourceTestResponse:
    source = db.query(CameraSource).filter(CameraSource.id == camera_id).first()
    if not source:
        raise AppException(
            f"Camera source '{camera_id}' not found.",
            code="camera_source_not_found",
            status_code=404,
        )

    redacted_uri = redact_uri_credentials(source.connection_uri) or ""

    try:
        adapter = create_camera_source(
            source_id=source.id,
            source_type=source.source_type,
            uri=source.connection_uri,
        )
        connected = adapter.connect()
        if not connected:
            return CameraSourceTestResponse(
                success=False,
                message="Connection probe failed. Source rejected connection or timed out.",
                source_type=source.source_type,
                connection_uri=redacted_uri,
                error="Unable to connect to source device or stream.",
            )

        meta = adapter.read_metadata()
        frame = adapter.read_frame(timeout_seconds=3.0)
        adapter.release()

        if frame is None:
            return CameraSourceTestResponse(
                success=False,
                message="Connected to stream, but failed to read video frame within timeout.",
                source_type=source.source_type,
                connection_uri=redacted_uri,
                width=meta.width,
                height=meta.height,
                fps=meta.fps,
                error="Frame acquisition timeout.",
            )

        # Update cached metadata in DB
        source.width = meta.width
        source.height = meta.height
        source.fps = meta.fps
        db.commit()

        return CameraSourceTestResponse(
            success=True,
            message=f"Successfully connected to camera stream ({meta.width}x{meta.height} @ {meta.fps} FPS).",
            source_type=source.source_type,
            connection_uri=redacted_uri,
            width=meta.width,
            height=meta.height,
            fps=meta.fps,
        )

    except Exception as err:
        return CameraSourceTestResponse(
            success=False,
            message="Error while probing camera connection.",
            source_type=source.source_type,
            connection_uri=redacted_uri,
            error=str(err),
        )


@router.post(
    "/{camera_id}/start",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start live traffic monitoring on camera",
    description="Launches an asynchronous live analysis background job on this camera stream.",
)
def start_live_monitoring_endpoint(
    camera_id: str,
    payload: Optional[LiveMonitoringStartRequest] = None,
    db: Session = Depends(get_db),
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> AnalysisJobResponse:
    config_dict = {}
    if payload:
        if payload.confidence_threshold is not None:
            config_dict["confidence_threshold"] = payload.confidence_threshold
        if payload.processing_fps is not None:
            config_dict["processing_fps"] = payload.processing_fps
        if payload.iou_threshold is not None:
            config_dict["iou_threshold"] = payload.iou_threshold
        if payload.counting_line:
            config_dict["counting_line"] = payload.counting_line.model_dump()
        if payload.lanes:
            config_dict["lanes"] = [lane.model_dump() for lane in payload.lanes]
        if payload.persistence_threshold is not None:
            config_dict["persistence_threshold"] = payload.persistence_threshold

    job = manager.submit_live_job(db=db, camera_source_id=camera_id, config=config_dict)
    return AnalysisJobResponse.model_validate(job)


@router.post(
    "/{camera_id}/stop",
    response_model=AnalysisJobResponse,
    summary="Stop live traffic monitoring on camera",
    description="Stops active live analysis, completes the job, and persists the resulting AnalysisSession.",
)
def stop_live_monitoring_endpoint(
    camera_id: str,
    db: Session = Depends(get_db),
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> AnalysisJobResponse:
    job = manager.stop_live_job(db=db, job_id_or_camera_id=camera_id)
    return AnalysisJobResponse.model_validate(job)


@router.get(
    "/{camera_id}/live-status",
    response_model=LiveMonitoringStatusResponse,
    summary="Poll real-time metrics and status for camera",
    description="Returns live vehicle volume, active tracks, flow, dropped frames, and connection state.",
)
def get_live_status_endpoint(
    camera_id: str,
    db: Session = Depends(get_db),
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> LiveMonitoringStatusResponse:
    source = db.query(CameraSource).filter(CameraSource.id == camera_id).first()
    if not source:
        raise AppException(
            f"Camera source '{camera_id}' not found.",
            code="camera_source_not_found",
            status_code=404,
        )

    # Check active snapshot from manager
    snapshot = manager.get_live_status(camera_id)

    # Find active job ID if running
    active_job = (
        db.query(AnalysisJob)
        .filter(
            AnalysisJob.camera_source_id == camera_id,
            AnalysisJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
        )
        .order_by(AnalysisJob.created_at.desc())
        .first()
    )

    if snapshot:
        return LiveMonitoringStatusResponse(
            camera_source_id=source.id,
            camera_name=source.name,
            status="running",
            active_job_id=snapshot.job_id,
            is_live=snapshot.is_live,
            source_type=snapshot.source_type,
            source_fps=snapshot.source_fps,
            processing_fps=snapshot.processing_fps,
            frames_acquired=snapshot.frames_acquired,
            frames_processed=snapshot.frames_processed,
            dropped_frames=snapshot.dropped_frames,
            reconnect_count=snapshot.reconnect_count,
            total_volume=snapshot.total_volume,
            inbound_volume=snapshot.inbound_volume,
            outbound_volume=snapshot.outbound_volume,
            active_tracks_count=snapshot.active_tracks_count,
            class_distribution=snapshot.class_distribution,
            direction_distribution=snapshot.direction_distribution,
            lane_occupancies=snapshot.lane_occupancies,
            lane_densities=snapshot.lane_densities,
            provenance_tag=snapshot.provenance_tag,
            last_frame_timestamp=snapshot.last_frame_timestamp,
            last_updated=snapshot.last_updated,
            error_message=snapshot.error_message,
        )

    # If no live service active, return static source status
    prov = "test_fixture_observation" if source.source_type == "test_fixture" else "live_observation"
    return LiveMonitoringStatusResponse(
        camera_source_id=source.id,
        camera_name=source.name,
        status=active_job.status if active_job else source.status,
        active_job_id=active_job.id if active_job else None,
        is_live=active_job is not None and active_job.status in (JobStatus.RUNNING.value, JobStatus.QUEUED.value),
        source_type=source.source_type,
        source_fps=source.fps or 0.0,
        processing_fps=0.0,
        provenance_tag=prov,
        last_updated=source.updated_at,
        error_message=source.last_error,
    )


@router.get(
    "/{camera_id}/preview.jpg",
    summary="Get latest annotated video frame preview",
    description="Returns the current annotated frame JPEG generated by the live analysis loop without secondary inference.",
    responses={
        200: {"content": {"image/jpeg": {}}, "description": "Annotated JPEG frame."},
        404: {"description": "No active preview available."},
    },
)
def get_live_preview_endpoint(
    camera_id: str,
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> Response:
    jpeg_bytes = manager.get_preview_jpeg(camera_id)
    if not jpeg_bytes:
        # Return lightweight blank 1x1 or placeholder
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No live preview frame available for this camera.",
        )

    return Response(content=jpeg_bytes, media_type="image/jpeg")
