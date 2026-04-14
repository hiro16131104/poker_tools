import logging
import os

from flask import Flask, jsonify, render_template, request

from equity.calculator import calculate_equity

app = Flask(__name__)

# ── ロギング設定 ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_VALID_RANKS = set("AKQJT98765432")
_VALID_SUITS = set("shdc")
_VALID_RANGE_KEY_SUFFIXES = {"s", "o"}


def _is_valid_card(s: str) -> bool:
    """カード文字列が正しい形式かどうかを検証する。"""
    return len(s) == 2 and s[0] in _VALID_RANKS and s[1] in _VALID_SUITS


def _is_valid_range_key(key: str) -> bool:
    """レンジキーが正しい形式かどうかを検証する。"""
    if len(key) == 2:
        # ポケットペア (例: "AA") — 2文字が同じランクであること
        return key[0] in _VALID_RANKS and key[0] == key[1]
    if len(key) == 3:
        # スーテッド/オフスート (例: "AKs", "AKo") — 異なるランク + s/o
        r1, r2, suffix = key[0], key[1], key[2]
        return (
            r1 in _VALID_RANKS
            and r2 in _VALID_RANKS
            and r1 != r2
            and suffix in _VALID_RANGE_KEY_SUFFIXES
        )
    return False


@app.after_request
def set_security_headers(response):
    """セキュリティ関連の HTTP レスポンスヘッダーを付与する。"""
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    # フレームワークのバージョン情報を隠す
    response.headers.pop("Server", None)
    return response


@app.context_processor
def inject_env():
    return {"app_env": os.environ.get("APP_ENV", "dev")}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stack-calculator")
def stack_calculator():
    return render_template("stack_calculator.html")


@app.route("/equity-calculator")
def equity_calculator():
    return render_template("equity_calculator.html")


@app.route("/equity-calculator/calculate", methods=["POST"])
def equity_calculator_calculate():
    data = request.get_json(silent=True)
    if not data:
        logger.warning(
            "不正なリクエスト: JSON のパースに失敗 (ip=%s)", request.remote_addr
        )
        return jsonify({"error": "Invalid JSON."}), 400

    hero_hand = data.get("hero_hand", [])
    board = data.get("board", [])
    opponents = data.get("opponents", [])

    # ── 基本バリデーション ────────────────────────────────────────────────────
    if len(hero_hand) != 2:
        logger.warning(
            "バリデーションエラー: hero_hand の枚数が不正 (ip=%s)", request.remote_addr
        )
        return jsonify({"error": "hero_hand must contain exactly 2 cards."}), 400

    if len(board) not in (0, 3, 4, 5):
        logger.warning(
            "バリデーションエラー: board の枚数が不正 (ip=%s)", request.remote_addr
        )
        return jsonify({"error": "board must have 0, 3, 4, or 5 cards."}), 400

    if not (1 <= len(opponents) <= 3):
        logger.warning(
            "バリデーションエラー: opponents の数が不正 (ip=%s)", request.remote_addr
        )
        return jsonify({"error": "opponents must have 1 to 3 entries."}), 400

    for i, opp in enumerate(opponents):
        if not opp.get("range_keys"):
            logger.warning(
                "バリデーションエラー: opponents[%d].range_keys が空 (ip=%s)",
                i,
                request.remote_addr,
            )
            return jsonify({"error": f"opponents[{i}].range_keys is empty."}), 400

    # カード文字列の書式チェック
    for card in hero_hand:
        if not _is_valid_card(card):
            logger.warning(
                "バリデーションエラー: 不正なカード文字列 '%s' (ip=%s)",
                card,
                request.remote_addr,
            )
            return jsonify({"error": f"Invalid card string: '{card}'."}), 400
    for card in board:
        if not _is_valid_card(card):
            logger.warning(
                "バリデーションエラー: 不正なカード文字列 '%s' (ip=%s)",
                card,
                request.remote_addr,
            )
            return jsonify({"error": f"Invalid card string: '{card}'."}), 400

    # レンジキーの書式チェック
    for i, opp in enumerate(opponents):
        for key in opp["range_keys"]:
            if not _is_valid_range_key(key):
                logger.warning(
                    "バリデーションエラー: 不正なレンジキー '%s' (ip=%s)",
                    key,
                    request.remote_addr,
                )
                return (
                    jsonify({"error": f"Invalid range key: '{key}'."}),
                    400,
                )

    # ヒーローとボードのカード重複チェック
    all_cards = hero_hand + board
    if len(all_cards) != len(set(all_cards)):
        logger.warning(
            "バリデーションエラー: カードの重複を検出 (ip=%s)", request.remote_addr
        )
        return jsonify({"error": "Duplicate card detected in hero_hand or board."}), 400

    # ── 計算 ──────────────────────────────────────────────────────────────────
    try:
        equity, win_rate, chop_rate = calculate_equity(hero_hand, board, opponents)
    except ValueError as exc:
        logger.warning("計算エラー: %s (ip=%s)", exc, request.remote_addr)
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("予期しない計算エラー (ip=%s)", request.remote_addr)
        return jsonify({"error": "Calculation failed. Please check your input."}), 500

    return jsonify(
        {
            "equity": round(equity, 1),
            "win_rate": round(win_rate, 1),
            "chop_rate": round(chop_rate, 1),
        }
    )


if __name__ == "__main__":
    # デバッグモードは環境変数で制御する（本番では APP_ENV=prod に設定すること）
    app.run(debug=os.environ.get("APP_ENV") == "dev", port=5050)
