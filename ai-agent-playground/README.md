# AI Agent 開発講座（音声入出力編）

このプロジェクトは、AIエージェントと対話するためのWebアプリケーションです。FastAPIバックエンドとStreamlitフロントエンドで構成され、ブラウザで音声入力と音声出力が利用できます。

## 学習内容

- Streamlitを使用したWebフロントエンドの構築
- FastAPIバックエンドとの連携
- Webインターフェースの設計と実装
- ユーザーとAIの対話機能の実装
- データベースとの連携
- 音声入力と音声出力機能の実装

## プロジェクト構成

```
.
├── app/
│   ├── api/                    # FastAPIバックエンド
│   │   ├── main.py            # メインAPIエンドポイント
│   │   ├── ai.py              # AI応答生成ロジック
│   │   └── db.py              # メッセージ保存ロジック
│   └── ui/                    # Streamlitフロントエンド
│       ├── ui.py              # UIアプリケーション
│       ├── voice_input.py     # 音声入力機能
│       └── audio_output.py    # 音声出力機能
├── voicevox/                  # VOICEVOX エンジンコンテナ
├── mysql/                     # MySQLデータベース関連
│   └── db/
│       ├── schema.sql                # テーブル定義
│       ├── seed_root_categories.sql  # 初期データ
│       └── user_messages.sql         # メッセージ保存テーブル
├── config.py                  # 設定ファイル
├── requirements.api.txt       # API依存関係
├── requirements.ui.txt        # UI依存関係
├── Dockerfile.api             # API用Dockerfile
├── Dockerfile.ui              # UI用Dockerfile
├── docker-compose.yaml        # Docker Compose設定
├── api_test.sh                # APIテスト用スクリプト
└── db_connect.sh              # DB接続確認用スクリプト
```

## 主要なコンポーネント

- FastAPIバックエンド: ユーザーメッセージの処理とAI応答の生成
- Streamlitフロントエンド: ユーザーインターフェースの提供
- データベース連携: 会話履歴の保存と取得
- 音声入出力: マイク録音と VOICEVOX による音声生成
- RabbitMQ と 2 つのワーカー:
  - 生データを受け取るプロセッサーが OpenAI API で要約・分類し次のキューへ転送
  - 解析済みデータを受け取るワーカーが MySQL へ保存
  - 分類に使用する root カテゴリーは `config.py` の `ROOT_CATEGORIES` に固定化

## システム構成

`docker-compose.yaml` で定義された複数のサービスが連携して動作します。

- `ui`: Streamlit によるフロントエンド。ポート `8080` で起動します。
- `api`: FastAPI バックエンド。ポート `8086` で待ち受けます。
- `voicevox`: 返答を音声化する VOICEVOX エンジン。ポート `50021`。
- `db`: MySQL データベース。会話履歴や分析結果を保存します。
- `rabbitmq`: メッセージキューを提供し、管理 UI はポート `15672` から利用可能です。
- `processor`: RabbitMQ の生データを要約・分類して次のキューへ転送するワーカー。
- `worker`: 解析済みデータをデータベースへ保存するワーカー。

UI → API → RabbitMQ → Processor → Worker → DB の流れでデータが処理され、生成された応答は VOICEVOX で音声化されてブラウザに返されます。

## 実装のポイント

### バックエンド（FastAPI）
- APIエンドポイントの定義
- データベース操作の実装
- AI応答生成ロジックの実装

### フロントエンド（Streamlit）
- ユーザーインターフェースの実装
- APIとの通信処理
- セッション状態を使用した会話履歴の管理
 - OpenAI Whisper API を利用した音声認識
- 音声認識結果とLLMへ送信するプロンプトをログ出力
 - AI応答を VOICEVOX で音声生成して再生

## セットアップ

### 前提条件

- Python 3.9以上
- 必要なパッケージ（requirements.txtに記載）

### セットアップ手順

1. **リポジトリのクローン**
    ```bash
    git clone -b voice https://github.com/dx-junkyard/ai-agent-playground.git
    cd ai-agent-playground
    ```

2. **環境構築**
    - `.env.example` をコピーして `.env` を作成し、`OPENAI_API_KEY` などの環境変数を設定します
      - `VOICEVOX_SPEAKER` や `VOICEVOX_SPEED` もこのファイルに記述します
      - `MQ_HOST` と `MQ_RAW_QUEUE`、`MQ_PROCESSED_QUEUE` を設定します（デフォルトは `rabbitmq`、`raw_actions`、`processed_actions`）
      - `docker compose up` を実行するとコンテナ内から自動的に読み込まれるため、`docker-compose.yaml` に環境変数を追加する必要はありません
    - 依存パッケージのインストール

3. **アプリケーションの起動**
    ```bash
    # Linux/Mac環境
    docker compose up
    ```

4. **アプリケーションにアクセス**
    - UI: http://localhost:8080
    - API: http://localhost:8086
    - VOICEVOX: http://localhost:50021
    - RabbitMQ 管理UI: http://localhost:15672

## 使い方

### Webインターフェース

1. ブラウザで http://localhost:8080 にアクセス
2. テキスト入力欄にメッセージを入力
3. 「送信」ボタンでAIと対話
4. 🎤 ボタンを押すとブラウザで録音して送信できます
5. AIの応答は自動で音声再生されます
6. 会話履歴は画面上に表示されます

#### 音声入力を利用するには

1. `.env.example` をコピーして `.env` を作成し、`OPENAI_API_KEY` を設定します
2. ブラウザがマイクへのアクセスを求めたら許可してください。録音はブラウザ側で行われるため、Dockerコンテナからホストのマイクを参照する必要はありません
3. 音声の変換には `ffmpeg` が必要です。Docker イメージでは自動でインストールされます。ローカル環境で実行する場合は `ffmpeg` をインストールしてください
4. 音声認識で得られたテキストはログに出力されます

#### 音声出力について
VOICEVOX コンテナを利用して音声を生成し、ブラウザ上で再生します。
`docker compose up` を実行すると自動で起動します。
`VOICEVOX_SPEAKER` や `VOICEVOX_SPEED` は `.env` に記述した値がアプリケーション起動時に読み込まれます。
`VOICEVOX_SPEAKER` では VOICEVOX の speaker ID を設定して使用する声色を選択できます（デフォルト: `1`）。
`VOICEVOX_SPEED` を変更すると生成される音声のスピードを調整できます（デフォルト: `1.0`）。1 より大きい値で速く、0.5 など 1 未満でゆっくりになります。

### APIの直接利用

#### メッセージの送信

```bash
curl http://localhost:8086/api/v1/user-message \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "message": "こんにちは！"
  }'
```

#### 履歴の取得

```bash
curl 'http://localhost:8086/api/v1/user-messages?user_id=me&limit=10'
```

#### ブラウジング情報の送信

Chrome 拡張 [curiosity-capture](https://github.com/dx-junkyard/curiosity-capture-chrome-extension) から送られるページ閲覧データを受け取るエンドポイントです。
利用前に `mysql/db/schema.sql` と `mysql/db/seed_root_categories.sql` を実行してテーブルと初期データを作成してください。

```bash
curl http://localhost:8086/api/v1/user-actions \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "title": "Example",
    "text": "page text",
    "scrollDepth": 0.5,
    "visit_start": "2024-01-01T00:00:00Z",
    "visit_end": "2024-01-01T00:05:00Z"
  }'
```

ページ滞在時間が 30 秒以上かつスクロール率が 0.3 以上の場合、
ワーカーがそのページの要約を含むメッセージを WebSocket 経由で
Chrome 拡張へ送信します。拡張側では受け取ったメッセージを音声
で再生するため、閲覧ページに関連した話題を自動で振ってくれます。
生成された音声は VOICEVOX によって作られ、WebSocket メッセージの `audio` フィールド
に Base64 文字列として含まれます。Chrome 拡張はこのデータをデコードして再生する
ようにコードを修正してください。従来の Web Speech API を使用する処理は不要です。

## 開発

### バックエンド（FastAPI）

バックエンドはFastAPIを使用して実装されており、以下のエンドポイントを提供します：

- `POST /api/v1/user-message`: ユーザーメッセージを処理し、AI応答を返す
- `GET /api/v1/user-messages`: 過去のメッセージ履歴を取得
- `POST /api/v1/transcribe`: 音声ファイルを文字起こししてテキストを返す
- 送信するプロンプトをログに記録してデバッグ可能
- OpenAI APIへのリクエストやWebSocket通知の送信状況を詳細にログ出力

### フロントエンド（Streamlit）

フロントエンドはStreamlitを使用して実装されており、以下の機能を提供します：

- ユーザーメッセージの入力
- AI応答の表示
- メッセージ履歴の表示
- マイク入力と音声読み上げ

このUIは、以前HTMLサンプルとして示したチャット画面のレイアウトをStreamlit上で再現しています。

## 拡張アイデア

- ユーザー認証の追加
- 複数のAIモデル切り替え機能
- メッセージの検索機能
- 会話履歴のエクスポート機能

## ライセンス

このプロジェクトは[MITライセンス](LICENSE)の下で公開されています。
