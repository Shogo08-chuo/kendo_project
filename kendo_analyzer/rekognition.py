import boto3
from typing import Optional

from kendo_analyzer.config import AppConfig
from kendo_analyzer.models import Detection, detection_from_label


def create_rekognition_client(config: AppConfig):
    client_args = {"region_name": config.region}
    if config.aws_access_key_id and config.aws_secret_access_key:
        client_args.update(
            {
                "aws_access_key_id": config.aws_access_key_id,
                "aws_secret_access_key": config.aws_secret_access_key,
            }
        )
    return boto3.client("rekognition", **client_args)


class RekognitionWazaDetector:
    def __init__(self, client, model_arn: str):
        self.client = client
        self.model_arn = model_arn

    def detect_image_bytes(
        self,
        image_bytes: bytes,
        min_confidence: float,
        timestamp_sec: Optional[float] = None,
    ) -> list[Detection]:
        response = self.client.detect_custom_labels(
            ProjectVersionArn=self.model_arn,
            Image={"Bytes": image_bytes},
            MinConfidence=min_confidence,
        )
        return [
            detection_from_label(label, timestamp_sec=timestamp_sec)
            for label in response.get("CustomLabels", [])
        ]
