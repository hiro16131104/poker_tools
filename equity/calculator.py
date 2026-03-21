"""
モンテカルロ法によるエクイティ計算モジュール (NumPy 一括処理, 200,000 試行)。

各試行で行う処理:
  1. 使用済みカードを除いたレンジから、各対戦相手のハンドを重複なしで無作為に選ぶ。
  2. 残りのデッキからボードの未公開カードを無作為に引く。
  3. 全員の 7 枚組ハンドを評価し、ヒーローの結果を判定する。

戻り値: ヒーローの (エクイティ%, 勝率%, チョップ率%) のタプル。
"""

from __future__ import annotations

import numpy as np

from .evaluator import batch_evaluate_7
from .range_parser import card_str_to_id, expand_range_keys

N_TRIALS = 200_000


def calculate_equity(
    hero_hand: list[str],
    board: list[str],
    opponents: list[dict],
) -> tuple[float, float, float]:
    """
    Parameters
    ----------
    hero_hand : list[str]
        ちょうど 2 枚のカード文字列 (例: ["Ah", "Kd"])。
    board : list[str]
        0, 3, 4, または 5 枚のカード文字列。
    opponents : list[dict]
        各要素は "range_keys": list[str] キーを持つ辞書。
        対戦相手の数は 1 〜 3。

    Returns
    -------
    (equity, win_rate, chop_rate) を [0, 100] の float で返す。
    """
    N = N_TRIALS

    hero_ids = [card_str_to_id(c) for c in hero_hand]
    board_ids = [card_str_to_id(c) for c in board]
    fixed_used = set(hero_ids) | set(board_ids)

    n_board = len(board_ids)
    n_fill = 5 - n_board  # ボードに補充が必要な枚数

    # ── 対戦相手のレンジを構築し、使用済みカードを除いて絞り込む ─────────────
    ranges_filtered: list[np.ndarray] = []
    for opp in opponents:
        combos = expand_range_keys(opp["range_keys"])
        valid = [c for c in combos if not (set(c) & fixed_used)]
        if not valid:
            raise ValueError("Opponent range is empty after filtering dead cards.")
        ranges_filtered.append(np.array(valid, dtype=np.int32))  # (M, 2)

    # ── 各対戦相手のハンドを無作為に選択（先に確定した相手との重複を解消） ──
    opp_hands: list[np.ndarray] = []
    for r in ranges_filtered:
        idx = np.random.randint(0, len(r), N)
        hand = r[idx]  # (N, 2)
        # 先に確定した全相手のカードと重複している試行を最大 30 回再抽選する
        for _ in range(30):
            if not opp_hands:
                break
            conflict = np.zeros(N, dtype=bool)
            for prev in opp_hands:
                conflict |= (hand[:, 0:1] == prev).any(axis=1) | (
                    hand[:, 1:2] == prev
                ).any(axis=1)
            n_conf = int(conflict.sum())
            if n_conf == 0:
                break
            hand[conflict] = r[np.random.randint(0, len(r), n_conf)]
        opp_hands.append(hand)

    # ── ヒーローとボードのカードを除いたデッキを構築 ─────────────────────────
    base_deck = np.array([c for c in range(52) if c not in fixed_used], dtype=np.int32)
    D = len(base_deck)

    # ── ボード補充カードを無作為に抽出 ───────────────────────────────────────
    board_fill: np.ndarray | None = None
    if n_fill > 0:
        # デッキの N 通りの無作為な並び替えを生成 (形状 N × D)
        perm = np.argsort(np.random.rand(N, D), axis=1)
        deal = base_deck[perm]  # (N, D) – 無作為なカードの引き順

        # 対戦相手のカードをボードカードとして使わないよう除外フラグを立てる
        is_excl = np.zeros((N, D), dtype=bool)
        for hand in opp_hands:
            is_excl |= (deal == hand[:, 0:1]) | (deal == hand[:, 1:2])

        # 除外されていないカードの累積個数
        valid_rank = (~is_excl).cumsum(axis=1)  # (N, D)

        board_fill = np.empty((N, n_fill), dtype=np.int32)
        arange_N = np.arange(N)
        for k in range(1, n_fill + 1):
            target_mask = (valid_rank == k) & ~is_excl  # (N, D) bool
            col_idx = target_mask.argmax(axis=1)  # (N,)
            board_fill[:, k - 1] = deal[arange_N, col_idx]

    # ── 7 枚組ハンドの組み立て ────────────────────────────────────────────────
    def _make_hand(hole_cards: np.ndarray) -> np.ndarray:
        """
        hole_cards : (N, 2) int32 – プレイヤーのホールカード 2 枚
        戻り値      : (N, 7) int32 – 7 枚組のフルハンド
        """
        hand = np.empty((N, 7), dtype=np.int32)
        hand[:, :2] = hole_cards
        if n_board > 0:
            hand[:, 2 : 2 + n_board] = np.array(board_ids, dtype=np.int32)
        if n_fill > 0:
            hand[:, 2 + n_board :] = board_fill  # type: ignore[index]
        return hand

    hero_hole = np.broadcast_to(np.array(hero_ids, dtype=np.int32), (N, 2)).copy()

    # ── ハンドの評価 ──────────────────────────────────────────────────────────
    hero_scores = batch_evaluate_7(_make_hand(hero_hole))  # (N,)
    opp_scores = [batch_evaluate_7(_make_hand(h)) for h in opp_hands]  # list of (N,)

    # 相手の中での最大スコア
    max_opp = opp_scores[0].copy()
    for s in opp_scores[1:]:
        np.maximum(max_opp, s, out=max_opp)

    # ── 勝ち / チョップ / 負けの判定 ─────────────────────────────────────────
    # 「勝ち」= ヒーローのスコアが全員の中で最も高い
    # 「チョップ」= ヒーローが同率トップだが単独勝利でない
    hero_at_top = hero_scores >= max_opp
    strict_wins = hero_scores > max_opp
    chops = hero_at_top & ~strict_wins

    # ── エクイティ（期待ポット取得割合）の計算 ────────────────────────────────
    # 全員の最大スコアを求め、同率トップが何人いるかを数えて按分する
    all_max = np.maximum(hero_scores, max_opp)
    at_max_count = (hero_scores == all_max).astype(np.float64)
    for s in opp_scores:
        at_max_count += (s == all_max).astype(np.float64)
    hero_share = np.where(hero_at_top, 1.0 / at_max_count, 0.0)

    equity = float(hero_share.mean() * 100)
    win_rate = float(strict_wins.mean() * 100)
    chop_rate = float(chops.mean() * 100)

    return equity, win_rate, chop_rate
