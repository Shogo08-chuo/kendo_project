import streamlit as st
import boto3
from PIL import Image
import io
import pandas as pd
import cv2
import os
import time
import sqlite3

# --- 設定 ---
MODEL_ARN = "arn:aws:rekognition:ap-northeast-1:625966732318:project/kendo-waza-detection/version/kendo-waza-detection.2026-01-28T14.21.35/1769577694890"

st.set_page_config(page_title="剣道AI分析プラットフォーム", layout="wide")
st.title("剣道専用：AI判定＆統計アプリ")

# --- AWSクライアント準備（デプロイ・Secrets対応版） ---
# Streamlit Cloudの「Advanced settings」→「Secrets」に入力した値を読み込みます
try:
    rekognition = boto3.client(
        'rekognition',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name='ap-northeast-1'
    )
except Exception as e:
    st.error("AWSの認証情報が見つかりません。Streamlit CloudのSecrets設定を確認してください。")
    st.stop()

# サイドバー設定
st.sidebar.header("メニュー")
mode = st.sidebar.radio("機能を選択", ["画像1枚判定", "動画スタッツ分析"])

# --- 【モード1】画像1枚判定 ---
if mode == "画像1枚判定":
    st.header("写真で技判定")
    img_file = st.file_uploader("写真をアップロード...", type=['jpg', 'jpeg', 'png'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, caption='アップロード画像', width=500)
        
        if st.button('AI判定を実行'):
            with st.spinner('AWSが分析中...'):
                img_byte_arr = io.BytesIO()
                rgb_image = image.convert('RGB')
                rgb_image.save(img_byte_arr, format='JPEG')
                
                response = rekognition.detect_custom_labels(
                    ProjectVersionArn=MODEL_ARN,
                    Image={'Bytes': img_byte_arr.getvalue()},
                    MinConfidence=1
                )
                
                labels = response['CustomLabels']
                if labels:
                    best = max(labels, key=lambda x: x['Confidence'])
                    st.success(f"判定結果: **{best['Name']}** ({best['Confidence']:.2f}%)")
                else:
                    st.warning("技が検出されませんでした。")

# --- 【モード2】動画スタッツ分析 ---
else:
    st.header("試合動画スタッツ分析")
    st.info("動画を2秒ごとに解析します。同じ技でも5秒空けば「別の一本」としてカウントします。")
    
    video_file = st.file_uploader("動画(mp4)をアップロード...", type=['mp4', 'mov'])
    
    if video_file:
        # 動画を画面に表示
        st.video(video_file)

        if st.button("試合分析を開始"):
            # 1. 一時ファイルとして動画を保存
            with open("temp_video.mp4", "wb") as f:
                f.write(video_file.read())

            cap = cv2.VideoCapture("temp_video.mp4")
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            waza_counts = {"men": 0, "kote": 0, "do": 0}
            last_detected_time = {"men": -10, "kote": -10, "do": -10} # 5秒判定用
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            current_frame = 0
            while cap.isOpened():
                # 2秒ごとに解析（例：FPSが30なら60フレームごと）
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                ret, frame = cap.read()
                if not ret: break

                # 画像をAIが読める形式に変換
                _, buffer = cv2.imencode('.jpg', frame)
                img_bytes = buffer.tobytes()

                # AWS Rekognition呼び出し
                response = rekognition.detect_custom_labels(
                    ProjectVersionArn=MODEL_ARN,
                    Image={'Bytes': img_bytes},
                    MinConfidence=50 # 50%以上の確信度で判定
                )

                current_time_sec = current_frame / fps

                for label in response['CustomLabels']:
                    waza_name = label['Name'].lower() # men, kote, do
                    if waza_name in waza_counts:
                        # 5秒ルール：前回の検出から5秒以上経過していれば「新しい一本」
                        if current_time_sec - last_detected_time[waza_name] > 5:
                            waza_counts[waza_name] += 1
                            last_detected_time[waza_name] = current_time_sec
                            st.write(f"⏱ {int(current_time_sec)}秒: **{label['Name']}** を検出！")

                current_frame += int(fps * 2) # 2秒分飛ばす
                
            cap.release()
            st.success("分析が完了しました！")

            # 統計を表示
            st.subheader("分析結果（スタッツ）")
            c1, c2, c3 = st.columns(3)
            c1.metric("面", f"{waza_counts['men']}回")
            c2.metric("小手", f"{waza_counts['kote']}回")
            c3.metric("胴", f"{waza_counts['do']}回")