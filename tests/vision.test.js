// SPDX-License-Identifier: MIT
import test from 'node:test';
import assert from 'node:assert/strict';
import { OpenCV5VisionSentinelEngine, DEFAULT_AWS_INGEST_CONFIG } from '../dist/index.js';

test('1. DEFAULT_AWS_INGEST_CONFIG validates AWS serverless endpoints', () => {
  assert.equal(DEFAULT_AWS_INGEST_CONFIG.awsRegion, 'us-east-1');
  assert.ok(DEFAULT_AWS_INGEST_CONFIG.s3BucketPayload.includes('opencv5'));
  assert.ok(DEFAULT_AWS_INGEST_CONFIG.lambdaFunctionName.startsWith('arn:aws:lambda:'));
  assert.ok(DEFAULT_AWS_INGEST_CONFIG.sqsQueueUrl.includes('amazonaws.com'));
});

test('2. processFrameTelemetry detects safety gear violation when helmet/vest missing', () => {
  const telemetry = OpenCV5VisionSentinelEngine.processFrameTelemetry(
    'frame-1001',
    'cam-dock-north',
    [
      { xMin: 100, yMin: 200, xMax: 300, yMax: 600, confidenceScore: 0.94, detectedClass: 'person' }
      // no hard_hat or safety_vest
    ]
  );

  assert.equal(telemetry.frameId, 'frame-1001');
  assert.equal(telemetry.primaryAnomaly, 'SAFETY_GEAR_MISSING');
  assert.ok(telemetry.opencv5PipelineProcessingTimeMs < 30);
});

test('3. dispatchAwsAlert routes CRITICAL anomaly with EventBridge payload', () => {
  const telemetry = OpenCV5VisionSentinelEngine.processFrameTelemetry(
    'frame-1002',
    'cam-substation-main',
    [
      { xMin: 50, yMin: 50, xMax: 200, yMax: 200, confidenceScore: 0.98, detectedClass: 'fire_hazard' }
    ]
  );

  assert.equal(telemetry.primaryAnomaly, 'EQUIPMENT_OVERHEAT_HAZARD');
  const alert = OpenCV5VisionSentinelEngine.dispatchAwsAlert(telemetry);
  assert.ok(alert);
  assert.equal(alert.severityLevel, 'CRITICAL');
  assert.ok(alert.awsEventBridgeEventId.startsWith('aws-eb-event-'));
  assert.ok(alert.annotatedFrameUrl.includes('.s3.us-east-1.amazonaws.com'));
});

test('4. Normal frame produces no alert dispatch', () => {
  const telemetry = OpenCV5VisionSentinelEngine.processFrameTelemetry(
    'frame-1003',
    'cam-lobby',
    []
  );

  assert.equal(telemetry.detectedObjects.length, 0);
  assert.equal(telemetry.primaryAnomaly, undefined);
  const alert = OpenCV5VisionSentinelEngine.dispatchAwsAlert(telemetry);
  assert.equal(alert, null);
});

test('5. Empty frameId throws error', () => {
  assert.throws(() => {
    OpenCV5VisionSentinelEngine.processFrameTelemetry('', 'cam-1', []);
  }, /Frame ID must be provided/);
});
