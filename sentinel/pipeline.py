"""Frame-by-frame orchestration: OpenCV 5 analysis in, telemetry out."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .config import PipelineConfig
from .detector import MotionChannel, PersonDetector
from .thermal import ThermalProxy
from .zones import ZoneEvaluator, build_polygon


@dataclass
class FrameTelemetry:
    frame_index: int
    timestamp_s: float
    person_count: int
    motion_ratio: float
    motion_boxes: int
    thermal: dict
    inference_ms: float
    total_ms: float
    events: list[dict] = field(default_factory=list)


class SentinelPipeline:
    """Runs detector, motion channel, thermal proxy and zone logic per frame."""

    def __init__(self, cfg: PipelineConfig = PipelineConfig()) -> None:
        self.cfg = cfg
        self.detector = PersonDetector(cfg.detector)
        self.motion = MotionChannel(cfg.motion)
        self.thermal = ThermalProxy(cfg.thermal)
        self.zones = ZoneEvaluator(cfg.zone)

    def run(
        self,
        source: Path,
        out_dir: Path,
        max_frames: int | None = None,
        on_event=None,
    ) -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)
        evidence_dir = out_dir / "evidence"
        evidence_dir.mkdir(exist_ok=True)

        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise RuntimeError(f"cannot open video source {source}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = cv2.VideoWriter(
            str(out_dir / "annotated.mp4"),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )

        polygon = build_polygon(self.cfg.zone.restricted, width, height)
        roi_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(roi_mask, [polygon], 255)

        telemetry: list[FrameTelemetry] = []
        all_events: list[dict] = []
        inference_times: list[float] = []
        frame_index = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if max_frames is not None and frame_index >= max_frames:
                break
            started = time.perf_counter()
            timestamp = frame_index / fps

            t0 = time.perf_counter()
            detections = self.detector.detect(frame)
            inference_ms = (time.perf_counter() - t0) * 1000.0
            inference_times.append(inference_ms)

            motion_mask, motion_boxes, motion_ratio = self.motion.apply(frame)
            thermal = self.thermal.analyse(frame, roi_mask)
            events = self.zones.evaluate(detections, polygon, timestamp, frame_index)
            if thermal["detected"]:
                events.append(
                    {
                        "anomaly": "THERMAL_PROXY_HIGH",
                        "severity": "WARNING",
                        "track_id": None,
                        "frame_index": frame_index,
                        "timestamp_s": round(timestamp, 3),
                        "dwell_s": 0.0,
                        "area_ratio": thermal["area_ratio"],
                    }
                )
            total_ms = (time.perf_counter() - started) * 1000.0

            annotated = self._annotate(frame, detections, motion_boxes, polygon, thermal, events)
            writer.write(annotated)
            for event in events:
                event["frame_index"] = frame_index
                all_events.append(event)
                evidence_path = evidence_dir / f"frame_{frame_index:05d}_{event['anomaly']}.jpg"
                cv2.imwrite(
                    str(evidence_path),
                    self._resize_evidence(annotated),
                    [int(cv2.IMWRITE_JPEG_QUALITY), self.cfg.evidence_jpeg_quality],
                )
                event["evidence_path"] = str(evidence_path.relative_to(out_dir).as_posix())
                if on_event is not None:
                    on_event(event, evidence_path)

            telemetry.append(
                FrameTelemetry(
                    frame_index=frame_index,
                    timestamp_s=round(timestamp, 3),
                    person_count=len(detections),
                    motion_ratio=round(motion_ratio, 5),
                    motion_boxes=len(motion_boxes),
                    thermal=thermal,
                    inference_ms=round(inference_ms, 2),
                    total_ms=round(total_ms, 2),
                    events=events,
                )
            )
            frame_index += 1

        cap.release()
        writer.release()

        events_path = out_dir / "events.jsonl"
        with events_path.open("w", encoding="utf-8") as handle:
            for event in all_events:
                handle.write(json.dumps(event) + "\n")

        summary = self._summarise(telemetry, inference_times, all_events, fps)
        (out_dir / "metrics.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        (out_dir / "frames.json").write_text(
            json.dumps([asdict(t) for t in telemetry[:: max(1, len(telemetry) // 240)]], indent=1),
            encoding="utf-8",
        )
        return summary

    def _resize_evidence(self, frame: np.ndarray) -> np.ndarray:
        max_width = self.cfg.evidence_max_width
        if frame.shape[1] <= max_width:
            return frame
        scale = max_width / frame.shape[1]
        return cv2.resize(frame, (max_width, int(frame.shape[0] * scale)))

    def _annotate(self, frame, detections, motion_boxes, polygon, thermal, events) -> np.ndarray:
        canvas = frame.copy()
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [polygon], (40, 20, 120))
        canvas = cv2.addWeighted(overlay, 0.22, canvas, 0.78, 0)
        cv2.polylines(canvas, [polygon], True, (0, 165, 255), 2)
        cv2.putText(
            canvas,
            "RESTRICTED ZONE",
            (int(polygon[:, 0].min()) + 8, int(polygon[:, 1].min()) - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 165, 255),
            1,
            cv2.LINE_AA,
        )
        for det in detections:
            colour = (0, 220, 0)
            cv2.rectangle(canvas, (det.x1, det.y1), (det.x2, det.y2), colour, 2)
            cv2.putText(
                canvas,
                f"person {det.score:.2f}",
                (det.x1, max(14, det.y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                colour,
                1,
                cv2.LINE_AA,
            )
            cv2.circle(canvas, (int(det.foot_point[0]), int(det.foot_point[1])), 3, (0, 255, 255), -1)
        for x, y, w, h in motion_boxes:
            cv2.rectangle(canvas, (x, y), (x + w, y + h), (255, 160, 0), 1)
        if thermal["detected"] and thermal["bbox"]:
            x, y, w, h = thermal["bbox"]
            cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(
                canvas,
                f"thermal proxy {thermal['area_ratio'] * 100:.2f}%",
                (x, max(14, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )
        if events:
            label = ", ".join(sorted({e["anomaly"] for e in events}))
            cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 26), (0, 0, 140), -1)
            cv2.putText(
                canvas,
                f"ALERT: {label}",
                (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        return canvas

    @staticmethod
    def _summarise(telemetry, inference_times, events, fps) -> dict:
        if not telemetry:
            return {"frames": 0}
        latencies = sorted(inference_times)
        counts = [t.person_count for t in telemetry]
        by_type: dict[str, int] = {}
        for event in events:
            by_type[event["anomaly"]] = by_type.get(event["anomaly"], 0) + 1
        return {
            "opencv_version": cv2.__version__,
            "frames": len(telemetry),
            "fps": fps,
            "duration_s": round(len(telemetry) / fps, 2),
            "persons": {
                "mean": round(sum(counts) / len(counts), 2),
                "max": max(counts),
                "frames_with_person": sum(1 for c in counts if c > 0),
            },
            "inference_ms": {
                "mean": round(sum(latencies) / len(latencies), 2),
                "p50": round(latencies[len(latencies) // 2], 2),
                "p95": round(latencies[int(len(latencies) * 0.95)], 2),
                "max": round(latencies[-1], 2),
            },
            "frame_budget_ms": {
                "mean": round(sum(t.total_ms for t in telemetry) / len(telemetry), 2)
            },
            "events_total": len(events),
            "events_by_type": by_type,
            "motion_ratio_mean": round(
                sum(t.motion_ratio for t in telemetry) / len(telemetry), 5
            ),
        }
