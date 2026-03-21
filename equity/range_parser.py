"""
ハンドレンジキーの解析モジュール: レンジキー (例: "AKs", "AA", "AKo") をカード ID の組み合わせリストに変換する。

カードの数値表現:  card_id = rank_index * 4 + suit_index
  rank_index: 0='2', 1='3', ..., 12='A'
  suit_index: 0='s', 1='h', 2='d', 3='c'

カード文字列の書式: ランク文字 + スート文字  (例: "Ah", "2c", "Ts")
ハンドレンジキーの書式:
  ポケットペア : "AA", "KK", ..., "22"          (各 6 通り)
  スーテッド   : "AKs", "QJs", ..., "32s"        (各 4 通り)
  オフスート   : "AKo", "QJo", ..., "32o"        (各 12 通り)
"""

from __future__ import annotations

RANKS = "AKQJT98765432"  # インデックス 0 = A, 12 = 2
SUITS = "shdc"  # インデックス 0 = s, 1 = h, 2 = d, 3 = c

_RANK_IDX: dict[str, int] = {r: i for i, r in enumerate(reversed(RANKS))}
# reversed により '2'=0, '3'=1, ..., 'A'=12 となる
_SUIT_IDX: dict[str, int] = {s: i for i, s in enumerate(SUITS)}


def card_str_to_id(s: str) -> int:
    """カード文字列 ('Ah' など) を card_id に変換する。"""
    return _RANK_IDX[s[0]] * 4 + _SUIT_IDX[s[1]]


def card_id_to_str(cid: int) -> str:
    """card_id をカード文字列 ('Ah' など) に変換する。"""
    rank_idx = cid // 4
    suit_idx = cid % 4
    rank_char = RANKS[12 - rank_idx]  # RANKS は A..2 の順; rank_idx 12=A → RANKS[0]
    return rank_char + SUITS[suit_idx]


def expand_range_key(key: str) -> list[tuple[int, int]]:
    """
    レンジキーを (card_id_1, card_id_2) タプルのリストに展開する。
    card_id_1 > card_id_2 の順序は保証しない。同じキー種別内では順序が一定。
    """
    combos: list[tuple[int, int]] = []

    if len(key) == 2:
        # ポケットペア (例: "AA") — 2文字が同じランクであること
        r = key[0]
        if key[1] != r or r not in _RANK_IDX:
            return combos
        for i in range(4):
            for j in range(i + 1, 4):
                combos.append(
                    (
                        _RANK_IDX[r] * 4 + i,
                        _RANK_IDX[r] * 4 + j,
                    )
                )

    elif len(key) == 3:
        r1, r2, hand_type = key[0], key[1], key[2]
        # r1 と r2 は異なるランクであること (例: "AAs" は無効)
        if r1 not in _RANK_IDX or r2 not in _RANK_IDX or r1 == r2:
            return combos
        if hand_type == "s":
            # スーテッド (例: "AKs")
            for si in range(4):
                combos.append(
                    (
                        _RANK_IDX[r1] * 4 + si,
                        _RANK_IDX[r2] * 4 + si,
                    )
                )
        elif hand_type == "o":
            # オフスート (例: "AKo")
            for s1 in range(4):
                for s2 in range(4):
                    if s1 != s2:
                        combos.append(
                            (
                                _RANK_IDX[r1] * 4 + s1,
                                _RANK_IDX[r2] * 4 + s2,
                            )
                        )

    return combos


def expand_range_keys(keys: list[str]) -> list[tuple[int, int]]:
    """レンジキーのリストを全組み合わせに展開する。"""
    combos: list[tuple[int, int]] = []
    for key in keys:
        combos.extend(expand_range_key(key))
    return combos
