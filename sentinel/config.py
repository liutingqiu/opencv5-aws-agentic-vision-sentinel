"""Pinned pipeline configuration.

All numeric thresholds live here so a judge can reproduce results by changing a
single file. Values were tuned on the bundled sample clip (768x576 @ 10 fps).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = PROJECT_ROOT / "models" / "ssd_mobilenet_v1.onnx"
DEFAULT_SOURCE = PROJECT_ROOT / "assets" / "vtest.avi"

# COCO class id used by the tf2onnx SSD export for "person".
PERSON_CLASS_ID = 1


@dataclass(frozen=True)
class DetectorConfig:
    """SSD-MobileNet-v1 (ONNX) settings.

    OpenCV 5's DNN engine requires a uint8 NHWC tensor for this graph, so the
    frame is resized and passed as 1xHxWx3 uint8 instead of the float32 blob
    used by the OpenCV 4 API.
    """

    model_path: Path = DEFAULT_MODEL
    input_size: tuple[int, int] = (300, 300)
    score_threshold: float = 0.42
    min_box_area_ratio: float = 0.0012
    min_box_height_px: int = 40
    max_aspect_ratio: float = 3.4


@dataclass(frozen=True)
class MotionConfig:
    """MOG2 background subtraction used as the second, model-free channel."""

    history: int = 200
    var_threshold: float = 25.0
    detect_shadows: bool = True
    min_contour_area: int = 900
    open_iterations: int = 1
    dilate_iterations: int = 2


@dataclass(frozen=True)
class ZoneConfig:
    """Normalised polygon zones (x, y in 0..1) for the sample camera view."""

    restricted: tuple[tuple[float, float], ...] = (
        (0.10, 0.35),
        (0.72, 0.30),
        (0.72, 0.62),
        (0.10, 0.70),
    )
    dwell_alert_seconds: float = 2.0
    intrusion_alert_seconds: float = 0.6


@dataclass(frozen=True)
class ThermalConfig:
    """Colour-space thermal proxy.

    This is not radiometric thermography: it flags high-saturation warm-hue
    regions (sparks, exhaust, hot metal) inside the restricted zone using an
    HSV mask, and is reported as a proxy signal in the technical report.
    """

    hue_ranges: tuple[tuple[int, int], ...] = ((0, 12), (168, 179))
    min_saturation: int = 140
    min_value: int = 120
    min_area_ratio: float = 0.0025


@dataclass(frozen=True)
class AwsConfig:
    """Serverless target resources. ARNs are placeholders until deployment."""

    region: str = "us-east-1"
    event_bus_name: str = "default"
    event_source: str = "sentinel.edge.cv5"
    s3_bucket: str = "opencv5-sentinel-evidence"
    sqs_queue_url: str = ""
    sqs_queue_name: str = "sentinel-alerts"
    lambda_function: str = "sentinel-alert-router"


@dataclass(frozen=True)
class PipelineConfig:
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    zone: ZoneConfig = field(default_factory=ZoneConfig)
    thermal: ThermalConfig = field(default_factory=ThermalConfig)
    aws: AwsConfig = field(default_factory=AwsConfig)
    evidence_max_width: int = 640
    evidence_jpeg_quality: int = 82
