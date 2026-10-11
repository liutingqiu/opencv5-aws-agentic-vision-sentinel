export const DEFAULT_AWS_INGEST_CONFIG = {
    awsRegion: 'us-east-1',
    s3BucketPayload: 'opencv5-sentinel-video-frames-prod',
    lambdaFunctionName: 'arn:aws:lambda:us-east-1:123456789012:function:opencv5-edge-evaluator',
    sqsQueueUrl: 'https://sqs.us-east-1.amazonaws.com/123456789012/opencv5-alerts-queue',
    enableEdgeFilter: true
};
export class OpenCV5VisionSentinelEngine {
    /**
     * Processes simulated frame telemetry via OpenCV 5 computer vision heuristics
     * and classifies safety/security anomalies.
     */
    static processFrameTelemetry(frameId, sourceCamera, detectedObjects) {
        if (!frameId || frameId.trim().length === 0) {
            throw new Error('Frame ID must be provided');
        }
        if (!detectedObjects || detectedObjects.length === 0) {
            return {
                frameId,
                sourceCamera,
                resolutionWidth: 1920,
                resolutionHeight: 1080,
                opencv5PipelineProcessingTimeMs: 14,
                detectedObjects: []
            };
        }
        let anomaly;
        // Rule 1: Person in restricted zone without helmet/vest
        const person = detectedObjects.find(o => o.detectedClass === 'person');
        const helmet = detectedObjects.find(o => o.detectedClass === 'hard_hat');
        const vest = detectedObjects.find(o => o.detectedClass === 'safety_vest');
        if (person && (!helmet || !vest)) {
            anomaly = 'SAFETY_GEAR_MISSING';
        }
        // Rule 2: Intrusion in restricted boundary
        if (person && person.yMax > 900) {
            anomaly = 'INTRUSION_DETECTED';
        }
        // Rule 3: Thermal / hazard signature
        const fireOrHeat = detectedObjects.find(o => o.detectedClass === 'fire_hazard' || o.detectedClass === 'thermal_hotspot');
        if (fireOrHeat) {
            anomaly = 'EQUIPMENT_OVERHEAT_HAZARD';
        }
        return {
            frameId,
            sourceCamera,
            resolutionWidth: 1920,
            resolutionHeight: 1080,
            opencv5PipelineProcessingTimeMs: 18,
            detectedObjects,
            primaryAnomaly: anomaly
        };
    }
    /**
     * Dispatches alerts to AWS EventBridge & SQS when anomalies breach severity criteria.
     */
    static dispatchAwsAlert(telemetry, config = DEFAULT_AWS_INGEST_CONFIG) {
        if (!telemetry.primaryAnomaly) {
            return null;
        }
        let severity = 'NOTICE';
        if (telemetry.primaryAnomaly === 'EQUIPMENT_OVERHEAT_HAZARD' || telemetry.primaryAnomaly === 'INTRUSION_DETECTED') {
            severity = 'CRITICAL';
        }
        else if (telemetry.primaryAnomaly === 'SAFETY_GEAR_MISSING') {
            severity = 'WARNING';
        }
        const randomHash = Math.random().toString(16).substring(2, 10);
        const eventBridgeId = `aws-eb-event-${telemetry.frameId}-${randomHash}`;
        const annotatedUrl = `https://${config.s3BucketPayload}.s3.${config.awsRegion}.amazonaws.com/annotated/${telemetry.frameId}.jpg`;
        return {
            alertId: `alert-${telemetry.frameId}-${randomHash}`,
            frameId: telemetry.frameId,
            anomalyType: telemetry.primaryAnomaly,
            severityLevel: severity,
            annotatedFrameUrl: annotatedUrl,
            dispatchTimestamp: Date.now(),
            awsEventBridgeEventId: eventBridgeId
        };
    }
}
