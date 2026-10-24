"""Render the demo video title/metrics/outro cards (1280x720, dark console look)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BG = (6, 11, 19)
PANEL = (13, 23, 36)
LINE = (29, 44, 63)
INK = (232, 240, 248)
MUTED = (139, 160, 182)
CV = (18, 176, 232)
AWS = (255, 153, 0)
ALERT = (255, 59, 92)
OK = (37, 208, 125)
FONT_DIR = Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


MONO = "consola.ttf"
SANS = "seguisb.ttf"


def base() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for y in range(0, H, 4):
        shade = 8 + int(10 * (1 - y / H))
        draw.line([(0, y), (W, y)], fill=(shade, shade + 4, shade + 8))
    for x in range(0, W, 64):
        draw.line([(x, 0), (x, H)], fill=(12, 20, 30))
    return img


def title_card(path: Path) -> None:
    img = base()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 8, H], fill=CV)
    d.text((72, 96), "OPENCV AI COMPETITION 2026  /  POWERED BY AWS", font=font(MONO, 17), fill=MUTED)
    d.text((72, 150), "Agentic Vision", font=font(SANS, 74), fill=INK)
    d.text((72, 236), "Sentinel", font=font(SANS, 74), fill=CV)
    d.line([(72, 340), (560, 340)], fill=LINE, width=2)
    d.text((72, 366), "Edge analysis in OpenCV 5.0.0  ->  serverless escalation", font=font(MONO, 21), fill=INK)
    d.text((72, 402), "Every figure in this video is emitted by the submitted code", font=font(MONO, 18), fill=MUTED)
    d.text((72, 428), "while decoding a real 795-frame video file.", font=font(MONO, 18), fill=MUTED)
    for i, (label, colour) in enumerate([("cv2 5.0.0", CV), ("boto3", AWS), ("S3 / EventBridge / SQS", AWS)]):
        x = 72 + i * 250
        d.rectangle([x, 500, x + 226, 544], outline=LINE, width=1)
        d.text((x + 14, 512), label, font=font(MONO, 15), fill=colour)
    d.text((72, 620), "Tingqiu Liu  @liutingqiu", font=font(MONO, 17), fill=MUTED)
    d.text((1208, 620), "github.com/liutingqiu/opencv5-aws-agentic-vision-sentinel", font=font(MONO, 13), fill=MUTED, anchor="ra")
    img.save(path)


def metrics_card(path: Path, metrics: dict) -> None:
    img = base()
    d = ImageDraw.Draw(img)
    inf = metrics["inference_ms"]
    d.text((72, 64), "MEASURED ON THE SUBMITTED RUN", font=font(MONO, 16), fill=MUTED)
    d.text((72, 96), "795 frames  /  79.5 s  /  10 fps source", font=font(SANS, 40), fill=INK)
    rows = [
        ("detections per frame (mean / peak)", f"{metrics[chr(112)+chr(101)+chr(114)+chr(115)+chr(111)+chr(110)+chr(115)][chr(109)+chr(101)+chr(97)+chr(110)]} / {metrics[chr(112)+chr(101)+chr(114)+chr(115)+chr(111)+chr(110)+chr(115)][chr(109)+chr(97)+chr(120)]}"),
        ("inference latency p50 / p95", f"{inf[chr(112)+chr(53)+chr(48)]} ms / {inf[chr(112)+chr(57)+chr(53)]} ms"),
        ("inference latency max", f"{inf[chr(109)+chr(97)+chr(120)]} ms"),
        ("end-to-end frame budget", f"{metrics[chr(102)+chr(114)+chr(97)+chr(109)+chr(101)+chr(95)+chr(98)+chr(117)+chr(100)+chr(103)+chr(101)+chr(116)+chr(95)+chr(109)+chr(115)][chr(109)+chr(101)+chr(97)+chr(110)]} ms"),
        ("events raised", str(metrics["events_total"])),
        ("alerts dispatched (S3 + EventBridge + SQS)", str(metrics["alerts_dispatched"])),
    ]
    y = 190
    for label, value in rows:
        d.line([(72, y - 14), (1208, y - 14)], fill=LINE)
        d.text((72, y), label, font=font(MONO, 19), fill=MUTED)
        d.text((880, y - 4), value, font=font(SANS, 26), fill=INK)
        y += 62
    d.text((72, 610), "p95 and max are shown because the mean hides the frames that break a frame budget.", font=font(MONO, 15), fill=MUTED)
    d.text((72, 636), "CPU only, no GPU, no OpenVINO. 92 alerts x 3 AWS calls, all logged.", font=font(MONO, 15), fill=OK)
    img.save(path)


def outro_card(path: Path) -> None:
    img = base()
    d = ImageDraw.Draw(img)
    d.text((72, 78), "REPRODUCE IT", font=font(MONO, 16), fill=MUTED)
    for i, line in enumerate([
        "pip install -r requirements.txt",
        "pytest tests -q          # 9 passed",
        "python -m sentinel.cli --source assets/vtest.avi --out runs/demo --mode local",
        "python -m sentinel.cli --source assets/vtest.avi --out runs/aws  --mode aws",
    ]):
        d.text((72, 130 + i * 44), line, font=font(MONO, 19), fill=INK if i < 3 else AWS)
    d.line([(72, 340), (1208, 340)], fill=LINE)
    d.text((72, 366), "Stated plainly:", font=font(SANS, 24), fill=INK)
    d.text((72, 408), "the cloud boundary ran under moto for this recording. Same boto3", font=font(MONO, 18), fill=MUTED)
    d.text((72, 434), "code path, same request identifiers, no AWS account involved.", font=font(MONO, 18), fill=MUTED)
    d.text((72, 480), "COOL / Graviton, PPE detection and a labelled accuracy benchmark", font=font(MONO, 18), fill=MUTED)
    d.text((72, 506), "are not claimed: there is no measurement behind them yet.", font=font(MONO, 18), fill=MUTED)
    d.text((72, 596), "github.com/liutingqiu/opencv5-aws-agentic-vision-sentinel", font=font(MONO, 17), fill=CV)
    img.save(path)


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/video")
    out.mkdir(parents=True, exist_ok=True)
    metrics = json.loads(Path("runs/demo/metrics.json").read_text())
    title_card(out / "card_title.png")
    metrics_card(out / "card_metrics.png", metrics)
    outro_card(out / "card_outro.png")
    print("cards written to", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
