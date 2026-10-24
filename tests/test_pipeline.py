"""End-to-end pipeline and AWS dispatch contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel.aws_dispatch import AlertDispatcher
from sentinel.config import DEFAULT_SOURCE, AwsConfig, PipelineConfig
from sentinel.pipeline import SentinelPipeline


def test_pipeline_writes_artifacts(tmp_path: Path) -> None:
    pipeline = SentinelPipeline(PipelineConfig())
    summary = pipeline.run(DEFAULT_SOURCE, tmp_path, max_frames=24)
    assert summary["frames"] == 24
    assert summary["opencv_version"].startswith("5.")
    assert summary["inference_ms"]["p50"] > 0
    assert (tmp_path / "annotated.mp4").exists()
    assert (tmp_path / "events.jsonl").exists()
    assert json.loads((tmp_path / "metrics.json").read_text())["frames"] == 24


def test_dispatch_returns_cloud_identifiers(tmp_path: Path) -> None:
    evidence = tmp_path / "frame.jpg"
    evidence.write_bytes(b"\xff\xd8\xff\xd9")
    dispatcher = AlertDispatcher(AwsConfig(), mode="local", log_path=tmp_path / "aws_calls.jsonl")
    try:
        record = dispatcher.dispatch(
            {"anomaly": "INTRUSION_DETECTED", "severity": "CRITICAL"},
            evidence,
            42,
            "vtest.avi",
        )
    finally:
        dispatcher.close()
    assert record["s3"]["key"].startswith("evidence/")
    assert record["sqs"]["message_id"]
    assert record["eventbridge"]["entry_id"]
    assert record["eventbridge"]["failed"] == 0
    logged = [json.loads(line)["operation"] for line in (tmp_path / "aws_calls.jsonl").read_text().splitlines()]
    assert "s3:PutObject" in logged and "sqs:SendMessage" in logged and "events:PutEvents" in logged
