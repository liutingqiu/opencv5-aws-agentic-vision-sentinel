"""Serverless dispatch layer: EventBridge -> S3 evidence -> SQS alert.

Two execution modes:

* "aws"   - real boto3 calls against an AWS account/region.
* "local" - the same boto3 calls, intercepted by moto so the full
  request/response chain is exercised offline and every returned identifier is
  logged. This is what the recorded demo runs, because the submitted artifact
  must be reproducible by a judge without credentials.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3

from .config import AwsConfig


class AlertDispatcher:
    def __init__(self, cfg: AwsConfig = AwsConfig(), mode: str = "local", log_path: Path | None = None) -> None:
        self.cfg = cfg
        self.mode = mode
        self.log_path = log_path
        self.calls: list[dict] = []
        self._mock = None
        if mode == "local":
            from moto import mock_aws

            self._mock = mock_aws()
            self._mock.start()
        self.s3 = boto3.client("s3", region_name=cfg.region)
        self.sqs = boto3.client("sqs", region_name=cfg.region)
        self.events = boto3.client("events", region_name=cfg.region)
        self._provision()

    def _provision(self) -> None:
        """Idempotent resource setup (no-op scope for an already-deployed stack)."""
        try:
            self.s3.head_bucket(Bucket=self.cfg.s3_bucket)
        except Exception:
            kwargs = {"Bucket": self.cfg.s3_bucket}
            if self.cfg.region != "us-east-1":
                kwargs["CreateBucketConfiguration"] = {"LocationConstraint": self.cfg.region}
            self.s3.create_bucket(**kwargs)
            self._log("s3:CreateBucket", {"bucket": self.cfg.s3_bucket})
        try:
            self.queue_url = self.cfg.sqs_queue_url or self.sqs.get_queue_url(
                QueueName=self.cfg.sqs_queue_name
            )["QueueUrl"]
        except Exception:
            self.sqs.create_queue(QueueName=self.cfg.sqs_queue_name)
            self._log("sqs:CreateQueue", {"queue": self.cfg.sqs_queue_name})
            self.queue_url = self.sqs.get_queue_url(QueueName=self.cfg.sqs_queue_name)["QueueUrl"]

    def dispatch(self, event: dict, evidence_path: Path | None, frame_index: int, source: str) -> dict:
        """Publish one alert: S3 evidence, EventBridge detail, SQS message."""
        alert_id = f"alert-{uuid.uuid4().hex[:12]}"
        record: dict = {"alert_id": alert_id, "frame_index": frame_index, "anomaly": event["anomaly"]}

        if evidence_path is not None and evidence_path.exists():
            key = f"evidence/{evidence_path.name}"
            put = self.s3.put_object(
                Bucket=self.cfg.s3_bucket,
                Key=key,
                Body=evidence_path.read_bytes(),
                ContentType="image/jpeg",
                Metadata={"anomaly": event["anomaly"], "frame": str(frame_index)},
            )
            record["s3"] = {
                "bucket": self.cfg.s3_bucket,
                "key": key,
                "etag": put.get("ETag", "").strip(chr(34)),
                "version_id": put.get("VersionId"),
            }
            self._log("s3:PutObject", {"bucket": self.cfg.s3_bucket, "key": key})

        detail = {
            "alertId": alert_id,
            "anomaly": event["anomaly"],
            "severity": event["severity"],
            "source": source,
            "frameIndex": frame_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evidence": record.get("s3"),
        }
        put_events = self.events.put_events(
            Entries=[
                {
                    "Source": self.cfg.event_source,
                    "DetailType": "SentinelAnomaly",
                    "Detail": json.dumps(detail),
                    "EventBusName": self.cfg.event_bus_name,
                }
            ]
        )
        record["eventbridge"] = {
            "failed": put_events.get("FailedEntryCount"),
            "entry_id": (put_events.get("Entries") or [{}])[0].get("EventId"),
        }
        self._log("events:PutEvents", {"source": self.cfg.event_source})

        send = self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(detail),
            MessageAttributes={
                "severity": {"DataType": "String", "StringValue": event["severity"]},
                "anomaly": {"DataType": "String", "StringValue": event["anomaly"]},
            },
        )
        record["sqs"] = {
            "queue_url": self.queue_url,
            "message_id": send.get("MessageId"),
            "md5": send.get("MD5OfMessageBody"),
        }
        self._log("sqs:SendMessage", {"queue": self.cfg.sqs_queue_name})
        return record

    def _log(self, operation: str, payload: dict) -> None:
        self.calls.append({"operation": operation, "mode": self.mode, **payload})

    def close(self) -> None:
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("w", encoding="utf-8") as handle:
                for call in self.calls:
                    handle.write(json.dumps(call) + "\n")
        if self._mock is not None:
            self._mock.stop()
            self._mock = None
