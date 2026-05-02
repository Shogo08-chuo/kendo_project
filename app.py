import os
import tempfile

import streamlit as st
from PIL import Image

from kendo_analyzer.config import ConfigError, load_config
from kendo_analyzer.db import DetectionRepository
from kendo_analyzer.image import image_to_jpeg_bytes
from kendo_analyzer.rekognition import RekognitionWazaDetector, create_rekognition_client
from kendo_analyzer.video import VideoProgress, analyze_video_file
from kendo_analyzer.visualization import create_counts_figure


st.set_page_config(page_title="剣道AI分析プラットフォーム", layout="wide")
st.title("剣道専用：AI判定＆統計アプリ")


@st.cache_resource
def load_services():
    config = load_config(secrets=st.secrets)
    client = create_rekognition_client(config)
    detector = RekognitionWazaDetector(client, config.model_arn)
    repository = DetectionRepository(config.db_path)
    repository.init_db()
    return config, detector, repository


try:
    app_config, waza_detector, detection_repository = load_services()
except ConfigError as exc:
    st.error(str(exc))
    st.stop()
except Exception:
    st.error("AWSの認証情報、モデルARN、リージョン設定を確認してください。")
    st.stop()


def render_image_mode():
    st.header("写真で技判定")
    img_file = st.file_uploader("写真をアップロード...", type=["jpg", "jpeg", "png"])

    if not img_file:
        return

    image = Image.open(img_file)
    st.image(image, caption="アップロード画像", width=500)

    if st.button("AI判定を実行"):
        with st.spinner("分析中..."):
            try:
                detections = waza_detector.detect_image_bytes(
                    image_to_jpeg_bytes(image),
                    min_confidence=app_config.image_min_confidence,
                )
            except Exception as exc:
                st.error(f"AWS解析エラー: {exc}")
                st.stop()

            if not detections:
                st.warning("技が検出されませんでした。")
                return

            best = max(detections, key=lambda item: item.confidence)
            detection_repository.save(best)
            st.success(f"判定結果: **{best.name}** ({best.confidence:.2f}%)")


def render_video_mode():
    st.header("試合動画スタッツ分析")
    st.info("動画を解析し、その試合だけの統計グラフを表示します。")

    video_file = st.file_uploader("動画(mp4/mov)をアップロード...", type=["mp4", "mov"])
    if not video_file:
        return

    st.video(video_file)

    if not st.button("試合分析を開始"):
        return

    temp_video_path = None
    progress_bar = st.progress(0)
    event_area = st.container()

    def show_progress(progress: VideoProgress):
        progress_bar.progress(progress.progress_ratio)
        if progress.accepted_detection:
            detected = progress.accepted_detection
            event_area.write(
                f"{int(progress.current_time_sec)}秒: "
                f"**{detected.name}** を検出 ({detected.confidence:.1f}%)"
            )

    try:
        suffix = os.path.splitext(video_file.name)[1] or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_video:
            temp_video.write(video_file.getbuffer())
            temp_video_path = temp_video.name

        with st.spinner("動画を解析中..."):
            result = analyze_video_file(
                temp_video_path,
                detector=waza_detector,
                config=app_config,
                on_progress=show_progress,
            )
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)

    progress_bar.progress(1.0)
    if result.completed:
        st.success("分析完了")
    else:
        st.warning(f"分析を中断しました: {result.error_message}")

    if result.detections:
        detection_repository.save_many(result.detections)

    st.subheader("今回の試合分析グラフ")
    st.pyplot(create_counts_figure(result.counts))

    st.subheader("技の合計数")
    c1, c2, c3 = st.columns(3)
    c1.metric("面 (Men)", f"{result.counts.get('men', 0)}回")
    c2.metric("小手 (Kote)", f"{result.counts.get('kote', 0)}回")
    c3.metric("胴 (Do)", f"{result.counts.get('do', 0)}回")


mode = st.sidebar.radio("機能を選択", ["画像1枚判定", "動画スタッツ分析"])
if mode == "画像1枚判定":
    render_image_mode()
else:
    render_video_mode()
