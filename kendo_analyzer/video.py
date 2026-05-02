from dataclasses import dataclass
from typing import Callable, Optional

import cv2

from kendo_analyzer.config import AppConfig
from kendo_analyzer.counter import StrikeCounter
from kendo_analyzer.models import Detection


@dataclass(frozen=True)
class VideoProgress:
    current_frame: int
    total_frames: int
    current_time_sec: float
    progress_ratio: float
    accepted_detection: Optional[Detection] = None


@dataclass(frozen=True)
class VideoAnalysisResult:
    counts: dict[str, int]
    detections: list[Detection]
    processed_frames: int
    total_frames: int
    completed: bool = True
    error_message: Optional[str] = None


ProgressCallback = Callable[[VideoProgress], None]


def analyze_video_file(
    video_path: str,
    detector,
    config: AppConfig,
    on_progress: Optional[ProgressCallback] = None,
) -> VideoAnalysisResult:
    cap = cv2.VideoCapture(video_path)

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or total_frames <= 0:
            return VideoAnalysisResult(
                counts={"men": 0, "kote": 0, "do": 0},
                detections=[],
                processed_frames=0,
                total_frames=0,
                completed=False,
                error_message="動画を読み込めませんでした。",
            )

        counter = StrikeCounter(dedupe_seconds=config.dedupe_seconds)
        frame_step = max(int(fps * config.frame_interval_seconds), 1)
        current_frame = 0

        while cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret:
                break

            encoded, buffer = cv2.imencode(".jpg", frame)
            if not encoded:
                current_frame += frame_step
                continue

            current_time_sec = current_frame / fps
            try:
                detections = detector.detect_image_bytes(
                    buffer.tobytes(),
                    min_confidence=config.video_min_confidence,
                    timestamp_sec=current_time_sec,
                )
            except Exception as exc:
                return VideoAnalysisResult(
                    counts=dict(counter.counts),
                    detections=list(counter.accepted_detections),
                    processed_frames=current_frame,
                    total_frames=total_frames,
                    completed=False,
                    error_message=str(exc),
                )

            for detection in detections:
                accepted = counter.register(detection)
                if accepted and on_progress:
                    on_progress(
                        VideoProgress(
                            current_frame=current_frame,
                            total_frames=total_frames,
                            current_time_sec=current_time_sec,
                            progress_ratio=min(current_frame / total_frames, 1.0),
                            accepted_detection=counter.accepted_detections[-1],
                        )
                    )

            if on_progress:
                on_progress(
                    VideoProgress(
                        current_frame=current_frame,
                        total_frames=total_frames,
                        current_time_sec=current_time_sec,
                        progress_ratio=min(current_frame / total_frames, 1.0),
                    )
                )

            current_frame += frame_step

        return VideoAnalysisResult(
            counts=dict(counter.counts),
            detections=list(counter.accepted_detections),
            processed_frames=min(current_frame, total_frames),
            total_frames=total_frames,
        )
    finally:
        cap.release()
