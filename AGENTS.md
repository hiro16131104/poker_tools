# AGENTS.md — Poker Tools

AI エージェント（Claude Code など）がこのリポジトリで作業する際のガイドです。

---

## プロジェクト概要

ポーカープレイヤー向けの Web ツール集。  
Flask 3.x アプリを AWS Lambda（Lambda Web Adapter）上で動かす構成。

- **言語 / ランタイム**: Python 3.12
- **パッケージ管理**: Poetry
- **フロントエンド**: Tailwind CSS (CDN)、Jinja2 テンプレート、日本語 UI
- **インフラ**: AWS Lambda + API Gateway REST、Docker イメージで配信

---

## ディレクトリ構造

```
poker_tools/
├── app.py                    # Flask アプリ本体・ルート定義
├── equity/
│   ├── __init__.py
│   ├── calculator.py         # モンテカルロ エクイティ計算 (200,000 試行)
│   ├── evaluator.py          # NumPy 一括 7 枚評価 (batch_evaluate_7)
│   └── range_parser.py       # レンジキー解析 (card_str_to_id, expand_range_keys)
├── templates/
│   ├── base.html             # 全テンプレートの親 (Jinja2 継承)
│   ├── index.html
│   ├── stack_calculator.html
│   └── equity_calculator.html
├── static/                   # 静的ファイル
├── tests/
│   ├── test_app.py
│   ├── test_calculator.py
│   ├── test_evaluator.py
│   └── test_range_parser.py
├── Dockerfile                # マルチステージビルド (python:3.12-slim + LWA 0.9.1)
├── template.yaml             # AWS SAM テンプレート
├── samconfig.toml            # SAM デプロイ設定 (dev / prod)
├── deploy.sh                 # デプロイ / ローカル起動スクリプト
└── pyproject.toml            # Poetry 依存関係定義
```

---

## 実装済み機能

| 機能 | ルート | 概要 |
|------|--------|------|
| スタック計算機 | `/stack-calculator` | クライアントサイド JS のみ |
| エクイティ計算機 | `/equity-calculator` | モンテカルロ、レンジ vs レンジ |

---

## API

### `POST /equity-calculator/calculate`

**リクエスト (JSON)**

```json
{
  "hero_hand": ["Ah", "Kd"],
  "board": ["2s", "7h", "Tc"],
  "opponents": [
    { "range_keys": ["AA", "KK", "AKs", "AKo"] }
  ]
}
```

- `hero_hand`: 必ず 2 枚
- `board`: 0 / 3 / 4 / 5 枚
- `opponents`: 1〜3 エントリ、各エントリに `range_keys` 必須

**レスポンス (JSON)**

```json
{ "equity": 42.3, "win_rate": 39.8, "chop_rate": 2.5 }
```

全値は `[0, 100]` の `float`（小数点以下 1 桁）。

---

## カード・レンジの表現

| 概念 | 形式 | 例 |
|------|------|----|
| カード文字列 | `ランク文字 + スート文字` | `"Ah"`, `"2c"`, `"Ts"` |
| ランク | `AKQJT98765432` | rank_index: 2=0 … A=12 |
| スート | `shdc` | suit_index: s=0, h=1, d=2, c=3 |
| card_id | `rank_index * 4 + suit_index` | `0–51` |
| ポケットペア | `"XX"` (2 文字同ランク) | `"AA"` (6 コンボ) |
| スーテッド | `"XYs"` | `"AKs"` (4 コンボ) |
| オフスート | `"XYo"` | `"AKo"` (12 コンボ) |

---

## 主要モジュール詳細

### `equity/evaluator.py`

- `batch_evaluate_7(hands: ndarray(N,7)) → ndarray(N,) int64`
- スコア = `(category << 20) | tiebreak`（category 0=ハイカード〜8=ストレートフラッシュ）
- `_STRAIGHT_TOP_LUT[8192]`: 13 ビットのランクビットマスク → ストレート最上位ランク

### `equity/range_parser.py`

- `card_str_to_id(s)` / `card_id_to_str(cid)`: 文字列 ↔ card_id
- `expand_range_key(key)` / `expand_range_keys(keys)`: レンジキー → `(id1, id2)` リスト

### `equity/calculator.py`

- `calculate_equity(hero_hand, board, opponents) → (equity%, win_rate%, chop_rate%)`
- 200,000 試行モンテカルロ（常時。網羅探索なし）
- 対戦相手のハンド衝突は最大 30 回の再抽選で解消
- ボード補充は `np.argsort(rand)` 順列 + `cumsum` トリックで除外カードをスキップ

---

## セキュリティ

`app.py` の `set_security_headers` で全レスポンスに付与:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy`（Tailwind CDN・Google Fonts を許可）
- `Server` ヘッダーを削除（バージョン情報の秘匿）

---

## 環境変数

| 変数 | 値 | 説明 |
|------|----|------|
| `APP_ENV` | `dev` / `prod` | `dev` のとき Flask デバッグモード ON、UI に DEV バッジ表示 |
| `PORT` | `8080` | gunicorn / LWA がバインドするポート |
| `AWS_LWA_READINESS_CHECK_PATH` | `/` | LWA ヘルスチェックパス |

---

## インフラ・デプロイ

### Lambda 設定 (`template.yaml`)

- **アーキテクチャ**: arm64
- **メモリ**: 1770 MB
- **タイムアウト**: 30 秒
- **ウォームアップ**: EventBridge が 5 分ごとに Lambda を呼び出す（prod のみ ENABLED）
- **ログ保持**: prod=90 日 / dev=14 日

### デプロイコマンド

```bash
# ローカル起動 (Docker, ポート 8080)
./deploy.sh local

# 開発環境デプロイ
./deploy.sh dev

# 本番環境デプロイ（確認プロンプトあり）
./deploy.sh prod

# テストをスキップしてデプロイ
./deploy.sh dev --skip-tests
```

`deploy.sh` は isort → black → flake8 → pytest を自動実行してからデプロイする。

### Dockerfile

- マルチステージビルド（`python:3.12-slim`）
- Lambda Web Adapter 0.9.1 を `/opt/extensions/lambda-adapter` にコピー
- gunicorn: `--workers 1 --threads 8 --timeout 28`

---

## ローカル開発

```bash
# 依存関係インストール
poetry install

# Flask 開発サーバー起動 (ポート 5050)
python app.py

# テスト
poetry run pytest

# フォーマット・lint
poetry run isort .
poetry run black .
poetry run flake8 .
```

---

## コーディング規約

- **コメントはすべて日本語**で記述する
- Black (line-length=88) / isort (profile=black) / flake8 に準拠
- `E203` は ignore、`.venv` は flake8 対象外
- 新しいテンプレートは必ず `templates/base.html` を継承する
- セキュリティ上の懸念（コマンドインジェクション・XSS・SQLi など）がある変更は行わない
