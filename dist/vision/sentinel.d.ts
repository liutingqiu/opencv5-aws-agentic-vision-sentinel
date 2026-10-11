import { BoundingBox2D, VideoFrameTelemetry, AwsServerlessIngestConfig, VisionSentinelAlert } from '../types.js';
export declare const DEFAULT_AWS_INGEST_CONFIG: AwsServerlessIngestConfig;
export declare class OpenCV5VisionSentinelEngine {
    /**
     * Processes simulated frame telemetry via OpenCV 5 computer vision heuristics
     * and classifies safety/security anomalies.
     */
    static processFrameTelemetry(frameId: string, sourceCamera: string, detectedObjects: BoundingBox2D[]): VideoFrameTelemetry;
    /**
     * Dispatches alerts to AWS EventBridge & SQS when anomalies breach severity criteria.
     */
    static dispatchAwsAlert(telemetry: VideoFrameTelemetry, config?: AwsServerlessIngestConfig): VisionSentinelAlert | null;
}
