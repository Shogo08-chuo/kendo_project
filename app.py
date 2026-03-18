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
st.title("🥋 剣道専用：AI判定＆統計アプリ（DB連携版）")

# --- データベース保存用関数 ---
def save_to_db(waza, conf):
    try:
        conn = sqlite3.connect('kendo_app.db')
        cursor = conn.cursor()
        # setup_db.pyで作ったテーブルに挿入
        cursor.execute('INSERT INTO waza_results (waza_name, confidence) VALUES (?, ?)', (waza, conf))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"DB保存エラー: {e}")

# --- AWSクライアント準備 ---
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
    st.header("📸 写真で技判定")
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
                    # 画像判定の結果もDBに保存
                    save_to_db(best['Name'], best['Confidence'])
                else:
                    st.warning("技が検出されませんでした。")

# --- 【モード2】動画スタッツ分析 ---
else:
    st.header("📊 試合動画スタッツ分析")
    st.info("動画を2秒ごとに解析し、結果をデータベースに自動保存します。")
    
    video_file = st.file_uploader("動画(mp4)をアップロード...", type=['mp4', 'mov'])
    
    if video_file:
        st.video(video_file)

        if st.button("試合分析を開始"):
            with open("temp_video.mp4", "wb") as f:
                f.write(video_file.read())

            cap = cv2.VideoCapture("temp_video.mp4")
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            waza_counts = {"men": 0, "kote": 0, "do": 0}
            last_detected_time = {"men": -10, "kote": -10, "do": -10}
            
            status_text = st.empty()
            current_frame = 0
            
            while cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                ret, frame = cap.read()
                if not ret: break

                _, buffer = cv2.imencode('.jpg', frame)
                img_bytes = buffer.tobytes()

                response = rekognition.detect_custom_labels(
                    ProjectVersionArn=MODEL_ARN,
                    Image={'Bytes': img_bytes},
                    MinConfidence=50
                )

                current_time_sec = current_frame / fps

                for label in response['CustomLabels']:
                    waza_name = label['Name'].lower()
                    if waza_name in waza_counts:
                        if current_time_sec - last_detected_time[waza_name] > 5:
                            waza_counts[waza_name] += 1
                            last_detected_time[waza_name] = current_time_sec
                            
                            # 【追加】DBへ保存
                            save_to_db(label['Name'], label['Confidence'])
                            st.write(f"⏱ {int(current_time_sec)}秒: **{label['Name']}** を検出・保存しました。")

                current_frame += int(fps * 2)
                
            cap.release()
            st.success("分析が完了しました！")

            st.subheader("今回分析した試合のスタッツ")
            c1, c2, c3 = st.columns(3)
            c1.metric("面", f"{waza_counts['men']}回")
            c2.metric("小手", f"{waza_counts['kote']}回")
            c3.metric("胴", f"{waza_counts['do']}回")

# --- 【修正版】累計データ表示（ここから下を書き換え） ---
st.divider()
st.subheader("📈 累計データ（面・小手・胴のみ）")
try:
    if os.path.exists('kendo_app.db'):
        conn = sqlite3.connect('kendo_app.db')
        
        # SQL文で「関係ない単語」を無視して、剣道の技だけを抽出します
        # あなたのモデルが返す名前に合わせて ('Men', 'Kote', 'Do') などに調整してください
        query = """
            SELECT waza_name, COUNT(*) as count 
            FROM waza_results 
            WHERE waza_name IN ('Men', 'Kote', 'Do', 'men', 'kote', 'do', '面', '小手', '胴') 
            GROUP BY waza_name
        """
        df_db = pd.read_sql_query(query, conn)
        conn.close()

        if not df_db.empty:
            # グラフを表示
            st.bar_chart(df_db.set_index('waza_name'))
            # 確認用に表も表示
            st.table(df_db)
        else:
            st.info("まだ剣道の技データ（面・小手・胴）は保存されていません。")
    else:
        st.warning("データベースファイルが見つかりません。")
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")