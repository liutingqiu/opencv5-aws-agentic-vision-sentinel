"""HSV warm-hue proxy for heat, sparks, and hot metal.

Documented as a proxy in the technical report: the sample clips carry no
radiometric metadata, so this stage reports colour evidence only.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import ThermalConfig


class ThermalProxy:
    def __init__(self, cfg: ThermalConfig = ThermalConfig()) -> None:
        self.cfg = cfg

    def analyse(self, frame: np.ndarray, roi_mask: np.ndarray | None = None) -> dict:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        for low, high in self.cfg.hue_ranges:
            band = cv2.inRange(
                hsv,
                np.array([low, self.cfg.min_saturation, self.cfg.min_value]),
                np.array([high, 255, 255]),
            )
            mask = cv2.bitwise_or(mask, band)
        if roi_mask is not None:
            mask = cv2.bitwise_and(mask, roi_mask)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        hottest = 0.0
        area_ratio = float(np.count_nonzero(mask)) / float(mask.size)
        found = area_ratio >= self.cfg.min_area_ratio
        if found:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest)
                hottest = float(np.max(hsv[:, :, 2][mask > 0]))
                return {
                    "detected": True,
                    "area_ratio": round(area_ratio, 5),
                    "peak_value": round(hottest, 1),
                    "bbox": [int(x), int(y), int(w), int(h)],
                }
        return {"detected": False, "area_ratio": round(area_ratio, 5), "peak_value": 0.0, "bbox": None}
