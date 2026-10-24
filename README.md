# OpenCV 5 Agentic Vision Sentinel

Edge-side vision that decides locally and escalates to AWS only when a decision was made.

Submitted to the **OpenCV AI Competition 2026, powered by AWS**.

| | |
| --- | --- |
| OpenCV | 5.0.0 (`opencv-python==5.0.0.93`), CPU only |
| Detection | SSD-MobileNet-v1 (COCO) ONNX through `cv2.dnn`, uint8 NHWC |
| Second channel | MOG2 background subtraction + contours |
| Decision | polygon zone, ground-point association, dwell timing |
| Cloud | boto3 to S3 (evidence), EventBridge (detail), SQS (alert) |
| Measured | 795 frames, inference p50 28.7 ms / p95 31.8 ms, 92 alerts |

Live run record: https://liutingqiu.github.io/opencv5-aws-agentic-vision-sentinel/  
Technical report: [`docs/technical-report.md`](docs/technical-report.md)  
Architecture: [`docs/architecture.svg`](docs/architecture.svg)  
Demo video: [`docs/demo.mp4`](docs/demo.mp4)

## Quick start

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
python scripts/fetch_assets.py          # pinned sample clip + ONNX model
python -m sentinel.cli --source assets/vtest.avi --out runs/demo --mode local
pytest tests -q                          # 9 tests
```

`--mode local` routes real boto3 calls through moto. `--mode aws` uses ambient
credentials and the resources named in `sentinel/config.py::AwsConfig`; the code
path is identical.

## What a run produces

```
runs/demo/
  annotated.mp4      full clip with boxes, motion, zone, alert banner
  evidence/*.jpg     one annotated frame per alert, the S3 payload
  events.jsonl       every event with frame index, timestamp, track id
  metrics.json       latency percentiles, person counts, event totals
  dispatches.json    S3 key/ETag, EventBridge EventId, SQS MessageId
  aws_calls.jsonl    the boto3 operations that ran
```

`index.html` reads `data/` (copied from a run) so the published page shows a real
run rather than a simulated one.

## Layout

```
sentinel/
  config.py        every threshold in one file
  detector.py      cv2.dnn inference + MOG2 motion channel
  zones.py         polygon containment, association, dwell state
  thermal.py       HSV warm-hue proxy (not radiometric)
  pipeline.py      per-frame orchestration and artifact writing
  aws_dispatch.py  boto3 boundary, local (moto) or live
  cli.py           entry point
scripts/
  fetch_assets.py  pinned inputs + SHA-256
  render_cards.py  metric cards for the demo video
  render_author_card.py
tests/             9 tests over real frames, geometry, artifacts, dispatch
```

## Limits, stated plainly

The thermal stage is a colour proxy, not thermography. Association is greedy
nearest-point, so crossing tracks can swap and split a dwell interval. The SSD
input is 300x300, so distant people and static objects are confused at score
~0.42. No precision/recall benchmark was run against labelled data, and the
cloud boundary in the recorded run was moto, not an AWS account.

`docs/technical-report.md` covers each of these with the measured evidence.
