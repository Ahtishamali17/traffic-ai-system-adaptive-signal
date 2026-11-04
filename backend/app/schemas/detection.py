"""
app/schemas/detection.py
--------------------------------------------------------------------
Pydantic request/response models for the detection API.
Keeping these separate from DB models (app/models) so the wire
format can evolve independently of storage format.
--------------------------------------------------------------------
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.signal import AdaptiveSignalConfig


class SourceType(str, Enum):
    """Where the video frames come from."""
    WEBCAM = "webcam"
    RTSP = "rtsp"
    IP_CAMERA = "ip_camera"
    UPLOADED_FILE = "uploaded_file"


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class LinePoint(BaseModel):
    x: int
    y: int


class CountingLineConfig(BaseModel):
    """Defines a virtual line as two points in frame-pixel coordinates."""
    name: str = "main"
    point_a: LinePoint
    point_b: LinePoint
    entry_label: str = "IN"
    exit_label: str = "OUT"


class ViolationConfig(BaseModel):
    """Optional violation-detection configuration for a session."""
    enable_violations: bool = False
    correct_direction_deg: Optional[float] = Field(
        None, description="0=right,90=down,180=left,270=up. Required to enable wrong-direction detection."
    )
    lane_polygon: Optional[list[LinePoint]] = Field(None, description="3+ points defining the allowed lane area")
    stop_line_a: Optional[LinePoint] = None
    stop_line_b: Optional[LinePoint] = Field(None, description="Both stop_line points required for red-light-jump detection")
    no_parking_zone: Optional[list[LinePoint]] = Field(None, description="3+ points defining a no-parking polygon")
    no_parking_max_seconds: float = Field(30.0, ge=5.0)
    enable_u_turn_detection: bool = True
    # Simulated traffic signal cycle (real deployments would feed real signal state instead)
    signal_red_seconds: float = Field(10.0, gt=0)
    signal_yellow_seconds: float = Field(3.0, gt=0)
    signal_green_seconds: float = Field(10.0, gt=0)


class StartDetectionRequest(BaseModel):
    """Body for POST /detection/start"""
    source_type: SourceType
    source: str = Field(
        ...,
        description=(
            "Webcam device index as a string (e.g. '0'), an RTSP/IP camera "
            "URL (e.g. 'rtsp://user:pass@host/stream'), or an uploaded "
            "file's server-side path/id returned by /detection/upload."
        ),
    )
    camera_id: str = Field(..., description="Logical name for this camera/source, e.g. 'gate-1'")
    confidence_threshold: float = Field(0.4, ge=0.05, le=0.95)
    frame_skip: int = Field(1, ge=1, le=10, description="Process every Nth frame")
    enable_tracking: bool = Field(True, description="Assign permanent IDs via DeepSORT")
    counting_line: Optional[CountingLineConfig] = Field(
        None, description="Virtual line for entry/exit counting. Omit to disable counting."
    )
    pixels_per_meter: Optional[float] = Field(
        None, description="Camera-specific calibration for speed estimation. Falls back to app setting."
    )
    speed_limit_kmph: Optional[float] = Field(
        None, description="Overspeed alert threshold. Falls back to app setting."
    )
    violations: Optional[ViolationConfig] = None
    enable_alerts: bool = Field(False, description="Send Telegram/email alerts for violations & overspeed")
    crowd_threshold: int = Field(15, description="Vehicle count in one frame that triggers a crowded-area alert")
    adaptive_signal: Optional[AdaptiveSignalConfig] = Field(
        None,
        description="Multi-lane adaptive traffic signal: green-light duration adapts to each lane's live vehicle density",
    )

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source must not be empty")
        return v



class VehicleDetection(BaseModel):
    """A single detected vehicle in one frame."""
    class_name: str
    confidence: float
    bbox: BoundingBox
    track_id: Optional[int] = None  # populated once DeepSORT is wired in (Step 3)


class FrameDetectionResult(BaseModel):
    """Result of running detection on a single frame."""
    camera_id: str
    frame_index: int
    timestamp: float  # unix epoch seconds
    detections: list[VehicleDetection]
    inference_ms: float
    fps: float


class SessionInfo(BaseModel):
    """Status snapshot of an active or stopped detection session."""
    session_id: str
    camera_id: str
    source_type: SourceType
    source: str
    status: str  # "running" | "stopped" | "error"
    started_at: float
    total_frames_processed: int
    current_fps: float
    error: Optional[str] = None


class UploadVideoResponse(BaseModel):
    success: bool
    file_id: str
    filename: str
    size_bytes: int
    server_path: str


class StartDetectionResponse(BaseModel):
    success: bool
    session_id: str
    message: str


class StopDetectionResponse(BaseModel):
    success: bool
    message: str
    summary: Optional[SessionInfo] = None
