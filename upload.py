import argparse
import os
import sys

from kendo_analyzer.config import ConfigError, load_config
from kendo_analyzer.db import DetectionRepository
from kendo_analyzer.rekognition import RekognitionWazaDetector, create_rekognition_client
from kendo_analyzer.video import VideoProgress, analyze_video_file


def run_kendo_analysis(video_path: str):
    config = load_config()
    client = create_rekognition_client(config)
    detector = RekognitionWazaDetector(client, config.model_arn)
    repository = DetectionRepository(config.db_path)

    print(f"剣道AI分析を開始: {video_path}")

    def show_progress(progress: VideoProgress):
        if progress.accepted_detection:
            detected = progress.accepted_detection
            print(
                f"{int(progress.current_time_sec)}秒: "
                f"{detected.name} ({detected.confidence:.1f}%)"
            )

    result = analyze_video_file(video_path, detector, config, on_progress=show_progress)
    if result.detections:
        repository.save_many(result.detections)

    if result.completed:
        print("分析が完了しました。")
    else:
        print(f"分析を中断しました: {result.error_message}")

    print(f"面: {result.counts.get('men', 0)}件")
    print(f"小手: {result.counts.get('kote', 0)}件")
    print(f"胴: {result.counts.get('do', 0)}件")
    print(f"DB保存件数: {len(result.detections)}件")


def parse_args():
    parser = argparse.ArgumentParser(description="剣道試合動画の技検出テスト")
    parser.add_argument("video_path", nargs="?", default="video.mp4")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not os.path.exists(args.video_path):
        print(f"{args.video_path} が見つかりません。", file=sys.stderr)
        sys.exit(1)

    try:
        run_kendo_analysis(args.video_path)
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"解析に失敗しました: {exc}", file=sys.stderr)
        sys.exit(1)
