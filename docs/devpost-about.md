## Inspiration

Fixed-camera sites already own the camera but not the attention. A human watching a dozen streams misses most events, and shipping every frame to a cloud inference service costs more than the guard it replaces while adding a round trip that makes any alert arrive too late to matter.

The constraint we designed around: decide at the edge, escalate to the cloud only when a decision was actually made.

## What it does

The pipeline runs four stages on every decoded frame:

1. **OpenCV 5 detection** — SSD-MobileNet-v1 (COCO) exported to ONNX and executed by the OpenCV 5 DNN engine, filtered to the person class with geometric sanity checks (minimum height, aspect ratio, area ratio).
2. **Classical motion channel** — MOG2 background subtraction, morphological open/close, contour extraction and area filtering, kept independent of the learned detector so the two signals can be compared on the same frames.
3. **Spatial decision layer** — a normalised polygon zone, a ground-contact point per detection, greedy frame-to-frame association, and dwell timing. This is where a detection becomes an event: `INTRUSION_DETECTED`, `DWELL_EXCEEDED`, or `THERMAL_PROXY_HIGH` from an HSV warm-hue mask inside the zone.
4. **AWS escalation** — on an event, the annotated frame is written to Amazon S3, a structured detail is published to Amazon EventBridge, and an alert message is queued in Amazon SQS.

## How we built it

- **Edge core:** `sentinel/` — `detector.py` (cv2.dnn + MOG2), `zones.py` (polygon containment, association, dwell state), `thermal.py`, `pipeline.py` (per-frame orchestration and artifact writing), `config.py` (every threshold in one auditable file).
- **Cloud boundary:** `sentinel/aws_dispatch.py` — one boto3 boundary for `s3.put_object`, `events.put_events` and `sqs.send_message`, identical in `--mode aws` and `--mode local`.
- **Artifacts per run:** `annotated.mp4`, `evidence/*.jpg`, `events.jsonl`, `metrics.json`, `dispatches.json`, `aws_calls.jsonl`. The project page, the report and the video all read from that one directory.
- **Tests:** 9 pytest cases over real decoded frames, zone geometry, artifact writing, and the dispatch contract (asserting non-empty `MessageId` / `EventId` and `FailedEntryCount == 0`).

## Challenges we ran into

OpenCV 5.0 rejects the float32 blob that OpenCV 4 accepted for this graph: `ssd_mobilenet_v1_10.onnx` declares a uint8 `image_tensor:0`, so `cv2.dnn.blobFromImage` fails with `CV_32FC1 given, CV_8UC1 expected`. Building the tensor as uint8 NHWC fixed it. The second trap was calling `forward(name)` once per output, which re-runs the graph — 92 ms per frame instead of 25 ms. A single `net.forward(list_of_names)` brought it back under budget.

`cv2.HOGDescriptor` is gone in 5.0, which removed the usual pedestrian baseline, so the second channel had to be classical motion analysis.

## Accomplishments that we are proud of

On the bundled 795-frame, 768x576, 10 fps clip, on CPU with no GPU:

- inference p50 **23.31 ms**, p95 **30.62 ms**, max 34.89 ms; end-to-end frame budget 31.54 ms
- **4.48** detections per frame on average, peak 9, with a person present in all 795 frames
- **92** alerts raised and dispatched — each one a real S3 put, EventBridge put_events and SQS send_message
- 9/9 tests passing

## What we learned

Percentiles, not means. A pipeline whose average is 31 ms still breaks a 10 fps budget on the tail, and only p95 and max make that visible. The other lesson is scope honesty: a narrower system whose every claim is traceable to a frame index and a request identifier is worth more than a broad one that sounds impressive and cannot be demonstrated.

## What is next

Replace greedy nearest-point association with a real tracker (ByteTrack/OC-SORT) so crossing tracks stop splitting a dwell interval; add COOL on AWS Graviton with a measured throughput comparison; and run a precision/recall benchmark against a labelled set, which this entry does not have.

## Stated plainly

The cloud boundary in the recorded run was exercised with moto, using the same boto3 calls and identifiers that `--mode aws` uses against a live account. COOL/Graviton execution and PPE detection are not implemented and are not claimed. No labelled accuracy benchmark was run; the report gives latency, event counts, and the known failure cases instead.
