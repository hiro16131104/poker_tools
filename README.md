# Poker Tools

ポーカープレイヤーのための便利ツール集です。

## 機能

### スタック計算機
- BB換算・M値をリアルタイムで計算
- SB / BB / アンティ単位でのスタック増減ボタン
- M値に応じたゾーン表示（通常 / 要アグレッション / プッシュフォールド / 危機的）
- アンティのON/OFF状態をブラウザに保存

## 技術スタック

| 項目 | 内容 |
|------|------|
| 言語 | Python 3.12 |
| フレームワーク | Flask 3.x |
| フロントエンド | Tailwind CSS (CDN), Vanilla JS |
| パッケージ管理 | Poetry |
| インフラ | AWS Lambda + API Gateway (Lambda Web Adapter) |
| コンテナ | Docker (multi-stage build) |
| IaC | AWS SAM |

## ローカル開発

### 前提条件
- Python 3.12+
- Poetry
- Docker

### セットアップ

```bash
# 依存関係のインストール
poetry install

# 開発サーバー起動（Flask built-in）
poetry run flask run
```

ブラウザで `http://localhost:5000` を開いてください。

### Docker でローカル起動

```bash
./deploy.sh local
```

`http://localhost:8080` で確認できます。

## デプロイ

### 前提条件
- AWS CLI（設定済み）
- AWS SAM CLI
- Docker

### コマンド

```bash
# 開発環境へデプロイ
./deploy.sh dev

# 本番環境へデプロイ
./deploy.sh prod
```

デプロイ前に自動でコードのフォーマット（isort / black）とリント（flake8）が実行されます。

## プロジェクト構成

```
poker_tools/
├── app.py                  # Flask アプリ・ルーティング
├── templates/
│   ├── base.html           # 共通レイアウト
│   ├── index.html          # トップページ
│   └── stack_calculator.html
├── static/
│   └── js/
│       ├── base.js         # ハンバーガーメニュー
│       └── stack_calculator.js
├── Dockerfile
├── template.yaml           # SAM テンプレート
├── samconfig.toml          # SAM デプロイ設定
├── deploy.sh               # デプロイ / ローカル起動スクリプト
└── pyproject.toml
```

## コードスタイル

[Black](https://github.com/psf/black)・[isort](https://pycqa.github.io/isort/)・[Flake8](https://flake8.pycqa.org/) を使用しています。設定は `pyproject.toml` にまとめています。

```bash
# フォーマット
poetry run isort .
poetry run black .

# リント
poetry run flake8 .
```

## ライセンス

[MIT](LICENSE)
