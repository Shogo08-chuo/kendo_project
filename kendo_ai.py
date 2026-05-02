import argparse
import sys

from kendo_analyzer.config import ConfigError, load_config
from kendo_analyzer.image import image_to_jpeg_bytes
from kendo_analyzer.rekognition import RekognitionWazaDetector, create_rekognition_client

from PIL import Image


def analyze_kendo_waza(photo_path: str):
    config = load_config()
    client = create_rekognition_client(config)
    detector = RekognitionWazaDetector(client, config.model_arn)

    image = Image.open(photo_path)
    detections = detector.detect_image_bytes(
        image_to_jpeg_bytes(image),
        min_confidence=config.image_min_confidence,
    )

    print("--- 判定結果 (ベスト回答) ---")
    if not detections:
        print("技は検出されませんでした。")
        return

    best = max(detections, key=lambda item: item.confidence)
    print(f"AIの推論結果: {best.name} (自信度: {best.confidence:.2f}%)")


def parse_args():
    parser = argparse.ArgumentParser(description="剣道技判定モデルの静止画像テスト")
    parser.add_argument("photo_path", nargs="?", default="test_image.jpg")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        analyze_kendo_waza(args.photo_path)
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"解析に失敗しました: {exc}", file=sys.stderr)
        sys.exit(1)
