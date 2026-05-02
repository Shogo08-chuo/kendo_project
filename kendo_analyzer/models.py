from dataclasses import dataclass
from typing import Iterable, Optional


TARGET_WAZA = ("men", "kote", "do")


@dataclass(frozen=True)
class Detection:
    name: str
    confidence: float
    timestamp_sec: Optional[float] = None

    @property
    def normalized_name(self) -> str:
        return self.name.lower()


def detection_from_label(label: dict, timestamp_sec: Optional[float] = None) -> Detection:
    return Detection(
        name=str(label["Name"]),
        confidence=float(label["Confidence"]),
        timestamp_sec=timestamp_sec,
    )


def best_detection(labels: Iterable[dict], timestamp_sec: Optional[float] = None) -> Optional[Detection]:
    labels = list(labels)
    if not labels:
        return None
    return detection_from_label(max(labels, key=lambda item: item["Confidence"]), timestamp_sec)


def is_target_waza(name: str) -> bool:
    return name.lower() in TARGET_WAZA
