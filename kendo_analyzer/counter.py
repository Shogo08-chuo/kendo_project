from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from kendo_analyzer.models import Detection, TARGET_WAZA


@dataclass
class StrikeCounter:
    target_waza: Iterable[str] = TARGET_WAZA
    dedupe_seconds: float = 5.0
    counts: Dict[str, int] = field(init=False)
    last_detected_time: Dict[str, float] = field(init=False)
    accepted_detections: List[Detection] = field(default_factory=list)

    def __post_init__(self):
        normalized = tuple(waza.lower() for waza in self.target_waza)
        self.counts = {waza: 0 for waza in normalized}
        self.last_detected_time = {waza: float("-inf") for waza in normalized}

    def register(self, detection: Detection) -> bool:
        name = detection.normalized_name
        if name not in self.counts:
            return False

        timestamp_sec = detection.timestamp_sec
        if timestamp_sec is None:
            timestamp_sec = self.last_detected_time[name] + self.dedupe_seconds + 1

        if timestamp_sec - self.last_detected_time[name] <= self.dedupe_seconds:
            return False

        self.counts[name] += 1
        self.last_detected_time[name] = timestamp_sec
        self.accepted_detections.append(
            Detection(
                name=detection.name,
                confidence=detection.confidence,
                timestamp_sec=timestamp_sec,
            )
        )
        return True
