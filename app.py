import streamlit as st
import boto3
from PIL import Image
import io
import pandas as pd
import cv2
import os
import sqlite3
import matplotlib.pyplot as plt  # 追加：グラフ用

# --- 設定 ---
MODEL_ARN = "arn:aws:rekognition:ap-northeast-1:625966732318:project/kendo-waza-detection/version/kendo-waza-detection.2026-01-28T14.21.35/1769577694890"

st.set_page_config(page_title="剣道AI分析プラットフォーム", layout="wide")
st.title("剣道専用：AI判定＆統計アプリ")

# --- データベース保存用関数 ---
def save_to_db(waza, conf):
    try:
        conn = sqlite3.connect('kendo_app.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO waza_results (waza_name, confidence) VALUES (?, ?)', (waza, conf))
        conn.commit()
        conn.close()
    except:
        pass

# --- AWSクライアント準備 ---
try:
    rekognition = boto3.client(
        'rekognition',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name='ap-northeast-1'
    )
except Exception as e:
    st.error("AWSの認証情報が不正です。")
    st.stop()

# サイドバー設定
mode = st.sidebar.radio("機能を選択", ["画像1枚判定", "動画スタッツ分析"])

# --- 【モード1】画像1枚判定 ---
if mode == "画像1枚判定":
    st.header("写真で技判定")
    img_file = st.file_uploader("写真をアップロード...", type=['jpg', 'jpeg', 'png'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, caption='アップロード画像', width=500)
        
        if st.button('AI判定を実行'):
            with st.spinner('分析中...'):
                img_byte_arr = io.BytesIO()
                image.convert('RGB').save(img_byte_arr, format='JPEG')
                
                response = rekognition.detect_custom_labels(
                    ProjectVersionArn=MODEL_ARN,
                    Image={'Bytes': img_byte_arr.getvalue()},
                    MinConfidence=1
                )
                
                labels = response['CustomLabels']
                if labels:
                    best = max(labels, key=lambda x: x['Confidence'])
                    st.success(f"判定結果: **{best['Name']}** ({best['Confidence']:.2f}%)")
                    save_to_db(best['Name'], best['Confidence'])
                else:
                    st.warning("技が検出されませんでした。")

# --- 【モード2】動画スタッツ分析 ---
else:
    st.header("試合動画スタッツ分析")
    st.info("動画を解析し、その試合だけの統計グラフを表示します。")
    
    video_file = st.file_uploader("動画(mp4)をアップロード...", type=['mp4', 'mov'])
    
    if video_file:
        st.video(video_file)

        if st.button("試合分析を開始"):
            # ボタンが押されるたびにこのスコープが実行されるため、集計は常に0から始まる
            with open("temp_video.mp4", "wb") as f:
                f.write(video_file.read())

            cap = cv2.VideoCapture("temp_video.mp4")
            fps = cap.get(cv2.CAP_PROP_FPS)
            waza_counts = {"men": 0, "kote": 0, "do": 0}
            last_detected_time = {"men": -10, "kote": -10, "do": -10}
            
            progress_bar = st.progress(0) # 進捗バー
            current_frame = 0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            while cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                ret, frame = cap.read()
                if not ret: break

                _, buffer = cv2.imencode('.jpg', frame)
                response = rekognition.detect_custom_labels(
                    ProjectVersionArn=MODEL_ARN,
                    Image={'Bytes': buffer.tobytes()},
                    MinConfidence=50
                )

                current_time_sec = current_frame / fps

                for label in response['CustomLabels']:
                    w_name = label['Name'].lower()
                    if w_name in waza_counts:
                        if current_time_sec - last_detected_time[w_name] > 5:
                            waza_counts[w_name] += 1
                            last_detected_time[w_name] = current_time_sec
                            save_to_db(label['Name'], label['Confidence'])
                            st.write(f"⏱ {int(current_time_sec)}秒: **{label['Name']}** を検出")

                current_frame += int(fps * 2)
                # プログレス更新
                progress_bar.progress(min(current_frame / total_frames, 1.0))
                
            cap.release()
            st.success("分析完了")

            # --- グラフ表示セクション（今回の動画のみ） ---
            st.subheader("今回の試合分析グラフ")
            
            fig, ax = plt.subplots(figsize=(10, 5))
            labels = ["Men", "Kote", "Do"]
            counts = [waza_counts["men"], waza_counts["kote"], waza_counts["do"]]
            colors = ["#ff4b4b", "#1c83e1", "#ffaa00"] # 面(赤)、小手(青)、胴(黄)のイメージ
            
            ax.bar(labels, counts, color=colors)
            ax.set_ylabel("検出回数")
            ax.set_title("技別スタッツ")
            
            # グラフをStreamlitに表示
            st.pyplot(fig)

            # 数値メトリクスを表示
            st.subheader("技の合計数")
            c1, c2, c3 = st.columns(3)
            c1.metric("面 (Men)", f"{waza_counts['men']}回")
            c2.metric("小手 (Kote)", f"{waza_counts['kote']}回")
            c3.metric("胴 (Do)", f"{waza_counts['do']}回")