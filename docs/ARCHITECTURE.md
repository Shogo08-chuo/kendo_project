# アーキテクチャ

## 全体構成

```text
Streamlit UI / CLI
  |
  | 画像・動画を受け取る
  v
kendo_analyzer
  |
  | config.py        設定値の読み込み
  | image.py         画像のJPEGバイト列変換
  | video.py         動画フレーム抽出と解析制御
  | rekognition.py   AWS Rekognition Custom Labels連携
  | counter.py       技ごとの重複排除・集計
  | db.py            SQLite保存
  | visualization.py グラフ生成
  v
AWS Rekognition Custom Labels / SQLite / Streamlit表示
```

## 設計方針

### UIと分析ロジックの分離

初期実装ではStreamlitアプリ内にAWS呼び出し、動画解析、DB保存、可視化がまとまっていました。現在は`kendo_analyzer`パッケージへ処理を分離し、UIは入力受付と表示に集中する構成にしています。

この構成により、次の利点があります。

- CLIスクリプトから同じ分析ロジックを再利用できる
- AWSを使わない単体テストを書きやすい
- 今後YOLOや姿勢推定へ置き換える場合も、推論部分の差し替えで対応しやすい
- Streamlit以外のUIやAPIサーバーへ拡張しやすい

### 動画解析の流れ

1. OpenCVで動画を読み込む
2. `FRAME_INTERVAL_SECONDS`ごとにフレームを抽出する
3. フレームをJPEGへエンコードする
4. Rekognition Custom Labelsへ送信する
5. 返却されたラベルを`Detection`として扱う
6. `StrikeCounter`で面・小手・胴のみを集計する
7. `DEDUPE_SECONDS`以内の同一技を重複として除外する
8. 結果をSQLiteへ保存し、Streamlitで可視化する

## 現在のトレードオフ

### 一定間隔フレーム抽出

全フレームを解析するとコストと時間が増えるため、現在は一定間隔でフレームを抽出しています。高速な打突を取り逃す可能性がある一方で、プロトタイプとしては処理時間と実装コストを抑えられます。

### 画像分類モデルの利用

打突の位置や時系列動作を直接扱うのではなく、フレーム単位の分類として扱っています。実用精度を高めるには、物体検出、姿勢推定、時系列モデルを組み合わせる余地があります。

### SQLite保存

ローカル検証ではSQLiteを採用しています。チーム利用やクラウド運用を想定する場合は、RDSやDynamoDB、S3への解析結果保存に移行できます。
