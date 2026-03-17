import streamlit as st
import boto3
from PIL import Image
import io
import pandas as pd
import cv2
import os
import time
import sqlite3


# --- 設定（変更不要。もしARNが変わったらここだけ直してください） ---
MODEL_ARN = "arn:aws:rekognition:ap-northeast-1:625966732318:project/kendo-waza-detection/version/kendo-waza-detection.2026-01-28T14.21.35/1769577694890"

st.set_page_config(page_title="剣道AI分析プラットフォーム", layout="wide")
st.title("🥋 剣道専用：AI判定＆統計アプリ（真・完全版）")

# サイドバー設定
st.sidebar.header("メニュー")
mode = st.sidebar.radio("機能を選択", ["📸 画像1枚判定", "📊 動画スタッツ分析"])

# AWSクライアント準備
rekognition = boto3.client('rekognition', region_name='ap-northeast-1')

# --- 【モード1】画像1枚判定 ---
if mode == "📸 画像1枚判定":
    st.header("📸 写真で技判定")
    img_file = st.file_uploader("写真をアップロード...", type=['jpg', 'jpeg', 'png'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, caption='アップロード画像', width=500)
        
        if st.button('AI判定を実行'):
            with st.spinner('AWSが分析中...'):
                img_byte_arr = io.BytesIO()
                # RGBAエラー対策：RGBに変換してから保存
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
    st.header("📊 試合動画スタッツ分析")
    st.info("動画を2秒ごとに解析します。同じ技でも5秒空けば「別の一本」としてカウントします。")
    
    video_file = st.file_uploader("動画(mp4)をアップロード...", type=['mp4', 'mov'])
    
    if video_file:
        st.video(video_file)
        if st.button("自作AIで分析を開始"):
            # 動画の一時保存
            with open("temp_video.mp4", "wb") as f:
                f.write(video_file.getbuffer())
            
            vidcap = cv2.VideoCapture("temp_video.mp4")
            fps = vidcap.get(cv2.CAP_PROP_FPS)
            if fps <= 0: fps = 30
            
            total_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            
            waza_counts = {"Men": 0, "Kote": 0, "Do": 0}
            last_waza = None
            last_detected_time = -10  # 最後に技を見つけた秒数を記録（最初はマイナス10秒）
            
            # UI：進捗表示用
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            count = 0
            while vidcap.isOpened():
                success, frame = vidcap.read()
                if not success: break
                
                # 2秒に1回判定（高速化）
                if count % int(fps * 2) == 0:
                    current_sec = int(count / fps)
                    status_text.text(f"🚀 解析中: {current_sec}秒 / {int(duration)}秒 を精査...")
                    progress_bar.progress(min(count / total_frames, 1.0))

                    # フレームを画像に変換
                    _, buffer = cv2.imencode(".jpg", frame)
                    
                    response = rekognition.detect_custom_labels(
                        ProjectVersionArn=MODEL_ARN,
                        Image={'Bytes': buffer.tobytes()},
                        MinConfidence=35 # 確信度が低いものは無視
                    )
                    
                    if response['CustomLabels']:
                        best = max(response['CustomLabels'], key=lambda x: x['Confidence'])
                        name = best['Name']
                        
                        # 【改良ロジック】
                        # 1. 前回の判定と技の名前が違う
                        # 2. または、名前が同じでも前回の検出から5秒以上経過している
                        if name != last_waza or (current_sec - last_detected_time) > 5:
                            if name in waza_counts:
                                waza_counts[name] += 1
                                last_detected_time = current_sec # 検出時間を更新
                                st.write(f"⏱ {current_sec}秒付近： **{name}** を検出！")
                        
                        last_waza = name
                    else:
                        last_waza = None
                count += 1
            
            vidcap.release()
            status_text.text("✅ すべての解析が完了しました！")
            progress_bar.empty()

            # 結果を統計グラフで表示
            st.subheader("📊 判定結果サマリー")
            df = pd.DataFrame(list(waza_counts.items()), columns=['技の種類', '本数'])
            st.bar_chart(df.set_index('技の種類'))
            
            c1, c2, c3 = st.columns(3)
            c1.metric("面(Men)", f"{waza_counts['Men']}本")
            c2.metric("小手(Kote)", f"{waza_counts['Kote']}本")
            c3.metric("胴(Do)", f"{waza_counts['Do']}本")

            if os.path.exists("temp_video.mp4"):
                os.remove("temp_video.mp4")

# Streamlit側での表示例
if st.sidebar.button("過去の分析データを確認"):
    conn = sqlite3.connect('kendo_app.db')
    df = pd.read_sql_query("SELECT * FROM waza_results", conn)
    st.write("### 過去の技判定ログ")
    st.dataframe(df)
    
    # 技ごとの集計グラフ
    st.bar_chart(df['waza_name'].value_counts())
    conn.close()