"""Zone logic: polygon containment, intrusion and dwell timing."""

from __future__ import annotations

import numpy as np

from sentinel.config import ZoneConfig
from sentinel.detector import Detection
from sentinel.zones import ZoneEvaluator, build_polygon, point_in_polygon


def _square() -> np.ndarray:
    return build_polygon(((0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)), 100, 100)


def test_point_in_polygon_matches_geometry() -> None:
    polygon = _square()
    assert point_in_polygon((50, 50), polygon)
    assert not point_in_polygon((5, 5), polygon)


def test_intrusion_fires_after_threshold() -> None:
    evaluator = ZoneEvaluator(ZoneConfig(intrusion_alert_seconds=0.6, dwell_alert_seconds=2.0))
    polygon = _square()
    det = Detection(45, 20, 55, 70, 0.9)  # foot point (50, 70) sits inside the square
    assert evaluator.evaluate([det], polygon, 0.0, 0) == []
    events = evaluator.evaluate([det], polygon, 0.7, 7)
    assert [e["anomaly"] for e in events] == ["INTRUSION_DETECTED"]
    assert events[0]["severity"] == "CRITICAL"


def test_dwell_fires_once_per_track() -> None:
    evaluator = ZoneEvaluator(ZoneConfig(intrusion_alert_seconds=0.1, dwell_alert_seconds=1.0))
    polygon = _square()
    det = Detection(45, 20, 55, 70, 0.9)
    fired: list[str] = []
    for step in range(30):
        fired += [e["anomaly"] for e in evaluator.evaluate([det], polygon, step * 0.1, step)]
    assert fired.count("INTRUSION_DETECTED") == 1
    assert fired.count("DWELL_EXCEEDED") == 1


def test_leaving_zone_resets_track() -> None:
    evaluator = ZoneEvaluator(ZoneConfig(intrusion_alert_seconds=0.1, dwell_alert_seconds=99.0))
    polygon = _square()
    inside = Detection(45, 20, 55, 70, 0.9)
    outside = Detection(400, 400, 420, 450, 0.9)
    for step in range(5):
        evaluator.evaluate([inside], polygon, step * 0.1, step)
    for step in range(5, 12):
        evaluator.evaluate([outside], polygon, step * 0.1, step)
    events = evaluator.evaluate([inside], polygon, 1.3, 13)
    assert events == [], "a fresh entry must re-arm only after re-entering the zone"
