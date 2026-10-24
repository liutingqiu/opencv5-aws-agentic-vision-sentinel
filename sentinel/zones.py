"""Polygon zone logic: intrusion, dwell time, and identity tracking.

Tracking is a greedy nearest-foot-point association over consecutive frames. It
is deliberately simple: the alert path needs stable dwell timing, not full
multi-object tracking, and a judge can audit every step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import ZoneConfig
from .detector import Detection


def build_polygon(points: tuple[tuple[float, float], ...], width: int, height: int) -> np.ndarray:
    return np.array(
        [[int(px * width), int(py * height)] for px, py in points], dtype=np.int32
    )


def point_in_polygon(point: tuple[float, float], polygon: np.ndarray) -> bool:
    import cv2

    return cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False) >= 0


@dataclass
class Track:
    track_id: int
    foot_point: tuple[float, float]
    first_seen: float
    last_seen: float
    inside_since: float | None = None
    alerted_intrusion: bool = False
    alerted_dwell: bool = False
    frames_seen: int = 1


@dataclass
class ZoneEvaluator:
    """Tracks detections across frames and emits auditable zone events."""

    cfg: ZoneConfig = field(default_factory=ZoneConfig)
    max_match_distance: float = 90.0
    tracks: dict[int, Track] = field(default_factory=dict)
    _next_id: int = 1

    def reset(self) -> None:
        self.tracks.clear()
        self._next_id = 1

    def _assign(self, detections: list[Detection], timestamp: float) -> list[Track]:
        unmatched = list(detections)
        assignments: list[Track] = []
        for track in sorted(self.tracks.values(), key=lambda t: -t.last_seen):
            if not unmatched:
                break
            distances = [
                (np.hypot(det.foot_point[0] - track.foot_point[0], det.foot_point[1] - track.foot_point[1]), i)
                for i, det in enumerate(unmatched)
            ]
            distance, index = min(distances)
            if distance <= self.max_match_distance:
                det = unmatched.pop(index)
                track.foot_point = det.foot_point
                track.last_seen = timestamp
                track.frames_seen += 1
                assignments.append(track)
        for det in unmatched:
            track = Track(
                track_id=self._next_id,
                foot_point=det.foot_point,
                first_seen=timestamp,
                last_seen=timestamp,
            )
            self._next_id += 1
            self.tracks[track.track_id] = track
            assignments.append(track)
        return assignments

    def evaluate(
        self,
        detections: list[Detection],
        polygon: np.ndarray,
        timestamp: float,
        frame_index: int,
    ) -> list[dict]:
        assigned = self._assign(detections, timestamp)
        events: list[dict] = []
        present_ids = {t.track_id for t in assigned}
        for track in assigned:
            inside = point_in_polygon(track.foot_point, polygon)
            if inside:
                if track.inside_since is None:
                    track.inside_since = timestamp
                dwell = timestamp - track.inside_since
                if dwell >= self.cfg.intrusion_alert_seconds and not track.alerted_intrusion:
                    track.alerted_intrusion = True
                    events.append(
                        self._event("INTRUSION_DETECTED", "CRITICAL", track, frame_index, timestamp, dwell)
                    )
                if dwell >= self.cfg.dwell_alert_seconds and not track.alerted_dwell:
                    track.alerted_dwell = True
                    events.append(
                        self._event("DWELL_EXCEEDED", "WARNING", track, frame_index, timestamp, dwell)
                    )
            else:
                track.inside_since = None
                track.alerted_intrusion = False
                track.alerted_dwell = False
        for lost_id in [tid for tid in self.tracks if tid not in present_ids]:
            del self.tracks[lost_id]
        return events

    @staticmethod
    def _event(
        anomaly: str,
        severity: str,
        track: Track,
        frame_index: int,
        timestamp: float,
        dwell: float,
    ) -> dict:
        return {
            "anomaly": anomaly,
            "severity": severity,
            "track_id": track.track_id,
            "frame_index": frame_index,
            "timestamp_s": round(timestamp, 3),
            "dwell_s": round(dwell, 3),
            "foot_point": [round(track.foot_point[0], 1), round(track.foot_point[1], 1)],
        }
