"""
equity/evaluator.py のユニットテスト。

カード文字列からカードIDへの変換:
  card_id = rank_index * 4 + suit_index
  rank_index: 0='2' ... 12='A'
  suit_index: 0='s', 1='h', 2='d', 3='c'

スコア形式: (category << 20) | tiebreak
  category: 0=ハイカード ... 8=ストレートフラッシュ
"""

import numpy as np

from equity.evaluator import batch_evaluate_7
from equity.range_parser import card_str_to_id


def make_hand(*card_strs: str) -> np.ndarray:
    """カード文字列7枚から shape (1, 7) の int32 配列を生成する。"""
    assert len(card_strs) == 7
    return np.array([[card_str_to_id(c) for c in card_strs]], dtype=np.int32)


# カテゴリ定数
CAT_HIGH_CARD = 0
CAT_ONE_PAIR = 1
CAT_TWO_PAIR = 2
CAT_TRIPS = 3
CAT_STRAIGHT = 4
CAT_FLUSH = 5
CAT_FULL_HOUSE = 6
CAT_QUADS = 7
CAT_STRAIGHT_FLUSH = 8


def get_category(score: int) -> int:
    """スコアからカテゴリ番号を取得する。"""
    return int(score) >> 20


class TestBatchEvaluate7OutputShape:
    """出力の形状・型のテスト。"""

    def test_output_shape(self):
        hand = make_hand("As", "Kd", "Qh", "Jc", "Ts", "2h", "3c")
        scores = batch_evaluate_7(hand)
        assert scores.shape == (1,)

    def test_output_dtype(self):
        hand = make_hand("As", "Kd", "Qh", "Jc", "Ts", "2h", "3c")
        scores = batch_evaluate_7(hand)
        assert scores.dtype == np.int64

    def test_batch_output_shape(self):
        # 複数ハンドを同時評価できること
        h1 = make_hand("As", "Kd", "Qh", "Jc", "Ts", "2h", "3c")
        h2 = make_hand("2s", "2h", "2d", "2c", "Ks", "Qd", "Jc")
        hands = np.vstack([h1, h2])
        scores = batch_evaluate_7(hands)
        assert scores.shape == (2,)


class TestHandCategories:
    """各役のカテゴリが正しく判定されるかのテスト。"""

    def test_high_card(self):
        # A K Q J 9 7 2 (フラッシュ・ストレートなし)
        hand = make_hand("As", "Kd", "Qh", "Jc", "9s", "7d", "2c")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_HIGH_CARD

    def test_one_pair(self):
        # AA K Q J 9 7
        hand = make_hand("As", "Ah", "Kd", "Qh", "Jc", "9s", "7d")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_ONE_PAIR

    def test_two_pair(self):
        # AA KK Q J 9
        hand = make_hand("As", "Ah", "Kd", "Kh", "Qh", "Jc", "9s")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_TWO_PAIR

    def test_three_of_a_kind(self):
        # AAA K Q J 9
        hand = make_hand("As", "Ah", "Ad", "Kd", "Qh", "Jc", "9s")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_TRIPS

    def test_straight_broadway(self):
        # A K Q J T 9 2 (A-high straight)
        hand = make_hand("As", "Kd", "Qh", "Jc", "Ts", "9d", "2c")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_STRAIGHT

    def test_straight_wheel(self):
        # A 2 3 4 5 K Q (Wheel: A-2-3-4-5 ストレート)
        hand = make_hand("Ah", "2d", "3c", "4s", "5h", "Kd", "Qc")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_STRAIGHT

    def test_flush(self):
        # A K Q J 9 7 2 全スペード (フラッシュ、ストレートフラッシュではない)
        hand = make_hand("As", "Ks", "Qs", "Js", "9s", "7d", "2c")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_FLUSH

    def test_full_house(self):
        # AAA KK Q J
        hand = make_hand("As", "Ah", "Ad", "Ks", "Kh", "Qd", "Jc")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_FULL_HOUSE

    def test_four_of_a_kind(self):
        # AAAA K Q J
        hand = make_hand("As", "Ah", "Ad", "Ac", "Ks", "Qd", "Jc")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_QUADS

    def test_straight_flush(self):
        # A K Q J T 全スペード (ロイヤルフラッシュ)
        hand = make_hand("As", "Ks", "Qs", "Js", "Ts", "2d", "3c")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_STRAIGHT_FLUSH

    def test_straight_flush_low(self):
        # 9 8 7 6 5 全ハート
        hand = make_hand("9h", "8h", "7h", "6h", "5h", "As", "2d")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_STRAIGHT_FLUSH

    def test_straight_flush_wheel(self):
        # A 2 3 4 5 全クラブ (ウィールストレートフラッシュ)
        hand = make_hand("Ac", "2c", "3c", "4c", "5c", "Kd", "Qh")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_STRAIGHT_FLUSH


class TestHandRanking:
    """役の強弱の大小関係が正しいかのテスト。"""

    def _score(self, *card_strs: str) -> int:
        return int(batch_evaluate_7(make_hand(*card_strs))[0])

    def test_category_ordering(self):
        """カテゴリの大小関係: SF > 4K > FH > F > Str > 3K > 2P > 1P > HC"""
        sf = self._score("As", "Ks", "Qs", "Js", "Ts", "2d", "3c")
        quads = self._score("As", "Ah", "Ad", "Ac", "Ks", "Qd", "Jc")
        fh = self._score("As", "Ah", "Ad", "Ks", "Kh", "Qd", "Jc")
        flush = self._score("As", "Ks", "Qs", "Js", "9s", "7d", "2c")
        straight = self._score("As", "Kd", "Qh", "Jc", "Ts", "9d", "2c")
        trips = self._score("As", "Ah", "Ad", "Kd", "Qh", "Jc", "9s")
        two_pair = self._score("As", "Ah", "Kd", "Kh", "Qh", "Jc", "9s")
        one_pair = self._score("As", "Ah", "Kd", "Qh", "Jc", "9s", "7d")
        high_card = self._score("As", "Kd", "Qh", "Jc", "9s", "7d", "2c")

        assert sf > quads > fh > flush > straight
        assert straight > trips > two_pair > one_pair > high_card

    def test_higher_straight_beats_lower_straight(self):
        # A-high straight > K-high straight
        a_high = self._score("As", "Kd", "Qh", "Jc", "Ts", "9d", "2c")
        k_high = self._score("Kh", "Qd", "Jc", "Ts", "9s", "2d", "3c")
        assert a_high > k_high

    def test_wheel_beats_nothing_but_loses_to_6_high_straight(self):
        # Wheel (A-2-3-4-5) は 6-high straight より弱い
        wheel = self._score("Ah", "2d", "3c", "4s", "5h", "Kd", "Qc")
        six_high = self._score("2h", "3d", "4c", "5s", "6h", "Kd", "Qc")
        assert wheel < six_high

    def test_higher_pair_beats_lower_pair(self):
        # AA > KK
        aa = self._score("As", "Ah", "Kd", "Qh", "Jc", "9s", "7d")
        kk = self._score("Ks", "Kh", "Ad", "Qh", "Jc", "9s", "7d")
        assert aa > kk

    def test_higher_flush_beats_lower_flush(self):
        # A high flush > K high flush (同スート)
        a_flush = self._score("As", "Ks", "Qs", "Js", "9s", "7d", "2c")
        k_flush = self._score("Ks", "Qs", "Js", "9s", "7s", "Ad", "2c")
        assert a_flush > k_flush

    def test_quads_kicker_matters(self):
        # AAAA + K > AAAA + Q
        quads_k = self._score("As", "Ah", "Ad", "Ac", "Ks", "Qd", "Jc")
        quads_q = self._score("As", "Ah", "Ad", "Ac", "Qs", "Jd", "Tc")
        assert quads_k > quads_q

    def test_same_hand_equal_score(self):
        # 同じカードIDの組み合わせは同じスコア
        hand = make_hand("As", "Ah", "Ad", "Ac", "Ks", "Qd", "Jc")
        scores = batch_evaluate_7(np.vstack([hand, hand]))
        assert scores[0] == scores[1]


class TestBestFiveSelection:
    """7枚から最良の5枚を選択できているかのテスト。"""

    def test_flush_uses_best_5_of_6_suited(self):
        # 6枚スペードがある場合、上位5枚を使うこと
        # As Ks Qs Js 9s 2s (6枚スペード) + 7d
        # → A K Q J 9 のフラッシュ (2は使わない)
        hand = make_hand("As", "Ks", "Qs", "Js", "9s", "2s", "7d")
        score = batch_evaluate_7(hand)[0]
        assert get_category(score) == CAT_FLUSH

    def test_two_pair_uses_top_two_pairs_plus_kicker(self):
        # AA KK QQ の場合、AA+KK+Q (AA KK が最良のツーペア)
        hand = make_hand("As", "Ah", "Ks", "Kh", "Qs", "Qh", "Jc")
        score = batch_evaluate_7(hand)[0]
        # ツーペアではなくフルハウスにならないことの確認
        # (3ペアはツーペア扱い、フルハウスではない)
        assert get_category(score) == CAT_TWO_PAIR

    def test_straight_beats_pair_on_same_board(self):
        # ストレートが成立していればペアより強い
        # ヒーロー: A K でボード: Q J T 9 2 → A-high straight
        # 比較: A A でボード: Q J T 9 2 → ワンペア AA
        straight = self._score_two_hole_five_board(
            "As", "Kd", "Qh", "Jc", "Ts", "9d", "2c"
        )
        pair = self._score_two_hole_five_board("As", "Ah", "Qh", "Jc", "2s", "9d", "3c")
        assert get_category(straight) == CAT_STRAIGHT
        assert get_category(pair) == CAT_ONE_PAIR
        assert straight > pair

    def _score_two_hole_five_board(self, *card_strs: str) -> int:
        return int(batch_evaluate_7(make_hand(*card_strs))[0])
