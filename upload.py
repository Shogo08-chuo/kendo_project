import boto3
import cv2
import sqlite3
import os
import time

# --- 設定（あなたのカスタムモデル情報） ---
MODEL_ARN = "arn:aws:rekognition:ap-northeast-1:625966732318:project/kendo-waza-detection/version/kendo-waza-detection.2026-01-28T14.21.35/1769577694890"
rekognition = boto3.client('rekognition', region_name='ap-northeast-1')

def save_to_db(waza_name, confidence):
    conn = sqlite3.connect('kendo_app.db')
    cursor = conn.cursor()
    # テーブルがなければ作成
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS waza_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waza_name TEXT,
            confidence REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('INSERT INTO waza_results (waza_name, confidence) VALUES (?, ?)', (waza_name, confidence))
    conn.commit()
    conn.close()

def run_kendo_analysis(video_path):
    print(f"剣道AI分析を開始: {video_path}")
    vidcap = cv2.VideoCapture(video_path)
    fps = vidcap.get(cv2.CAP_PROP_FPS)
    
    if fps <= 0:
        print("動画を読み込めませんでした。パスを確認してください。")
        return

    count = 0
    detected_count = 0

    while vidcap.isOpened():
        success, frame = vidcap.read()
        if not success: break

        # 1秒ごとに解析（fpsの数値ごとに判定）
        if count % int(fps) == 0:
            current_sec = int(count / fps)
            print(f"⏱ {current_sec}秒目を精査中...")

            # フレームを画像データに変換
            _, buffer = cv2.imencode(".jpg", frame)
            
            try:
                # AWSカスタムモデルによる判定
                response = rekognition.detect_custom_labels(
                    ProjectVersionArn=MODEL_ARN,
                    Image={'Bytes': buffer.tobytes()},
                    MinConfidence=40  # 40%以上の確信度で検出
                )

                if response['CustomLabels']:
                    # 最も確信度が高い技を取得
                    best = max(response['CustomLabels'], key=lambda x: x['Confidence'])
                    name = best['Name']
                    conf = best['Confidence']
                    
                    print(f"技を検出！: {name} ({conf:.1f}%)")
                    save_to_db(name, conf)
                    detected_count += 1
                
            except Exception as e:
                print(f"AWS解析エラー: {e}")
                print("※モデルがまだ起動（Starting）中かもしれません。Runningになるまでお待ちください。")
                break

        count += 1
    
    vidcap.release()
    print(f"全工程が完了しました。合計 {detected_count} 件の技をDBに保存しました。")

if __name__ == "__main__":
    target_video = 'video.mp4'  # 解析したい動画ファイル名
    if os.path.exists(target_video):
        run_kendo_analysis(target_video)
    else:
        print(f"{target_video} が見つかりません。")