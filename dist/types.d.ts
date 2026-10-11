export type DetectionAnomalyType = 'INTRUSION_DETECTED' | 'SAFETY_GEAR_MISSING' | 'EQUIPMENT_OVERHEAT_HAZARD' | 'STRUCTURAL_DEFECT';
export interface BoundingBox2D {
    xMin: number;
    yMin: number;
    xMax: number;
    yMax: number;
    confidenceScore: number;
    detectedClass: string;
}
export interface VideoFrameTelemetry {
    frameId: string;
    sourceCamera: string;
    resolutionWidth: number;
    resolutionHeight: number;
    opencv5PipelineProcessingTimeMs: number;
    detectedObjects: BoundingBox2D[];
    primaryAnomaly?: DetectionAnomalyType;
}
export interface AwsServerlessIngestConfig {
    awsRegion: string;
    s3BucketPayload: string;
    lambdaFunctionName: string;
    sqsQueueUrl: string;
    enableEdgeFilter: boolean;
}
export interface VisionSentinelAlert {
    alertId: string;
    frameId: string;
    anomalyType: DetectionAnomalyType;
    severityLevel: 'CRITICAL' | 'WARNING' | 'NOTICE';
    annotatedFrameUrl: string;
    dispatchTimestamp: number;
    awsEventBridgeEventId: string;
}
