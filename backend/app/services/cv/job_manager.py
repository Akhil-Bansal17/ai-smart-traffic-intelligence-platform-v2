"""
Analysis Job Manager and Background Worker Service.
Phase 17: Analysis Job Orchestration & Real-Time Processing Foundation.

Coordinates the lifecycle of asynchronous video analysis operations:
- Manages concurrency bounds via MAX_CONCURRENT_ANALYSIS_JOBS
- Handles explicit state machine transitions (QUEUED -> RUNNING -> COMPLETED / FAILED / CANCELLED)
- Cooperative non-blocking cancellation via thread cancellation tokens
- Honest frame-level progress tracking with periodic DB sync
- Stale RUNNING job recovery at server startup
- Preserves data provenance and ensures zero side effects on dashboard
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.analysis import AnalysisSession
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.video import Video
from app.schemas.analysis import AnalysisRunRequest
from app.schemas.analysis_job import AnalysisJobCreateRequest, AnalysisJobResponse
from app.schemas.counting import CountingLineSchema, Point2DSchema
from app.schemas.lane_analysis import LaneRegionSchema
from app.services.cv.analysis_persistence_service import (
    AnalysisPersistenceService,
    get_analysis_persistence_service,
)
from app.services.cv.tracker import JobCancelledException

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class AnalysisJobManager:
    """
    Central orchestration engine for background video analysis operations.
    Thread-safe, bounded in-process worker pool for single-node execution.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        persistence_service: Optional[AnalysisPersistenceService] = None,
        session_factory: Optional[Any] = None,
    ):
        self._max_workers = max_workers or settings.max_concurrent_analysis_jobs
        self._persistence_service = persistence_service or get_analysis_persistence_service()
        self._session_factory = session_factory or SessionLocal
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="analysis-worker",
        )
        self._lock = threading.Lock()
        self._cancellation_events: Dict[str, threading.Event] = {}
        self._active_job_ids: Set[str] = set()
        self._shutdown = False

    def set_session_factory(self, session_factory: Any) -> None:
        """Configures the sessionmaker used by worker threads (used for testing)."""
        self._session_factory = session_factory

    def submit_job(
        self,
        db: Session,
        request: AnalysisJobCreateRequest,
    ) -> AnalysisJob:
        """
        Validates the analysis request, creates a persistent AnalysisJob record in QUEUED status,
        and schedules it for background execution.
        """
        video_id = request.video_id

        # 1. Validate video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise AppException(
                f"Video with ID '{video_id}' not found.",
                code="video_not_found",
                status_code=404,
            )

        # 2. Validate video file exists on disk
        storage_path = Path(video.storage_path)
        if not storage_path.exists():
            raise AppException(
                f"Underlying video file '{video.original_filename}' is missing from server storage.",
                code="file_not_found",
                status_code=404,
            )

        # 3. Duplicate active job check (Idempotency / conflict protection)
        active_job = (
            db.query(AnalysisJob)
            .filter(
                AnalysisJob.video_id == video_id,
                AnalysisJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
            )
            .first()
        )
        if active_job:
            raise AppException(
                f"An active analysis job '{active_job.id}' is already {active_job.status} for video '{video_id}'.",
                code="duplicate_active_job",
                status_code=409,
            )

        # 4. Build configuration snapshot
        config_snapshot: Dict[str, Any] = {
            "analysis_type": request.analysis_type,
            "confidence_threshold": request.confidence_threshold,
            "processing_fps": request.processing_fps or settings.processing_fps,
            "max_frames": request.max_frames or 100,
            "iou_threshold": request.iou_threshold,
            "persistence_threshold": request.persistence_threshold or 2,
            "counting_line": request.counting_line.model_dump() if request.counting_line else None,
            "lanes": [lane.model_dump() for lane in request.lanes] if request.lanes else None,
        }

        # 5. Determine provenance categorization
        if video.provenance_verified:
            provenance_category = "real_analysis_job"
            is_synthetic = False
        elif video.source_type == "synthetic":
            provenance_category = "synthetic_analysis_job"
            is_synthetic = True
        else:
            provenance_category = "unverified_analysis_job"
            is_synthetic = False

        # 6. Estimate total frames if known from video metadata
        estimated_total_frames: Optional[int] = None
        target_fps = request.processing_fps or settings.processing_fps
        max_f = request.max_frames or 100
        effective_max_frames = min(max_f, 300)

        if video.frame_count > 0 and video.fps > 0:
            step = max(1, int(round(video.fps / target_fps))) if target_fps > 0 else 1
            sampled_count = max(1, video.frame_count // step)
            estimated_total_frames = min(effective_max_frames, sampled_count)
        else:
            estimated_total_frames = effective_max_frames

        # 7. Create persistent AnalysisJob record
        job = AnalysisJob(
            video_id=video.id,
            status=JobStatus.QUEUED.value,
            analysis_type=request.analysis_type,
            progress=0.0,
            frames_processed=0,
            total_frames=estimated_total_frames,
            config_snapshot=config_snapshot,
            provenance_category=provenance_category,
            is_synthetic=is_synthetic,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(
            "Created AnalysisJob %s for video %s in QUEUED status (max_concurrent=%s)",
            job.id,
            video.id,
            self._max_workers,
        )

        # 8. Dispatch to background executor
        self._dispatch_job(job.id)

        return job

    def cancel_job(self, db: Session, job_id: str) -> AnalysisJob:
        """
        Requests cooperative cancellation of a queued or running job.
        Rejects cancellation of terminal jobs (COMPLETED, FAILED, CANCELLED).
        """
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            raise AppException(
                f"Analysis job with ID '{job_id}' not found.",
                code="job_not_found",
                status_code=404,
            )

        if job.status in (
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
        ):
            raise AppException(
                f"Cannot cancel analysis job '{job_id}' in terminal state '{job.status}'.",
                code="cannot_cancel_terminal_job",
                status_code=400,
            )

        with self._lock:
            if job.status == JobStatus.QUEUED.value:
                # Immediate transition for queued jobs
                job.status = JobStatus.CANCELLED.value
                job.cancellation_requested = True
                job.completed_at = utcnow()
                job.updated_at = utcnow()
                db.commit()
                db.refresh(job)
                logger.info("Cancelled QUEUED AnalysisJob %s immediately", job.id)
                return job

            elif job.status == JobStatus.RUNNING.value:
                # Signal cooperative cancellation to running worker
                job.cancellation_requested = True
                job.updated_at = utcnow()
                db.commit()
                db.refresh(job)

                event = self._cancellation_events.get(job_id)
                if event:
                    event.set()
                    logger.info("Signalled cooperative cancellation for RUNNING AnalysisJob %s", job.id)
                else:
                    # Worker not actively tracked or already exiting
                    job.status = JobStatus.CANCELLED.value
                    job.completed_at = utcnow()
                    job.updated_at = utcnow()
                    db.commit()
                    db.refresh(job)
                return job

        return job

    def recover_stale_jobs(self, db: Session) -> int:
        """
        At application startup, finds any jobs left in RUNNING status (due to prior server crash/restart)
        and deterministically marks them as FAILED with a recovery error code.
        """
        stale_jobs = db.query(AnalysisJob).filter(AnalysisJob.status == JobStatus.RUNNING.value).all()
        recovered_count = len(stale_jobs)

        for job in stale_jobs:
            job.status = JobStatus.FAILED.value
            job.error_code = "process_restarted_stale_job"
            job.error_message = "Analysis job was interrupted by application shutdown or server restart."
            job.completed_at = utcnow()
            job.updated_at = utcnow()

        if stale_jobs:
            db.commit()
            logger.warning("Startup recovery: transitioned %s stale RUNNING jobs to FAILED", recovered_count)

        return recovered_count

    def _dispatch_job(self, job_id: str) -> None:
        """Submits job execution task to the thread pool executor."""
        if self._shutdown:
            logger.warning("Job dispatch rejected for %s: job manager is shutting down", job_id)
            return

        self._executor.submit(self._execute_job_task, job_id)

    def _execute_job_task(self, job_id: str) -> None:
        """
        Worker thread entrypoint for executing a single analysis job.
        Maintains isolated DB sessions and coordinates with the CV pipeline.
        """
        db = self._session_factory()
        cancellation_token = threading.Event()

        try:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                logger.error("Worker could not find AnalysisJob %s", job_id)
                return

            # Check if job was cancelled while in queue
            if job.status == JobStatus.CANCELLED.value or job.cancellation_requested:
                logger.info("Job %s was cancelled before execution started", job_id)
                return

            # Transition state QUEUED -> RUNNING
            job.status = JobStatus.RUNNING.value
            job.started_at = utcnow()
            job.updated_at = utcnow()
            db.commit()
            db.refresh(job)

            with self._lock:
                self._cancellation_events[job_id] = cancellation_token
                self._active_job_ids.add(job_id)

            video = db.query(Video).filter(Video.id == job.video_id).first()
            if not video:
                raise AppException(f"Video {job.video_id} disappeared from database", code="video_not_found")

            # Parse config snapshot into AnalysisRunRequest
            config = job.config_snapshot or {}
            counting_line_schema = None
            if config.get("counting_line"):
                cl_data = config["counting_line"]
                counting_line_schema = CountingLineSchema(
                    p1=Point2DSchema(**cl_data["p1"]),
                    p2=Point2DSchema(**cl_data["p2"]),
                    label=cl_data.get("label", "main_line"),
                    direction_a_to_b=cl_data.get("direction_a_to_b", "inbound"),
                    direction_b_to_a=cl_data.get("direction_b_to_a", "outbound"),
                )

            lane_schemas = None
            if config.get("lanes"):
                lane_schemas = [
                    LaneRegionSchema(
                        lane_id=l["lane_id"],
                        name=l["name"],
                        polygon=l["polygon"],
                        direction_hint=l.get("direction_hint"),
                    )
                    for l in config["lanes"]
                ]

            run_request = AnalysisRunRequest(
                analysis_type=config.get("analysis_type", job.analysis_type),
                confidence_threshold=config.get("confidence_threshold"),
                processing_fps=config.get("processing_fps"),
                max_frames=config.get("max_frames"),
                iou_threshold=config.get("iou_threshold"),
                counting_line=counting_line_schema,
                lanes=lane_schemas,
                persistence_threshold=config.get("persistence_threshold", 2),
            )

            # Define safe progress callback
            def progress_callback(frames_done: int, total_f: Optional[int], current_fps: float) -> None:
                try:
                    prog_db = self._session_factory()
                    try:
                        j = prog_db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
                        if j and j.status == JobStatus.RUNNING.value:
                            j.frames_processed = frames_done
                            j.total_frames = total_f
                            if total_f and total_f > 0:
                                j.progress = round(min(1.0, frames_done / total_f), 4)
                            else:
                                j.progress = None
                            j.processing_fps = current_fps
                            j.updated_at = utcnow()
                            prog_db.commit()
                    finally:
                        prog_db.close()
                except Exception as prog_err:
                    logger.debug("Progress DB write skipped for job %s: %s", job_id, prog_err)

            # Execute CV pipeline stages
            session = self._persistence_service.execute_and_persist(
                video=video,
                db=db,
                request=run_request,
                progress_callback=progress_callback,
                cancellation_token=cancellation_token,
            )

            # Transition state RUNNING -> COMPLETED
            job.status = JobStatus.COMPLETED.value
            job.session_id = session.id
            job.progress = 1.0
            job.frames_processed = session.total_frames_processed
            job.total_frames = session.total_frames_processed
            job.completed_at = utcnow()
            job.updated_at = utcnow()
            db.commit()

            logger.info("AnalysisJob %s COMPLETED (AnalysisSession %s)", job_id, session.id)

        except JobCancelledException:
            try:
                db.rollback()
                job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
                if job:
                    job.status = JobStatus.CANCELLED.value
                    job.completed_at = utcnow()
                    job.updated_at = utcnow()
                    db.commit()
                logger.info("AnalysisJob %s successfully CANCELLED", job_id)
            except Exception as cancel_save_err:
                logger.error("Failed persisting cancelled status for job %s: %s", job_id, cancel_save_err)

        except Exception as err:
            try:
                db.rollback()
                job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED.value
                    job.error_code = "analysis_execution_failed"
                    job.error_message = str(err)[:1000]
                    job.completed_at = utcnow()
                    job.updated_at = utcnow()
                    db.commit()
                logger.error("AnalysisJob %s FAILED: %s", job_id, err)
            except Exception as fail_save_err:
                logger.error("Failed persisting failed status for job %s: %s", job_id, fail_save_err)

        finally:
            with self._lock:
                self._cancellation_events.pop(job_id, None)
                self._active_job_ids.discard(job_id)
            db.close()

    def shutdown(self, wait: bool = False) -> None:
        """Gracefully shuts down the background worker pool."""
        self._shutdown = True
        with self._lock:
            for event in self._cancellation_events.values():
                event.set()
        self._executor.shutdown(wait=wait, cancel_futures=True)
        logger.info("AnalysisJobManager worker pool shut down")


# Global module singleton
_job_manager: Optional[AnalysisJobManager] = None


def get_analysis_job_manager() -> AnalysisJobManager:
    """Returns the singleton AnalysisJobManager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = AnalysisJobManager()
    return _job_manager
