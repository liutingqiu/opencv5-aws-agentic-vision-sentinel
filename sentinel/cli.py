"""Command line entry point.

Example:
    python -m sentinel.cli --source assets/vtest.avi --out runs/demo --mode local
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .aws_dispatch import AlertDispatcher
from .config import DEFAULT_SOURCE, AwsConfig, PipelineConfig
from .pipeline import SentinelPipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenCV 5 Agentic Vision Sentinel")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=Path("runs/demo"))
    parser.add_argument("--mode", choices=("local", "aws", "off"), default="local")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--no-aws", action="store_true", help="skip the dispatch layer entirely")
    args = parser.parse_args(argv)

    cfg = PipelineConfig()
    pipeline = SentinelPipeline(cfg)
    mode = "off" if args.no_aws else args.mode
    dispatcher = None
    dispatches: list[dict] = []
    if mode != "off":
        dispatcher = AlertDispatcher(AwsConfig(), mode=mode, log_path=args.out / "aws_calls.jsonl")

    def on_event(event: dict, evidence_path: Path) -> None:
        if dispatcher is None:
            return
        record = dispatcher.dispatch(event, evidence_path, event["frame_index"], args.source.name)
        dispatches.append(record)
        print("[dispatch] {} -> {}".format(event["anomaly"], record["alert_id"]))

    try:
        summary = pipeline.run(args.source, args.out, args.max_frames, on_event=on_event)
    finally:
        if dispatcher is not None:
            dispatcher.close()

    summary["aws_mode"] = mode
    summary["alerts_dispatched"] = len(dispatches)
    (args.out / "dispatches.json").write_text(json.dumps(dispatches, indent=2), encoding="utf-8")
    (args.out / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
