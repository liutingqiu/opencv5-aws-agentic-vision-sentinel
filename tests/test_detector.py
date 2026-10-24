"""Detector tests against real decoded frames."""

from __future__ import annotations

import cv2
import pytest

from sentinel.config import DEFAULT_SOURCE, DetectorConfig
from sentinel.detector import PersonDetector


@pytest.fixture(scope="module")
def detector() -> PersonDetector:
    return PersonDetector(DetectorConfig())


def _frame_at(index: int):
    cap = cv2.VideoCapture(str(DEFAULT_SOURCE))
    frame = None
    for _ in range(index + 1):
        ok, frame = cap.read()
        if not ok:
            break
    cap.release()
    return frame


def test_detects_people_on_sample_frame(detector: PersonDetector) -> None:
    frame = _frame_at(360)
    assert frame is not None
    detections = detector.detect(frame)
    assert len(detections) >= 3, "the sample clip has several visible pedestrians"
    for det in detections:
        assert 0.42 <= det.score <= 1.0
        assert det.x2 > det.x1 and det.y2 > det.y1
        assert det.y2 <= frame.shape[0] + 2


def test_boxes_respect_minimum_height(detector: PersonDetector) -> None:
    frame = _frame_at(120)
    detections = detector.detect(frame)
    assert all((det.y2 - det.y1) >= DetectorConfig().min_box_height_px for det in detections)


def test_scores_are_descending(detector: PersonDetector) -> None:
    frame = _frame_at(240)
    detections = detector.detect(frame)
    scores = [d.score for d in detections]
    assert scores == sorted(scores, reverse=True)
