"""
app.py の Flask エンドポイントのテスト。

/equity-calculator/calculate (POST) のバリデーション・正常系をテストする。
"""

import json

import pytest

from app import app


@pytest.fixture
def client():
    """Flask テストクライアントを生成する。"""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def post_calculate(client, payload: dict):
    """テスト用のヘルパー: /equity-calculator/calculate に POST する。"""
    return client.post(
        "/equity-calculator/calculate",
        data=json.dumps(payload),
        content_type="application/json",
    )


# ── ページルートのテスト ───────────────────────────────────────────────────────


class TestPageRoutes:
    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_equity_calculator_returns_200(self, client):
        resp = client.get("/equity-calculator")
        assert resp.status_code == 200

    def test_stack_calculator_returns_200(self, client):
        resp = client.get("/stack-calculator")
        assert resp.status_code == 200


# ── 正常系テスト ──────────────────────────────────────────────────────────────


class TestCalculateSuccess:
    def test_basic_response_keys(self, client):
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "equity" in data
        assert "win_rate" in data
        assert "chop_rate" in data

    def test_equity_is_number(self, client):
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        data = resp.get_json()
        assert isinstance(data["equity"], (int, float))
        assert isinstance(data["win_rate"], (int, float))
        assert isinstance(data["chop_rate"], (int, float))

    def test_with_flop(self, client):
        payload = {
            "hero_hand": ["As", "Kd"],
            "board": ["Qh", "Jc", "Ts"],
            "opponents": [{"range_keys": ["AA", "KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 200

    def test_with_turn(self, client):
        payload = {
            "hero_hand": ["As", "Kd"],
            "board": ["Qh", "Jc", "Ts", "2d"],
            "opponents": [{"range_keys": ["AA"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 200

    def test_with_river(self, client):
        payload = {
            "hero_hand": ["As", "Kd"],
            "board": ["Qh", "Jc", "Ts", "2d", "7c"],
            "opponents": [{"range_keys": ["QQ"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 200

    def test_two_opponents(self, client):
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [
                {"range_keys": ["KK"]},
                {"range_keys": ["QQ"]},
            ],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 200

    def test_equity_rounded_to_one_decimal(self, client):
        # アプリは小数点1桁で丸める
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        data = resp.get_json()
        for key in ("equity", "win_rate", "chop_rate"):
            val = data[key]
            assert val == round(val, 1)

    def test_multiple_range_keys(self, client):
        payload = {
            "hero_hand": ["As", "Kd"],
            "board": [],
            "opponents": [{"range_keys": ["AA", "KK", "QQ", "AKs", "AKo"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 200


# ── バリデーションエラーテスト ─────────────────────────────────────────────────


class TestValidationErrors:
    def test_no_body_returns_400(self, client):
        resp = client.post(
            "/equity-calculator/calculate",
            data="not json",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_hero_hand_too_short(self, client):
        payload = {
            "hero_hand": ["As"],
            "board": [],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "hero_hand" in resp.get_json()["error"]

    def test_hero_hand_too_long(self, client):
        payload = {
            "hero_hand": ["As", "Ah", "Ad"],
            "board": [],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400

    def test_invalid_board_length(self, client):
        # ボードは 0, 3, 4, 5 枚のみ許可; 1枚はエラー
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": ["Kd"],
            "opponents": [{"range_keys": ["QQ"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "board" in resp.get_json()["error"]

    def test_invalid_board_length_2(self, client):
        # ボード 2 枚もエラー
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": ["Kd", "Qc"],
            "opponents": [{"range_keys": ["QQ"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400

    def test_no_opponents(self, client):
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "opponents" in resp.get_json()["error"]

    def test_too_many_opponents(self, client):
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [
                {"range_keys": ["KK"]},
                {"range_keys": ["QQ"]},
                {"range_keys": ["JJ"]},
                {"range_keys": ["TT"]},
            ],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400

    def test_empty_range_keys(self, client):
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [{"range_keys": []}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "range_keys" in resp.get_json()["error"]

    def test_duplicate_cards_in_hero_and_board(self, client):
        # ヒーローとボードに同じカードがある場合
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": ["As", "Kd", "Qc"],  # As が重複
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "Duplicate" in resp.get_json()["error"]

    def test_duplicate_cards_in_hero(self, client):
        # ヒーローハンドに重複カード
        payload = {
            "hero_hand": ["As", "As"],
            "board": [],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400

    def test_missing_range_keys_field(self, client):
        # range_keys フィールド自体がない
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [{}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400

    def test_opponent_range_exhausted_by_dead_cards(self, client):
        # ボードで相手レンジが枯渇する場合 → 400
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": ["Ks", "Kh", "Kd"],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400

    def test_invalid_card_string_in_hero(self, client):
        # ヒーローに不正なカード文字列 → 400
        payload = {
            "hero_hand": ["Zz", "Ah"],
            "board": [],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "Invalid card" in resp.get_json()["error"]

    def test_invalid_card_string_in_board(self, client):
        # ボードに不正なカード文字列 → 400
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": ["Qh", "1c", "Ts"],
            "opponents": [{"range_keys": ["KK"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "Invalid card" in resp.get_json()["error"]

    def test_invalid_range_key(self, client):
        # 不正なレンジキー → 400
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [{"range_keys": ["A2"]}],  # ポケットペアではない2文字
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "Invalid range key" in resp.get_json()["error"]

    def test_invalid_range_key_same_rank_suited(self, client):
        # 同ランクのスーテッド指定 (例: "AAs") → 400
        payload = {
            "hero_hand": ["As", "Ah"],
            "board": [],
            "opponents": [{"range_keys": ["AAs"]}],
        }
        resp = post_calculate(client, payload)
        assert resp.status_code == 400
        assert "Invalid range key" in resp.get_json()["error"]
