"""Real OpenCV 5 object detection + background-subtraction motion channel."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .config import DetectorConfig, MotionConfig, PERSON_CLASS_ID


@dataclass(frozen=True)
class Detection:
    """One person hypothesis in pixel coordinates."""

    x1: int
    y1: int
    x2: int
    y2: int
    score: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def foot_point(self) -> tuple[float, float]:
        """Ground contact point: better than the centroid for zone tests."""
        return ((self.x1 + self.x2) / 2.0, float(self.y2))

    @property
    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


class PersonDetector:
    """SSD-MobileNet-v1 running through OpenCV 5's DNN engine.

    The graph is the tf2onnx COCO export: four outputs, 100 detections, already
    NMS'd. OpenCV 5 validates the declared input layout (uint8 NHWC) instead of
    silently accepting a float32 NCHW blob, which is why the tensor is built by
    hand rather than with cv2.dnn.blobFromImage.
    """

    def __init__(self, cfg: DetectorConfig = DetectorConfig()) -> None:
        self.cfg = cfg
        if not cfg.model_path.exists():
            raise FileNotFoundError(
                f"ONNX model missing at {cfg.model_path}; run scripts/fetch_assets.py"
            )
        self.net = cv2.dnn.readNetFromONNX(str(cfg.model_path))
        self.output_names = list(self.net.getUnconnectedOutLayersNames())

    def detect(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        tensor = cv2.resize(frame, self.cfg.input_size).astype(np.uint8)[None]
        self.net.setInput(tensor)
        # One forward pass returns every requested output; calling forward(name)
        # per output would re-run the graph for each tensor.
        raw = self.net.forward(self.output_names)
        outputs = dict(zip(self.output_names, raw))

        boxes = outputs["detection_boxes:0"][0]
        classes = outputs["detection_classes:0"][0]
        scores = outputs["detection_scores:0"][0]
        num = int(np.ravel(outputs["num_detections:0"])[0])

        results: list[Detection] = []
        for i in range(min(num, len(scores))):
            score = float(scores[i])
            if score < self.cfg.score_threshold:
                break
            if int(classes[i]) != PERSON_CLASS_ID:
                continue
            y1, x1, y2, x2 = (float(v) for v in boxes[i])
            box_w, box_h = (x2 - x1) * w, (y2 - y1) * h
            if box_h <= 0 or box_w <= 0:
                continue
            if (box_w * box_h) / (w * h) < self.cfg.min_box_area_ratio:
                continue
            if box_h < self.cfg.min_box_height_px:
                # Suppresses small static false positives (bollards, bins) that
                # the 300x300 SSD input cannot separate from a distant person.
                continue
            if box_h / box_w > self.cfg.max_aspect_ratio:
                continue
            results.append(
                Detection(
                    x1=int(x1 * w),
                    y1=int(y1 * h),
                    x2=int(x2 * w),
                    y2=int(y2 * h),
                    score=score,
                )
            )
        return results


class MotionChannel:
    """MOG2 background subtraction: a model-free second signal.

    Kept separate from the detector so the report can show agreement between a
    learned detector and classical motion analysis on the same frames.
    """

    def __init__(self, cfg: MotionConfig = MotionConfig()) -> None:
        self.cfg = cfg
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=cfg.history,
            varThreshold=cfg.var_threshold,
            detectShadows=cfg.detect_shadows,
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.kernel = kernel

    def apply(self, frame: np.ndarray) -> tuple[np.ndarray, list[tuple[int, int, int, int]], float]:
        raw = self.subtractor.apply(frame)
        # 255 for foreground, 127 for shadow, 0 for background.
        mask = cv2.threshold(raw, 200, 255, cv2.THRESH_BINARY)[1]
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel, iterations=self.cfg.open_iterations)
        mask = cv2.dilate(mask, self.kernel, iterations=self.cfg.dilate_iterations)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for contour in contours:
            if cv2.contourArea(contour) < self.cfg.min_contour_area:
                continue
            boxes.append(cv2.boundingRect(contour))
        ratio = float(np.count_nonzero(mask)) / float(mask.size)
        return mask, boxes, ratio
