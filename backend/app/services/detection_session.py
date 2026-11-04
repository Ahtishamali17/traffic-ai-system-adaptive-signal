"""
app/services/detection_session.py
--------------------------------------------------------------------
Manages the lifecycle of a "detection session": one running
video-source-in, detect -> track -> count -> speed -> violations ->
alerts -> annotated-frame-out loop for a single camera/video.

Why a thread, not an asyncio task: OpenCV's VideoCapture.read(), YOLO
inference, and DeepSORT matching are all blocking, CPU/GPU-bound
calls. Running them directly in FastAPI's async event loop would
freeze every other request. Each session therefore runs in its own
background thread; the API layer only ever touches thread-safe
shared state (behind a lock) to fetch the latest annotated frame /
stats for streaming.

Multiple simultaneous sessions (multi-camera support) are supported
by keeping a dict of session_id -> DetectionSession.
--------------------------------------------------------------------
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.logging import logger
from app.core.vehicle_classes import get_color
from app.schemas.detection import CountingLineConfig, SessionInfo, SourceType, ViolationConfig
from app.schemas.signal import AdaptiveSignalConfig, IntersectionStatus
from app.schemas.tracking import CountingStats
from app.schemas.violations import PolygonZone, ViolationEvent
from app.services.adaptive_signal import AdaptiveTrafficController
from app.services.alerts import AlertKind, alert_service
from app.services.detector import VehicleDetector, get_detector
from app.services.event_store import save_session_summary, save_vehicle_crossing_event, save_violation
from app.services.heatmap import HeatmapAccumulator
from app.services.line_counter import LineCounter
from app.services.speed_estimator import SpeedEstimator
from app.services.video_source import VideoSource, VideoSourceError
from app.tracking.tracker import VehicleTracker, get_centroid
from app.tracking.trajectory import TrajectoryStore
from app.utils.draw import draw_counting_line, draw_detections, draw_lane_zones, draw_stats_overlay, draw_trail, encode_jpeg
from app.utils.geometry import point_in_polygon
from app.violations.detector import (
    IllegalUTurnDetector,
    LaneViolationDetector,
    NoParkingDetector,
    RedLightJumpDetector,
    SignalCycleSimulator,
    ViolationEngine,
    WrongDirectionDetector,
)

settings = get_settings()

TRACK_STALE_AGE_SECONDS = 30.0
LOITERING_SUSPICIOUS_SECONDS = 120.0  # heuristic threshold for "suspicious vehicle" alert


@dataclass
class _SessionState:
    """Thread-safe mutable state for one session, guarded by `lock`."""
    lock: threading.Lock = field(default_factory=threading.Lock)
    latest_jpeg: bytes | None = None
    total_frames_processed: int = 0
    current_fps: float = 0.0
    status: str = "starting"  # starting | running | stopped | error
    error: str | None = None
    counting_stats: CountingStats | None = None
    recent_violations: list[ViolationEvent] = field(default_factory=list)


def _build_violation_engine(camera_id: str, config: ViolationConfig | None) -> ViolationEngine | None:
    """Constructs a ViolationEngine wired up with only the detectors the caller configured."""
    if config is None or not config.enable_violations:
        return None

    engine = ViolationEngine(camera_id)

    if config.correct_direction_deg is not None:
        engine.wrong_direction = WrongDirectionDetector(correct_direction_deg=config.correct_direction_deg)

    if config.lane_polygon and len(config.lane_polygon) >= 3:
        engine.lane_violation = LaneViolationDetector(lane_polygon=config.lane_polygon)

    if config.stop_line_a and config.stop_line_b:
        engine.red_light = RedLightJumpDetector(config.stop_line_a, config.stop_line_b)
        engine.signal_simulator = SignalCycleSimulator(
            red_seconds=config.signal_red_seconds,
            yellow_seconds=config.signal_yellow_seconds,
            green_seconds=config.signal_green_seconds,
        )

    if config.enable_u_turn_detection:
        engine.u_turn = IllegalUTurnDetector()

    if config.no_parking_zone and len(config.no_parking_zone) >= 3:
        zone = PolygonZone(name="no-parking", points=config.no_parking_zone)
        engine.no_parking = NoParkingDetector(zone, max_stationary_seconds=config.no_parking_max_seconds)

    return engine


class DetectionSession:
    """One running pipeline: video -> detect -> track -> count/speed -> violations -> stream."""

    def __init__(
        self,
        camera_id: str,
        source_type: SourceType,
        source: str,
        confidence_threshold: float,
        frame_skip: int,
        detector: VehicleDetector,
        enable_tracking: bool = True,
        counting_line: CountingLineConfig | None = None,
        pixels_per_meter: float | None = None,
        speed_limit_kmph: float | None = None,
        violations: ViolationConfig | None = None,
        enable_alerts: bool = False,
        crowd_threshold: int = 15,
        adaptive_signal: AdaptiveSignalConfig | None = None,
    ):
        self.session_id = str(uuid.uuid4())
        self.camera_id = camera_id
        self.source_type = source_type
        self.source = source
        self.confidence_threshold = confidence_threshold
        self.frame_skip = frame_skip
        self.detector = detector
        self.enable_tracking = enable_tracking
        self.enable_alerts = enable_alerts
        self.crowd_threshold = crowd_threshold
        self.started_at = time.time()

        self.tracker = VehicleTracker() if enable_tracking else None
        self.trajectory_store = TrajectoryStore(max_age_seconds=TRACK_STALE_AGE_SECONDS)
        self.line_counter = LineCounter(counting_line) if (enable_tracking and counting_line) else None
        self.heatmap: HeatmapAccumulator | None = None  # lazily sized once the first frame's dimensions are known
        self.speed_estimator = (
            SpeedEstimator(
                pixels_per_meter=pixels_per_meter or settings.PIXELS_PER_METER,
                speed_limit_kmph=speed_limit_kmph or settings.SPEED_LIMIT_KMPH,
            )
            if enable_tracking else None
        )
        self.violation_engine = _build_violation_engine(camera_id, violations) if enable_tracking else None
        self.adaptive_signal_controller = (
            AdaptiveTrafficController(camera_id, adaptive_signal)
            if (enable_tracking and adaptive_signal and adaptive_signal.enabled)
            else None
        )
        self._last_signal_tick = time.time()

        self.state = _SessionState()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"det-{self.session_id[:8]}")

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=5)
        with self.state.lock:
            self.state.status = "stopped"
        save_session_summary(self.camera_id, self.session_id, self._final_stats())

    def _final_stats(self) -> CountingStats:
        if self.line_counter:
            return self.line_counter.stats(self.camera_id)
        return CountingStats(camera_id=self.camera_id, total_count=0, entry_count=0, exit_count=0, by_class=[])

    def _handle_violation_events(self, events: list[ViolationEvent]) -> None:
        for event in events:
            save_violation(event)
            with self.state.lock:
                self.state.recent_violations.append(event)
                self.state.recent_violations = self.state.recent_violations[-50:]  # bounded buffer
            if self.enable_alerts:
                alert_service.send(
                    self.camera_id, AlertKind.VIOLATION,
                    f"{event.violation_type.value} - vehicle #{event.track_id} ({event.class_name}): {event.details}",
                )

    def _run(self) -> None:
        try:
            video_source = VideoSource(self.source_type, self.source, self.frame_skip)
        except VideoSourceError as exc:
            logger.error(f"Session {self.session_id}: {exc}")
            with self.state.lock:
                self.state.status = "error"
                self.state.error = str(exc)
            return

        with self.state.lock:
            self.state.status = "running"

        fps_window_start = time.time()
        fps_window_frames = 0
        last_prune = time.time()

        try:
            for frame_index, frame in video_source.frames():
                if self._stop_event.is_set():
                    break

                detections, inference_ms = self.detector.detect(frame)

                if self.heatmap is None:
                    h, w = frame.shape[:2]
                    self.heatmap = HeatmapAccumulator(frame_width=w, frame_height=h)

                speeds_kmph: dict[int, float] = {}
                overspeed_ids: set[int] = set()
                lane_counts: dict[str, int] = (
                    {lane.name: 0 for lane in self.adaptive_signal_controller.config.lanes}
                    if self.adaptive_signal_controller else {}
                )

                if self.enable_tracking and self.tracker is not None:
                    detections = self.tracker.update(detections, frame)
                    now = time.time()

                    for det in detections:
                        if det.track_id is None:
                            continue
                        cx, cy = get_centroid(det.bbox)
                        self.heatmap.add_point(cx, cy)
                        history = self.trajectory_store.update(det.track_id, det.class_name, cx, cy, now)

                        if self.adaptive_signal_controller is not None:
                            for lane in self.adaptive_signal_controller.config.lanes:
                                if point_in_polygon(cx, cy, lane.polygon):
                                    lane_counts[lane.name] += 1
                                    break  # a vehicle belongs to at most one lane

                        if self.speed_estimator is not None:
                            _, avg_speed, is_overspeed = self.speed_estimator.estimate(history)
                            if avg_speed is not None:
                                speeds_kmph[det.track_id] = avg_speed
                            if is_overspeed:
                                overspeed_ids.add(det.track_id)
                                if self.enable_alerts:
                                    alert_service.send(
                                        self.camera_id, AlertKind.OVERSPEED,
                                        f"Vehicle #{det.track_id} ({det.class_name}) at {avg_speed:.0f} km/h",
                                    )

                        if self.line_counter is not None:
                            direction = self.line_counter.update(det.track_id, det.class_name, cx, cy)
                            if direction is not None:
                                save_vehicle_crossing_event(
                                    self.camera_id, det.track_id, det.class_name, direction, now,
                                )

                        if self.violation_engine is not None:
                            events = self.violation_engine.evaluate(
                                det.track_id, det.class_name, cx, cy, history, det.bbox,
                            )
                            self._handle_violation_events(events)

                        if (
                            self.enable_alerts
                            and history.lifetime_seconds > LOITERING_SUSPICIOUS_SECONDS
                            and det.track_id not in getattr(self, "_suspicious_flagged", set())
                        ):
                            self._suspicious_flagged = getattr(self, "_suspicious_flagged", set()) | {det.track_id}
                            alert_service.send(
                                self.camera_id, AlertKind.SUSPICIOUS_VEHICLE,
                                f"Vehicle #{det.track_id} ({det.class_name}) present for "
                                f"{history.lifetime_seconds:.0f}s -- possible loitering",
                            )

                    if self.enable_alerts and len(detections) >= self.crowd_threshold:
                        alert_service.send(
                            self.camera_id, AlertKind.CROWDED_AREA,
                            f"{len(detections)} vehicles detected in one frame (threshold {self.crowd_threshold})",
                        )

                    # Periodic cleanup of tracks that left the frame.
                    if now - last_prune > 5.0:
                        removed = self.trajectory_store.prune_stale(now)
                        if removed:
                            active_ids = set(self.trajectory_store.active_track_ids())
                            if self.line_counter is not None:
                                for tid in self.line_counter.tracked_ids():
                                    if tid not in active_ids:
                                        self.line_counter.remove_track(tid)
                        last_prune = now

                    if self.adaptive_signal_controller is not None:
                        for lane_name, count in lane_counts.items():
                            self.adaptive_signal_controller.update_density(lane_name, count)
                        self.adaptive_signal_controller.tick(now)

                annotated = draw_detections(frame.copy(), detections, speeds_kmph, overspeed_ids)

                if self.enable_tracking:
                    for det in detections:
                        if det.track_id is None:
                            continue
                        history = self.trajectory_store.get(det.track_id)
                        if history:
                            annotated = draw_trail(annotated, list(history.points), get_color(det.class_name))

                if self.line_counter is not None:
                    annotated = draw_counting_line(annotated, self.line_counter.config)

                if self.adaptive_signal_controller is not None:
                    annotated = draw_lane_zones(
                        annotated,
                        self.adaptive_signal_controller.config.lanes,
                        self.adaptive_signal_controller.get_status(),
                    )

                counting_stats = self.line_counter.stats(self.camera_id) if self.line_counter else None

                annotated = draw_stats_overlay(
                    annotated,
                    fps=self.state.current_fps,
                    vehicle_count=len(detections),
                    inference_ms=inference_ms,
                    camera_id=self.camera_id,
                    entry_count=counting_stats.entry_count if counting_stats else None,
                    exit_count=counting_stats.exit_count if counting_stats else None,
                )

                jpeg_bytes = encode_jpeg(annotated)

                fps_window_frames += 1
                elapsed = time.time() - fps_window_start
                if elapsed >= 1.0:
                    fps = fps_window_frames / elapsed
                    fps_window_frames = 0
                    fps_window_start = time.time()
                else:
                    fps = None

                with self.state.lock:
                    self.state.latest_jpeg = jpeg_bytes
                    self.state.total_frames_processed = frame_index + 1
                    if fps is not None:
                        self.state.current_fps = round(fps, 1)
                    if counting_stats is not None:
                        self.state.counting_stats = counting_stats

        except Exception as exc:  # noqa: BLE001 - session loop must never crash the process
            logger.exception(f"Session {self.session_id} crashed: {exc}")
            with self.state.lock:
                self.state.status = "error"
                self.state.error = str(exc)
        finally:
            video_source.release()
            with self.state.lock:
                if self.state.status == "running":
                    self.state.status = "stopped"
            logger.info(f"Session {self.session_id} loop ended (status={self.state.status})")

    def get_latest_jpeg(self) -> bytes | None:
        with self.state.lock:
            return self.state.latest_jpeg

    def get_heatmap_jpeg(self) -> bytes | None:
        """Renders the accumulated density heatmap over the most recent frame."""
        with self.state.lock:
            latest_jpeg = self.state.latest_jpeg
        if latest_jpeg is None or self.heatmap is None:
            return None

        import cv2
        import numpy as np

        from app.utils.draw import encode_jpeg

        frame = cv2.imdecode(np.frombuffer(latest_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return None
        overlay = self.heatmap.render_overlay(frame)
        return encode_jpeg(overlay)

    def get_counting_stats(self) -> CountingStats | None:
        with self.state.lock:
            return self.state.counting_stats

    def get_recent_violations(self) -> list[ViolationEvent]:
        with self.state.lock:
            return list(self.state.recent_violations)

    def get_signal_status(self) -> IntersectionStatus | None:
        if self.adaptive_signal_controller is None:
            return None
        return self.adaptive_signal_controller.get_status()

    def info(self) -> SessionInfo:
        with self.state.lock:
            return SessionInfo(
                session_id=self.session_id,
                camera_id=self.camera_id,
                source_type=self.source_type,
                source=self.source,
                status=self.state.status,
                started_at=self.started_at,
                total_frames_processed=self.state.total_frames_processed,
                current_fps=self.state.current_fps,
                error=self.state.error,
            )


class SessionManager:
    """Registry of all active/stopped detection sessions for this process."""

    def __init__(self) -> None:
        self._sessions: dict[str, DetectionSession] = {}
        self._lock = threading.Lock()

    def start_session(
        self,
        camera_id: str,
        source_type: SourceType,
        source: str,
        confidence_threshold: float,
        frame_skip: int,
        enable_tracking: bool = True,
        counting_line: CountingLineConfig | None = None,
        pixels_per_meter: float | None = None,
        speed_limit_kmph: float | None = None,
        violations: ViolationConfig | None = None,
        enable_alerts: bool = False,
        crowd_threshold: int = 15,
        adaptive_signal: AdaptiveSignalConfig | None = None,
    ) -> DetectionSession:
        detector = get_detector()
        detector.confidence_threshold = confidence_threshold
        session = DetectionSession(
            camera_id=camera_id,
            source_type=source_type,
            source=source,
            confidence_threshold=confidence_threshold,
            frame_skip=frame_skip,
            detector=detector,
            enable_tracking=enable_tracking,
            counting_line=counting_line,
            pixels_per_meter=pixels_per_meter,
            speed_limit_kmph=speed_limit_kmph,
            violations=violations,
            enable_alerts=enable_alerts,
            crowd_threshold=crowd_threshold,
            adaptive_signal=adaptive_signal,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        session.start()
        logger.info(f"Started session {session.session_id} for camera '{camera_id}'")
        return session

    def get(self, session_id: str) -> DetectionSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def stop_session(self, session_id: str) -> DetectionSession | None:
        session = self.get(session_id)
        if session is None:
            return None
        session.stop()
        return session

    def list_sessions(self) -> list[SessionInfo]:
        with self._lock:
            sessions = list(self._sessions.values())
        return [s.info() for s in sessions]


# Process-wide singleton (fine for a single-instance deployment; for
# multi-worker/multi-process deployments this would move to Redis).
session_manager = SessionManager()
