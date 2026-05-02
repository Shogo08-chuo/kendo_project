# 剣道AI分析プラットフォーム

剣道の画像・試合動画から打突動作を推定し、面・小手・胴の発生回数を可視化するAI分析アプリケーションです。  
AWS Rekognition Custom Labelsで作成した競技特化モデルを利用し、Streamlit上で画像判定・動画スタッツ分析を実行できます。

技術評価で短時間に確認しやすいよう、提出向けの要点は [docs/REVIEWER_GUIDE.md](docs/REVIEWER_GUIDE.md) にもまとめています。

## 作成物の説明

### 何を作ったのか

剣道の試合・稽古動画、または静止画像を入力として、打突動作をAIで判定するアプリケーションを作成しました。

- 画像1枚から技種別を推定する「画像判定」機能
- 試合動画を一定間隔でフレーム抽出し、技の発生回数を集計する「動画スタッツ分析」機能
- 同一打突の連続検出を抑制する重複排除ロジック
- 判定結果をSQLiteに保存する履歴管理機能
- 面・小手・胴の検出回数をグラフとメトリクスで表示する可視化機能
- AWS設定・モデルARN・認証情報をコードから分離するSecrets管理
- 外部APIに依存しない単体テスト

### 目的・背景

剣道の試合分析では、打突の有無や技の傾向を把握するために動画を目視で確認する必要があります。しかし、剣道の打突は動作が高速で、試合全体を手作業で確認すると時間がかかります。また、分析結果が定量データとして残りにくく、継続的な改善に活用しづらいという課題がありました。

そこで、AIによる画像認識と動画フレーム解析を組み合わせ、試合中にどの技がどの程度発生したかを自動集計できる仕組みを実装しました。競技者や指導者が試合後に技の傾向を確認し、稽古内容や戦術改善に活かせることを目指しています。

## 自身が担当した役割

個人開発として、企画から設計・実装・検証までを担当しました。

- 課題設定: 剣道の試合分析における「目視確認の負荷」と「定量化の難しさ」を課題として定義
- 要件設計: 画像判定、動画解析、結果保存、グラフ可視化、Secrets管理の機能要件を整理
- AI連携: AWS Rekognition Custom Labelsの推論APIをBoto3から呼び出す処理を実装
- 動画処理: OpenCVを用いた動画読み込み、フレーム抽出、JPEG変換処理を実装
- 重複検出対策: 同一打突が複数フレームで連続検出される問題に対し、技ごとの検出間隔を制御
- アーキテクチャ改善: UI、設定、推論、動画解析、DB保存、可視化をモジュール分割
- UI実装: Streamlitで画像アップロード、動画アップロード、進捗表示、結果表示を実装
- データ保存: SQLiteを用いて判定結果、信頼度、検出秒数を保存する仕組みを実装
- 品質保証: AWSを呼ばずに実行できる単体テストを追加

## 技術情報

### 使用技術

| 分類 | 技術 |
| --- | --- |
| 言語 | Python |
| UI | Streamlit |
| AI / 画像認識 | AWS Rekognition Custom Labels |
| AWS連携 | Boto3 |
| 動画処理 | OpenCV |
| 画像処理 | Pillow |
| データ保存 | SQLite |
| 可視化 | Matplotlib, Streamlit metrics |
| テスト | unittest |

### 使用モデル・API

- 使用モデル: AWS Rekognition Custom Labelsで作成した剣道技判定モデル
- 判定対象: `men`, `kote`, `do`
- 使用API: `detect_custom_labels`
- 設定情報: Streamlit Secretsまたは環境変数からAWSリージョン、モデルARN、認証情報を読み込み
- デフォルトリージョン: `ap-northeast-1`

AWSアカウントIDやモデルARNは個人・環境情報を含むため、READMEおよびソースコードには実値を記載していません。実行時はSecretsまたは環境変数で設定します。

## アーキテクチャ

```text
Streamlit UI / CLI
  |
  | 画像・動画を受け取る
  v
kendo_analyzer package
  |
  | config.py        設定読み込み
  | image.py         画像変換
  | video.py         動画解析制御
  | rekognition.py   AWS Rekognition連携
  | counter.py       技ごとの重複排除・集計
  | db.py            SQLite保存
  | visualization.py グラフ生成
  v
AWS Rekognition Custom Labels / SQLite / Streamlit表示
```

詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) に記載しています。

## 実装方法

### 画像判定

1. Streamlitの`file_uploader`で画像を受け取る
2. PillowでRGB画像に変換し、JPEGバイト列としてメモリ上に保持する
3. Boto3経由でRekognition Custom Labelsの`detect_custom_labels`を呼び出す
4. 返却されたラベルのうち、最も信頼度が高いものを判定結果として表示する
5. 技名と信頼度をSQLiteに保存する

### 動画スタッツ分析

1. Streamlitで動画ファイルを受け取る
2. OpenCVの`VideoCapture`で動画を読み込む
3. `FRAME_INTERVAL_SECONDS`ごとにフレームを抽出し、JPEG形式にエンコードする
4. 各フレームをRekognition Custom Labelsに送信して技を推定する
5. `men`, `kote`, `do`に該当するラベルのみを集計対象にする
6. 同一技が短時間に連続検出された場合は、`DEDUPE_SECONDS`による時間窓で重複カウントを抑制する
7. 集計結果を棒グラフと数値メトリクスで表示する
8. 受理された検出イベントをSQLiteへ保存する

## 直面した課題と解決方法

### 1. 剣道特有の高速動作により検出結果が不安定になる

剣道の打突は一瞬で発生するため、動画の全フレームを単純に解析しても、ぶれや姿勢の変化により判定が安定しない場合がありました。  
対応として、動画から一定間隔でフレームを抽出し、各フレームを静止画としてモデルに入力する構成にしました。まずは画像分類として扱うことで、短期間でプロトタイプを構築し、検出結果を確認できるようにしました。

### 2. 同じ打突が複数回カウントされる

1つの打突動作が複数フレームにまたがって検出されるため、そのまま集計すると実際より多くカウントされる問題がありました。  
対応として、技ごとに最後に検出された時刻を保持し、同じ技が一定秒数以内に再検出された場合は集計しないロジックを実装しました。これにより、連続フレームによる重複カウントを抑制しました。

### 3. UIと分析ロジックが密結合になりやすい

初期実装ではStreamlitアプリ内にAWS呼び出し、動画解析、DB保存、可視化がまとまり、テストや拡張が難しい構成でした。  
対応として、`kendo_analyzer`パッケージに設定、推論、動画解析、集計、DB保存、可視化を分離しました。これにより、Streamlit UIだけでなくCLIや単体テストからも同じロジックを再利用できます。

### 4. 提出時の機密情報・個人情報の取り扱い

AWSモデルARN、アクセスキー、検証動画、SQLite DBには環境固有情報や個人情報が含まれる可能性があります。  
対応として、Secrets/環境変数による設定管理、`.gitignore`によるDB・画像・動画の除外、`SECURITY.md`による提出時チェック項目の明文化を行いました。

## ディレクトリ構成

```text
.
├── app.py                         # Streamlitアプリ本体
├── kendo_ai.py                    # 静止画像判定のCLI検証用スクリプト
├── upload.py                      # 動画解析のCLI検証用スクリプト
├── setup_db.py                    # SQLiteテーブル作成スクリプト
├── kendo_analyzer/                # 分析ロジック本体
│   ├── config.py                  # Secrets/環境変数の読み込み
│   ├── rekognition.py             # AWS Rekognition連携
│   ├── video.py                   # 動画解析
│   ├── counter.py                 # 重複排除・集計
│   ├── db.py                      # SQLite保存
│   ├── image.py                   # 画像変換
│   └── visualization.py           # グラフ生成
├── tests/                         # 単体テスト
├── docs/                          # 設計・評価計画・レビュー向け資料
├── data/                          # ローカル検証データ置き場
├── outputs/                       # ローカル出力置き場
├── .streamlit/secrets.toml.example
├── .env.example
├── SECURITY.md
├── Makefile
├── pyproject.toml
└── requirements.txt
```

`kendo_app.db`、検証用画像、検証用動画はローカル実行時に使用するファイルのため、Git管理対象から外しています。

## セットアップ・実行方法

### 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### Streamlit Secretsの設定

`.streamlit/secrets.toml.example`を参考に、ローカルで`.streamlit/secrets.toml`を作成してAWS設定を記述します。

```toml
AWS_REGION = "ap-northeast-1"
AWS_MODEL_ARN = "your_rekognition_custom_labels_model_arn"
AWS_ACCESS_KEY_ID = "your_access_key"
AWS_SECRET_ACCESS_KEY = "your_secret_key"
DB_PATH = "kendo_app.db"
IMAGE_MIN_CONFIDENCE = 1
VIDEO_MIN_CONFIDENCE = 50
FRAME_INTERVAL_SECONDS = 2
DEDUPE_SECONDS = 5
```

CLI検証スクリプトを使う場合は、同等の値を環境変数として設定します。設定項目は `.env.example` にも記載しています。

### データベースの初期化

```bash
python3 setup_db.py
```

### Streamlitアプリの起動

```bash
streamlit run app.py
```

または:

```bash
make run
```

### CLIでの検証

```bash
python3 kendo_ai.py path/to/image.jpg
python3 upload.py path/to/video.mp4
```

## テスト・品質確認

外部APIを呼ばずに、設定読み込み、重複排除、DB保存、モデル変換ロジックをテストできます。

```bash
make check
make test
```

直接実行する場合:

```bash
python3 -m py_compile app.py kendo_ai.py upload.py setup_db.py kendo_analyzer/*.py
python3 -m unittest discover -s tests
```

## 今後の改善

評価・改善計画は [docs/EVALUATION_PLAN.md](docs/EVALUATION_PLAN.md) にまとめています。主な改善案は以下です。

- 学習データを拡充し、撮影角度・照明・防具差への頑健性を高める
- Precision / Recall / F1-scoreを用いた定量評価を追加する
- YOLOなどの物体検出モデルや姿勢推定を組み合わせ、打突位置と動作タイミングをより詳細に検出する
- S3に動画を保存し、解析ジョブを非同期処理する構成へ拡張する
- 検出したシーンの秒数から該当クリップを自動生成する

## 提出・公開時の注意

- AWSアカウントID、アクセスキー、モデルARNなどの環境固有情報は公開しない
- 検証用画像・動画に個人が特定できる情報が含まれないことを確認する
- SQLite DBに個人情報や実試合の機微情報が含まれないことを確認する
- 提出前に `SECURITY.md` の確認コマンドを実行する
