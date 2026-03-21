"""
NumPy を使った 7 枚組ハンドの一括評価モジュール。

カードの数値表現:  card_id = rank_index * 4 + suit_index
  rank_index: 0='2', 1='3', ..., 12='A'
  suit_index: 0='s', 1='h', 2='d', 3='c'

役の種別 (数値が高いほど強い):
  8: ストレートフラッシュ
  7: フォーカード
  6: フルハウス
  5: フラッシュ
  4: ストレート
  3: スリーカード
  2: ツーペア
  1: ワンペア
  0: ハイカード

スコアの数値表現: (category << 20) | tiebreak
  tiebreak = r1<<16 | r2<<12 | r3<<8 | r4<<4 | r5  (4 ビットランク, rank 0=2 ... 12=A)
"""

import numpy as np

# ストレート判定用の参照テーブル: インデックス = 13 ビットのランク存在ビットマスク
# → 最良ストレートのトップランク (-1 はストレートなし); ビット k = ランク k の存在 (0=2 … 12=A)
_STRAIGHT_TOP_LUT: np.ndarray = np.full(8192, -1, dtype=np.int8)

for _bits in range(8192):
    # ホイール (A-2-3-4-5): ビット 0,1,2,3 と ビット 12 (A) が揃っているか確認
    if (_bits & 0x100F) == 0x100F:  # 0x100F = bits 0,1,2,3,12
        _STRAIGHT_TOP_LUT[_bits] = 3  # 5 ハイ (rank 3 = "5")
    # 6 ハイ〜A ハイのストレート
    for _top in range(4, 13):
        _mask = 0b11111 << (_top - 4)
        if (_bits & _mask) == _mask:
            _STRAIGHT_TOP_LUT[_bits] = (
                _top  # より強いストレート（トップランクが高い方）で上書き
            )


def batch_evaluate_7(hands: np.ndarray) -> np.ndarray:
    """
    N 個の 7 枚組ハンドを一括評価する。

    Parameters
    ----------
    hands : np.ndarray, shape (N, 7), dtype int32
        カード ID (0〜51) の配列。

    Returns
    -------
    np.ndarray, shape (N,), dtype int64
        各ハンドのスコア。スコアが高いほど強いハンド。
    """
    N = hands.shape[0]
    ranks = hands // 4  # (N, 7), 値 0–12
    suits = hands % 4  # (N, 7), 値 0–3

    # ── 各ランクの枚数 ────────────────────────────────────────────────────────
    # rank_counts[i, r] = ハンド i においてランク r のカード枚数
    rank_counts = (
        (ranks[:, :, None] == np.arange(13)).sum(axis=1).astype(np.int32)
    )  # (N, 13)

    # ── 各スートの枚数 ────────────────────────────────────────────────────────
    suit_counts = (
        (suits[:, :, None] == np.arange(4)).sum(axis=1).astype(np.int32)
    )  # (N, 4)

    # ── フラッシュ ────────────────────────────────────────────────────────────
    flush_suit = suit_counts.argmax(axis=1)  # (N,)
    is_flush = suit_counts[np.arange(N), flush_suit] >= 5  # (N,)

    # フラッシュのスートに属するカードを特定する
    flush_mask = suits == flush_suit[:, None]  # (N, 7)

    # flush_rank_present[i, r] = ハンド i においてランク r のフラッシュスートカードが存在するか
    flush_rank_present = (
        (ranks[:, :, None] == np.arange(13)) & flush_mask[:, :, None]
    ).any(
        axis=1
    )  # (N, 13)

    # ── ランクの存在を表すビットマスク ───────────────────────────────────────
    rank_present = rank_counts > 0  # (N, 13)
    powers = 1 << np.arange(13, dtype=np.int32)  # (13,)
    rank_bits = (rank_present.astype(np.int32) * powers).sum(axis=1)  # (N,)
    flush_rank_bits = (flush_rank_present.astype(np.int32) * powers).sum(axis=1)  # (N,)

    # ── 参照テーブルによるストレート判定 ─────────────────────────────────────
    straight_top = _STRAIGHT_TOP_LUT[rank_bits]  # (N,) int8; ストレートなしの場合 -1
    flush_straight_top = _STRAIGHT_TOP_LUT[flush_rank_bits]  # (N,) int8
    is_straight = straight_top >= 0  # (N,)
    is_sf = is_flush & (flush_straight_top >= 0)  # (N,)

    # ── 枚数の多い順・ランクの高い順で並べ替え ────────────────────────────────
    sort_key = rank_counts * 13 + np.arange(13)  # (N, 13)
    order = np.argsort(-sort_key, axis=1)  # (N, 13)
    sc = rank_counts[np.arange(N)[:, None], order]  # 並べ替え後の枚数  (N, 13)
    sr = order  # 並べ替え後のランク   (N, 13)

    # ── 役判定フラグ ──────────────────────────────────────────────────────────
    has_quads = sc[:, 0] == 4
    has_trips = sc[:, 0] == 3
    has_fh = has_trips & (sc[:, 1] >= 2)
    has_two_pair = (sc[:, 0] == 2) & (sc[:, 1] == 2)
    has_one_pair = (sc[:, 0] == 2) & (sc[:, 1] != 2)

    # ── フラッシュの強さ比較用: フラッシュスートの上位 5 ランク ─────────────────
    flush_sort_key = np.where(flush_rank_present, np.arange(13), -1)  # (N, 13)
    flush_order = np.argsort(-flush_sort_key, axis=1)  # (N, 13) 降順
    fr = flush_order[:, :5]  # (N, 5) 上位 5 フラッシュランク

    # ── 同点比較用ヘルパー ────────────────────────────────────────────────────
    def _tb(*rank_cols) -> np.ndarray:
        """最大 5 つのランク配列を 1 つの int64 値に詰め込む。"""
        result = np.zeros(N, dtype=np.int64)
        for i, col in enumerate(rank_cols[:5]):
            result |= col.astype(np.int64) << (4 * (4 - i))
        return result

    # ── スコアの算出 ──────────────────────────────────────────────────────────
    scores = np.zeros(N, dtype=np.int64)

    # 0: ハイカード
    scores[:] = _tb(sr[:, 0], sr[:, 1], sr[:, 2], sr[:, 3], sr[:, 4])

    # 1: ワンペア
    m = has_one_pair
    scores[m] = (np.int64(1) << 20) | _tb(sr[:, 0], sr[:, 1], sr[:, 2], sr[:, 3])[m]

    # 2: ツーペア
    m = has_two_pair & ~has_trips
    scores[m] = (np.int64(2) << 20) | _tb(sr[:, 0], sr[:, 1], sr[:, 2])[m]

    # 3: スリーカード
    m = has_trips & ~has_fh
    scores[m] = (np.int64(3) << 20) | _tb(sr[:, 0], sr[:, 1], sr[:, 2])[m]

    # 4: ストレート
    scores[is_straight] = (np.int64(4) << 20) | straight_top[is_straight].astype(
        np.int64
    )

    # 5: フラッシュ
    m = is_flush & ~is_sf
    scores[m] = (np.int64(5) << 20) | _tb(
        fr[:, 0], fr[:, 1], fr[:, 2], fr[:, 3], fr[:, 4]
    )[m]

    # 6: フルハウス
    scores[has_fh] = (np.int64(6) << 20) | _tb(sr[:, 0], sr[:, 1])[has_fh]

    # 7: フォーカード
    scores[has_quads] = (np.int64(7) << 20) | _tb(sr[:, 0], sr[:, 1])[has_quads]

    # 8: ストレートフラッシュ
    scores[is_sf] = (np.int64(8) << 20) | flush_straight_top[is_sf].astype(np.int64)

    return scores
