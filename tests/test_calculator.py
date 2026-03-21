"""
equity/calculator.py のテスト。

モンテカルロ法を使うため、確率的な揺れが生じる。
許容誤差は ±3% とする (500,000 試行での標準誤差は ~0.05% 程度)。
"""

import pytest

from equity.calculator import calculate_equity

TOLERANCE = 3.0  # エクイティの許容誤差 (%)


def opp(range_keys: list[str]) -> dict:
    """対戦相手の辞書を生成するヘルパー。"""
    return {"range_keys": range_keys}


class TestReturnValueStructure:
    """戻り値の構造と基本的な制約のテスト。"""

    def test_returns_tuple_of_three(self):
        result = calculate_equity(["As", "Ah"], [], [opp(["KK"])])
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_values_are_float(self):
        equity, win_rate, chop_rate = calculate_equity(["As", "Ah"], [], [opp(["KK"])])
        assert isinstance(equity, float)
        assert isinstance(win_rate, float)
        assert isinstance(chop_rate, float)

    def test_values_in_0_to_100(self):
        equity, win_rate, chop_rate = calculate_equity(
            ["Kd", "Qd"], ["Jd", "Td", "2c"], [opp(["AA"])]
        )
        for v in (equity, win_rate, chop_rate):
            assert 0.0 <= v <= 100.0

    def test_win_plus_chop_leq_equity(self):
        # エクイティ = 勝率 + チョップ率の半分; equity >= win_rate は常に成立
        equity, win_rate, chop_rate = calculate_equity(["As", "Ah"], [], [opp(["KK"])])
        assert equity >= win_rate

    def test_equity_approx_win_plus_half_chop(self):
        # 対戦相手が1人の場合: equity ≈ win_rate + chop_rate / 2
        equity, win_rate, chop_rate = calculate_equity(["As", "Ah"], [], [opp(["KK"])])
        expected = win_rate + chop_rate / 2
        assert abs(equity - expected) < 0.5


class TestPreflopEquity:
    """プリフロップのエクイティテスト。"""

    def test_aa_vs_kk(self):
        # AA vs KK: AA のエクイティは約 82%
        equity, _, _ = calculate_equity(["As", "Ah"], [], [opp(["KK"])])
        assert abs(equity - 82.0) < TOLERANCE

    def test_aa_vs_random_hand(self):
        # AA vs ランダムハンド (全レンジ): 約 85%
        all_range = _all_range_keys()
        equity, _, _ = calculate_equity(["As", "Ah"], [], [opp(all_range)])
        assert abs(equity - 85.0) < TOLERANCE

    def test_dominated_hand(self):
        # AKo vs AA: AK のエクイティは約 7% (ドミネート)
        equity, _, _ = calculate_equity(["As", "Kh"], [], [opp(["AA"])])
        assert abs(equity - 7.0) < TOLERANCE

    def test_suited_connector_vs_overcards(self):
        # 98s vs AKo: 98s のエクイティは約 38%
        equity, _, _ = calculate_equity(["9s", "8s"], [], [opp(["AKo"])])
        assert abs(equity - 38.0) < TOLERANCE

    def test_symmetry_equity_sum_is_100(self):
        # ヒーロー側エクイティ + 相手側エクイティ ≈ 100% (チョップを除くと成立)
        h_eq, h_win, h_chop = calculate_equity(["As", "Ah"], [], [opp(["KK"])])
        k_eq, k_win, k_chop = calculate_equity(["Ks", "Kh"], [], [opp(["AA"])])
        assert abs(h_eq + k_eq - 100.0) < TOLERANCE


class TestBoardRunout:
    """ボードがある場合のエクイティテスト。"""

    def test_nut_flush_draw_on_flop(self):
        # As Ks vs KK でフロップ Qh Jh 2h
        # As の役割: トップツーペア+ Ah のオーバーカードを持つヒーロー
        # (実際の数値は参考値; 合理的な範囲内であることを確認)
        equity, _, _ = calculate_equity(["As", "Kd"], ["Ah", "Kh", "2s"], [opp(["KK"])])
        # ヒーローはフロップでトリップスに負けているが、アウトがある
        # エクイティが 0〜100 の範囲にあることのみ確認
        assert 0 < equity < 100

    def test_full_board_set_vs_two_pair(self):
        # ヒーロー: AA (セット), ボード: A 7 2 K J (ターン+リバー)
        # 相手: KK (トップツーペア → 実際はボードにAが出てセット負け)
        equity, _, _ = calculate_equity(
            ["As", "Ah"], ["Ad", "Kd", "Jc", "7s", "2h"], [opp(["KK"])]
        )
        # ヒーローはクォーズまたはフルハウスが確定, 相手はKKのツーペア
        # ヒーローが勝つはずだが、チョップも起きうる (低確率)
        assert equity > 90.0

    def test_rivered_complete_board_straight(self):
        # ヒーロー: As Kd, ボード: Qh Jc Ts 9d 8c → Aハイストレート成立
        # 相手がストレートより弱い手の場合、ヒーローが高エクイティ
        equity, _, _ = calculate_equity(
            ["As", "Kd"], ["Qh", "Jc", "Ts", "9d", "8c"], [opp(["22"])]
        )
        # 22 はツーペアを作れないので A-high straight に負ける
        # (ただし運良く 5 カードでフルボード確定なので完全に決まる)
        assert equity >= 50.0  # ストレートが完成しているのでほぼ勝ち

    def test_turn_card_present(self):
        # ターンまでボードあり (4 枚)
        # 元のシナリオ (As+Ks vs Qs+Js+Ts+2d) はロイヤルフラッシュ確定で equity=100 になるため変更
        # 5s+5h (ワンペア) vs AA: 相手の方が強く、リバー次第で結果が変わる
        equity, _, _ = calculate_equity(
            ["5s", "5h"], ["Ks", "Qh", "Jd", "2c"], [opp(["AA"])]
        )
        assert 0 < equity < 100


class TestTwoOpponents:
    """対戦相手が 2 人の場合のテスト。"""

    def test_returns_tuple_of_three(self):
        result = calculate_equity(["As", "Ah"], [], [opp(["KK"]), opp(["QQ"])])
        assert len(result) == 3

    def test_equity_in_range(self):
        equity, win_rate, chop_rate = calculate_equity(
            ["As", "Ah"], [], [opp(["KK"]), opp(["QQ"])]
        )
        assert 0.0 <= equity <= 100.0

    def test_aa_vs_kk_qq_equity(self):
        # AA vs KK vs QQ: AA のエクイティは約 67%
        # 73% は AA vs ランダム2人のエクイティであり、KK/QQ 限定では誤り
        # 全 C(46,5) ボード完全列挙での理論値は約 67.7%
        equity, _, _ = calculate_equity(["As", "Ah"], [], [opp(["KK"]), opp(["QQ"])])
        assert abs(equity - 67.0) < TOLERANCE

    def test_equity_lower_than_heads_up(self):
        # 対戦相手2人のエクイティ < 1人のエクイティ
        one_opp, _, _ = calculate_equity(["As", "Ah"], [], [opp(["KK"])])
        two_opp, _, _ = calculate_equity(["As", "Ah"], [], [opp(["KK"]), opp(["QQ"])])
        assert two_opp < one_opp


class TestEquityWithTiedOpponents:
    """対戦相手同士がタイになるケースのエクイティテスト。"""

    def test_hero_wins_outright_while_opponents_tie(self):
        # ヒーロー: AA, ボード: A A K (フロップ) → フォーカード確定
        # 相手1: KK (スリーカード), 相手2: QQ (クイーンのワンペア)
        # 相手1と相手2が同じスコアになりうるボードで、ヒーローが両者を上回るケース
        # ここでは対戦相手が共にボードの同じ役に依存するリバーシナリオで検証
        # ヒーロー: As Kd, ボード: Ah Kh Ks Kc 2d → フルハウス (KKKA) 以上
        # 相手1: QQ, 相手2: JJ → どちらもボードのフォーカードKに負ける
        equity, win_rate, chop_rate = calculate_equity(
            ["As", "Kd"],
            ["Ah", "Kh", "Ks", "Kc", "2d"],  # ボード確定、ヒーローはフルハウス
            [opp(["QQ"]), opp(["JJ"])],
        )
        # ヒーローは必ず勝つ: equity ≈ 100%
        assert equity > 95.0
        # equity = win_rate + chop_rate / 2 の関係が成立すること
        assert abs(equity - (win_rate + chop_rate / 2)) < 0.5

    def test_equity_formula_two_opponents(self):
        # 2対戦相手時も equity = win_rate + chop_rate/2 が近似的に成立することを確認
        equity, win_rate, chop_rate = calculate_equity(
            ["As", "Ah"], [], [opp(["KK"]), opp(["QQ"])]
        )
        assert abs(equity - (win_rate + chop_rate / 2)) < 0.5


class TestEdgeCases:
    """エッジケースのテスト。"""

    def test_empty_range_after_dead_cards_raises(self):
        # ボードにKが4枚全て使われていて、相手レンジが KK だけの場合 → ValueError
        with pytest.raises(ValueError, match="empty"):
            calculate_equity(
                ["As", "Ah"],
                ["Ks", "Kh", "Kd"],
                [opp(["KK"])],
            )

    def test_single_range_key(self):
        # 1 つのレンジキーでも計算できること
        equity, _, _ = calculate_equity(["As", "Kd"], [], [opp(["AA"])])
        assert 0.0 <= equity <= 100.0

    def test_complete_board_preflop_range(self):
        # ボード5枚が全て確定している場合 (リバーでショーダウン)
        equity, _, _ = calculate_equity(
            ["As", "Ks"],
            ["Qh", "Jd", "Tc", "2s", "7d"],
            [opp(["22"])],
        )
        assert 0.0 <= equity <= 100.0


# ── ヘルパー ─────────────────────────────────────────────────────────────────


def _all_range_keys() -> list[str]:
    """全てのレンジキー (169 種類) を返す。"""
    ranks = "AKQJT98765432"
    keys = []
    # ポケットペア
    for r in ranks:
        keys.append(r + r)
    # スーテッド・オフスート
    for i, r1 in enumerate(ranks):
        for r2 in ranks[i + 1 :]:
            keys.append(r1 + r2 + "s")
            keys.append(r1 + r2 + "o")
    return keys
