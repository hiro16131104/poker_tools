"""
equity/range_parser.py のユニットテスト。
"""

from equity.range_parser import (
    card_id_to_str,
    card_str_to_id,
    expand_range_key,
    expand_range_keys,
)


class TestCardStrToId:
    """card_str_to_id のテスト。"""

    def test_lowest_card(self):
        # "2s" = rank_index 0, suit_index 0 → 0
        assert card_str_to_id("2s") == 0

    def test_highest_card(self):
        # "Ac" = rank_index 12, suit_index 3 → 12*4+3 = 51
        assert card_str_to_id("Ac") == 51

    def test_ace_of_hearts(self):
        # "Ah" = rank_index 12, suit_index 1 → 49
        assert card_str_to_id("Ah") == 49

    def test_king_of_spades(self):
        # "Ks" = rank_index 11, suit_index 0 → 44
        assert card_str_to_id("Ks") == 44

    def test_ten_of_diamonds(self):
        # "Td" = rank_index 8, suit_index 2 → 8*4+2 = 34
        assert card_str_to_id("Td") == 34

    def test_all_suits_of_two(self):
        # 2s=0, 2h=1, 2d=2, 2c=3
        assert card_str_to_id("2s") == 0
        assert card_str_to_id("2h") == 1
        assert card_str_to_id("2d") == 2
        assert card_str_to_id("2c") == 3

    def test_all_suits_of_ace(self):
        # As=48, Ah=49, Ad=50, Ac=51
        assert card_str_to_id("As") == 48
        assert card_str_to_id("Ah") == 49
        assert card_str_to_id("Ad") == 50
        assert card_str_to_id("Ac") == 51

    def test_range_is_0_to_51(self):
        # 全52枚のカードIDが 0〜51 の範囲に収まること
        ranks = "AKQJT98765432"
        suits = "shdc"
        ids = [card_str_to_id(r + s) for r in ranks for s in suits]
        assert min(ids) == 0
        assert max(ids) == 51
        assert len(set(ids)) == 52  # 重複なし


class TestCardIdToStr:
    """card_id_to_str のテスト。"""

    def test_lowest_card(self):
        assert card_id_to_str(0) == "2s"

    def test_highest_card(self):
        assert card_id_to_str(51) == "Ac"

    def test_ace_of_hearts(self):
        assert card_id_to_str(49) == "Ah"

    def test_roundtrip(self):
        # 全52枚のカードで str→id→str が一致すること
        ranks = "AKQJT98765432"
        suits = "shdc"
        for r in ranks:
            for s in suits:
                card_str = r + s
                assert card_id_to_str(card_str_to_id(card_str)) == card_str

    def test_roundtrip_id_to_str(self):
        # 全52枚のカードで id→str→id が一致すること
        for cid in range(52):
            assert card_str_to_id(card_id_to_str(cid)) == cid


class TestExpandRangeKey:
    """expand_range_key のテスト。"""

    # ── ポケットペア ──────────────────────────────────────────────────────────

    def test_pocket_pair_combo_count(self):
        # C(4,2) = 6 通り
        combos = expand_range_key("AA")
        assert len(combos) == 6

    def test_pocket_pair_all_same_rank(self):
        # AA の全コンボはどちらのカードも A (rank_index=12)
        combos = expand_range_key("AA")
        for c1, c2 in combos:
            assert c1 // 4 == 12
            assert c2 // 4 == 12

    def test_pocket_pair_no_duplicate_suits(self):
        # ペアのコンボでスートが重複しないこと
        combos = expand_range_key("AA")
        for c1, c2 in combos:
            assert c1 % 4 != c2 % 4

    def test_pocket_pair_no_duplicate_combos(self):
        # コンボに重複がないこと
        combos = expand_range_key("22")
        combo_sets = [frozenset(c) for c in combos]
        assert len(combo_sets) == len(set(combo_sets))

    def test_pocket_pair_low(self):
        # 22 も 6 通り
        combos = expand_range_key("22")
        assert len(combos) == 6
        for c1, c2 in combos:
            assert c1 // 4 == 0
            assert c2 // 4 == 0

    # ── スーテッド ────────────────────────────────────────────────────────────

    def test_suited_combo_count(self):
        # スーテッドは 4 通り (スート 0〜3 の各スート)
        combos = expand_range_key("AKs")
        assert len(combos) == 4

    def test_suited_both_same_suit(self):
        # スーテッドはどちらのカードも同一スート
        combos = expand_range_key("AKs")
        for c1, c2 in combos:
            assert c1 % 4 == c2 % 4

    def test_suited_correct_ranks(self):
        # AKs: A=12, K=11
        combos = expand_range_key("AKs")
        for c1, c2 in combos:
            assert {c1 // 4, c2 // 4} == {12, 11}

    def test_suited_covers_all_suits(self):
        # 4 通りのスート全てが含まれること
        combos = expand_range_key("QJs")
        suits_used = sorted(c1 % 4 for c1, _ in combos)
        assert suits_used == [0, 1, 2, 3]

    # ── オフスート ────────────────────────────────────────────────────────────

    def test_offsuit_combo_count(self):
        # オフスートは 4×3 = 12 通り
        combos = expand_range_key("AKo")
        assert len(combos) == 12

    def test_offsuit_different_suits(self):
        # オフスートはどちらのカードもスートが異なること
        combos = expand_range_key("AKo")
        for c1, c2 in combos:
            assert c1 % 4 != c2 % 4

    def test_offsuit_correct_ranks(self):
        # AKo: A=12, K=11
        combos = expand_range_key("AKo")
        for c1, c2 in combos:
            assert {c1 // 4, c2 // 4} == {12, 11}

    def test_offsuit_no_duplicate_combos(self):
        # コンボに重複がないこと
        combos = expand_range_key("AKo")
        combo_tuples = [tuple(sorted(c)) for c in combos]
        assert len(combo_tuples) == len(set(combo_tuples))

    # ── 不正なキーは空リストを返す ─────────────────────────────────────────────

    def test_invalid_key_returns_empty(self):
        assert expand_range_key("") == []
        assert expand_range_key("AAKK") == []


class TestExpandRangeKeys:
    """expand_range_keys のテスト。"""

    def test_single_key(self):
        combos = expand_range_keys(["AA"])
        assert len(combos) == 6

    def test_multiple_keys(self):
        # AA (6) + AKs (4) + AKo (12) = 22
        combos = expand_range_keys(["AA", "AKs", "AKo"])
        assert len(combos) == 22

    def test_empty_list(self):
        assert expand_range_keys([]) == []

    def test_total_count_suited_plus_offsuit(self):
        # AKs + AKo = 16 通り (AK の全コンボ)
        combos = expand_range_keys(["AKs", "AKo"])
        assert len(combos) == 16
