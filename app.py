import os

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

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
    from equity.calculator import calculate_equity

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON."}), 400

    hero_hand = data.get("hero_hand", [])
    board = data.get("board", [])
    opponents = data.get("opponents", [])

    # ── 基本バリデーション ────────────────────────────────────────────────────
    if len(hero_hand) != 2:
        return jsonify({"error": "hero_hand must contain exactly 2 cards."}), 400

    if len(board) not in (0, 3, 4, 5):
        return jsonify({"error": "board must have 0, 3, 4, or 5 cards."}), 400

    if not (1 <= len(opponents) <= 3):
        return jsonify({"error": "opponents must have 1 to 3 entries."}), 400

    for i, opp in enumerate(opponents):
        if not opp.get("range_keys"):
            return jsonify({"error": f"opponents[{i}].range_keys is empty."}), 400

    # カード文字列の書式チェック
    for card in hero_hand:
        if not _is_valid_card(card):
            return jsonify({"error": f"Invalid card string: '{card}'."}), 400
    for card in board:
        if not _is_valid_card(card):
            return jsonify({"error": f"Invalid card string: '{card}'."}), 400

    # レンジキーの書式チェック
    for i, opp in enumerate(opponents):
        for key in opp["range_keys"]:
            if not _is_valid_range_key(key):
                return (
                    jsonify({"error": f"Invalid range key: '{key}'."}),
                    400,
                )

    # ヒーローとボードのカード重複チェック
    all_cards = hero_hand + board
    if len(all_cards) != len(set(all_cards)):
        return jsonify({"error": "Duplicate card detected in hero_hand or board."}), 400

    # ── 計算 ──────────────────────────────────────────────────────────────────
    try:
        equity, win_rate, chop_rate = calculate_equity(hero_hand, board, opponents)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Calculation failed. Please check your input."}), 500

    return jsonify(
        {
            "equity": round(equity, 1),
            "win_rate": round(win_rate, 1),
            "chop_rate": round(chop_rate, 1),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
