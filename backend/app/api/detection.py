"""
app/api/detection.py
--------------------------------------------------------------------
REST API for the detection engine:
  POST /api/v1/detection/upload         - upload a video file
  POST /api/v1/detection/start          - start a detection session
  POST /api/v1/detection/stop/{id}      - stop a running session
  GET  /api/v1/detection/sessions       - list all sessions
  GET  /api/v1/detection/sessions/{id}  - get one session's status
  GET  /api/v1/detection/stream/{id}    - MJPEG live annotated stream
--------------------------------------------------------------------
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.detection import (
    SessionInfo,
    SourceType,
    StartDetectionRequest,
    StartDetectionResponse,
    StopDetectionResponse,
    UploadVideoResponse,
)
from app.schemas.signal import IntersectionStatus
from app.schemas.tracking import CountingStats
from app.schemas.violations import ViolationEvent
from app.services.detection_session import session_manager

router = APIRouter(prefix="/detection", tags=["Detection"])
settings = get_settings()

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB


@router.post("/upload", response_model=UploadVideoResponse)
async def upload_video(file: UploadFile = File(...)) -> UploadVideoResponse:
    """
    Upload a recorded video (CCTV export, dashcam clip, drone footage, etc.)
    to be used as a detection source. Returns a server-side path that can
    be passed as `source` to POST /detection/start with source_type=uploaded_file.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_VIDEO_EXTENSIONS)}",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    dest_path = upload_dir / f"{file_id}{ext}"

    size_bytes = 0
    try:
        with open(dest_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                size_bytes += len(chunk)
                if size_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File too large (max 500 MB)")
                out_file.write(chunk)
    except HTTPException:
        dest_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        dest_path.unlink(missing_ok=True)
        logger.exception(f"Upload failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file") from exc

    logger.info(f"Uploaded video saved: {dest_path} ({size_bytes} bytes)")

    return UploadVideoResponse(
        success=True,
        file_id=file_id,
        filename=file.filename or dest_path.name,
        size_bytes=size_bytes,
        server_path=str(dest_path),
    )


@router.post("/start", response_model=StartDetectionResponse)
async def start_detection(payload: StartDetectionRequest) -> StartDetectionResponse:
    """
    Start a detection session against a webcam, RTSP/IP camera stream,
    or a previously uploaded file. Runs in a background thread; use
    GET /detection/stream/{session_id} to view the live annotated feed
    and GET /detection/sessions/{session_id} to poll status.
    """
    source = payload.source
    if payload.source_type == SourceType.UPLOADED_FILE and not Path(source).exists():
        raise HTTPException(status_code=404, detail=f"Uploaded file not found: {source}")

    try:
        session = session_manager.start_session(
            camera_id=payload.camera_id,
            source_type=payload.source_type,
            source=source,
            confidence_threshold=payload.confidence_threshold,
            frame_skip=payload.frame_skip,
            enable_tracking=payload.enable_tracking,
            counting_line=payload.counting_line,
            pixels_per_meter=payload.pixels_per_meter,
            speed_limit_kmph=payload.speed_limit_kmph,
            violations=payload.violations,
            enable_alerts=payload.enable_alerts,
            crowd_threshold=payload.crowd_threshold,
            adaptive_signal=payload.adaptive_signal,
        )
    except Exception as exc:
        logger.exception(f"Failed to start detection session: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to start session: {exc}") from exc

    return StartDetectionResponse(
        success=True,
        session_id=session.session_id,
        message=f"Detection session started for camera '{payload.camera_id}'",
    )


@router.post("/stop/{session_id}", response_model=StopDetectionResponse)
async def stop_detection(session_id: str) -> StopDetectionResponse:
    """Stop a running detection session and release its video source."""
    session = session_manager.stop_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return StopDetectionResponse(
        success=True,
        message="Session stopped",
        summary=session.info(),
    )


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions() -> list[SessionInfo]:
    """List every detection session (running or stopped) in this process."""
    return session_manager.list_sessions()


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Get the current status of a single session."""
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.info()


@router.get("/sessions/{session_id}/counts", response_model=CountingStats)
async def get_counts(session_id: str) -> CountingStats:
    """
    Live entry/exit/class counts for a session with a configured
    counting_line. 404 if the session doesn't exist, 409 if the
    session has no counting line configured yet.
    """
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stats = session.get_counting_stats()
    if stats is None:
        raise HTTPException(
            status_code=409,
            detail="No counting line configured for this session, or no vehicle has crossed it yet",
        )
    return stats


@router.get("/sessions/{session_id}/violations", response_model=list[ViolationEvent])
async def get_recent_violations(session_id: str) -> list[ViolationEvent]:
    """Most recent violation events (up to 50) detected in this session, newest last."""
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.get_recent_violations()


@router.get("/sessions/{session_id}/heatmap")
async def get_heatmap(session_id: str) -> Response:
    """
    A single JPEG snapshot showing accumulated vehicle-traffic density
    for this session, color-mapped over the most recent frame. Re-fetch
    periodically for an updating view (it's a snapshot, not a stream).
    """
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    jpeg = session.get_heatmap_jpeg()
    if jpeg is None:
        raise HTTPException(status_code=409, detail="No frames processed yet for this session")
    return Response(content=jpeg, media_type="image/jpeg")


@router.get("/sessions/{session_id}/signals", response_model=IntersectionStatus)
async def get_signal_status(session_id: str) -> IntersectionStatus:
    """
    Live adaptive traffic signal status: which lane is currently green,
    how many seconds remain, and each lane's current measured density.
    409 if this session wasn't started with an `adaptive_signal` config.
    """
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    status = session.get_signal_status()
    if status is None:
        raise HTTPException(status_code=409, detail="Adaptive signal control is not enabled for this session")
    return status


def _mjpeg_generator(session_id: str):
    """
    Yields multipart/x-mixed-replace JPEG frames for MJPEG streaming.
    Standard trick browsers understand natively via an <img src=...> tag.
    """
    boundary = b"--frame"
    while True:
        session = session_manager.get(session_id)
        if session is None:
            break

        info = session.info()
        if info.status in ("stopped", "error"):
            break

        jpeg = session.get_latest_jpeg()
        if jpeg is not None:
            yield (
                boundary + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                + jpeg + b"\r\n"
            )
        time.sleep(0.03)  # ~30 fps cap on the streaming side, independent of inference speed


@router.get("/stream/{session_id}")
async def stream_detection(session_id: str) -> StreamingResponse:
    """
    Live MJPEG stream of the annotated video for a running session.
    Embed directly in the frontend with:
        <img src="/api/v1/detection/stream/{session_id}" />
    """
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(
        _mjpeg_generator(session_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
