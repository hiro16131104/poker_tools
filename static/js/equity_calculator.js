// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// カード定義
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const RANKS = ['A','K','Q','J','T','9','8','7','6','5','4','3','2'];
const SUITS = ['s','h','d','c'];
const SUIT_SYMBOLS = { s:'♠', h:'♥', d:'♦', c:'♣' };
const SUIT_CLASS    = { s:'spade', h:'heart', d:'diamond', c:'club' };

// カード文字列を生成する（例: 'Ah'）
function cardStr(rank, suit) { return rank + suit; }
// カード表示ラベルを生成する（例: 'A♥'）
function cardLabel(rank, suit) { return rank + SUIT_SYMBOLS[suit]; }

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 状態管理
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const heroCards  = [null, null];                              // ヒーローのハンド（カード文字列 2枚）
const boardCards = [null, null, null, null, null];            // ボードのカード（0〜4枚）
const oppRanges  = { 1: new Set(), 2: new Set(), 3: new Set() }; // 相手ごとの選択済みレンジキー
let numOpponents = 1;                                         // 現在の相手人数（1〜3）

// カードピッカーの選択対象
let pickerTarget = null;   // { type:'hero'|'board' }
let pickerSelected = new Set();  // ピッカーで現在選択中のカード文字列

// レンジピッカーモーダル（スマホ用）の対象相手番号
let rangeModalOpp = null;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ユーティリティ: ヒーロー + ボードで使用中のカードをSetで返す
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function usedCards() {
  const s = new Set();
  heroCards.forEach(c  => c && s.add(c));
  boardCards.forEach(c => c && s.add(c));
  // ピッカー編集中は対象タイプのカードを除外する（再選択可能にするため）
  if (pickerTarget) {
    if (pickerTarget.type === 'hero') {
      heroCards.forEach(c => c && s.delete(c));
    } else {
      boardCards.forEach(c => c && s.delete(c));
    }
  }
  return s;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// カード選択モーダル
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function openPicker(type) {
  pickerTarget = { type };
  // 現在の選択状態をピッカーに反映する
  pickerSelected = new Set();
  if (type === 'hero') {
    heroCards.forEach(c => c && pickerSelected.add(c));
    document.getElementById('picker-title').textContent = 'ハンドを選択（2枚）';
  } else {
    boardCards.forEach(c => c && pickerSelected.add(c));
    document.getElementById('picker-title').textContent = 'ボードカードを選択（0・3〜5枚）';
  }
  document.getElementById('picker-error').textContent = '';
  renderPickerGrid();
  document.getElementById('picker-modal').classList.remove('hidden');
}

function closePicker() {
  document.getElementById('picker-modal').classList.add('hidden');
  pickerTarget = null;
  pickerSelected = new Set();
}

function renderPickerGrid() {
  const grid = document.getElementById('card-picker-grid');
  grid.innerHTML = '';
  const used = usedCards();

  // スート4行 × ランク13列のグリッドを描画する
  SUITS.forEach(suit => {
    RANKS.forEach(rank => {
      const cs = cardStr(rank, suit);
      const disabled = used.has(cs);
      const btn = document.createElement('button');
      btn.className = `card-btn ${SUIT_CLASS[suit]}`;
      if (disabled) btn.classList.add('opacity-40');
      btn.disabled = disabled;
      btn.setAttribute('aria-label', cardLabel(rank, suit));
      if (pickerSelected.has(cs)) btn.classList.add('selected');
      btn.onclick = () => togglePickerCard(cs);
      const rankEl = document.createElement('span');
      rankEl.className = 'cb-rank';
      rankEl.textContent = rank;
      const suitEl = document.createElement('span');
      suitEl.className = 'cb-suit';
      suitEl.textContent = SUIT_SYMBOLS[suit];
      btn.appendChild(rankEl);
      btn.appendChild(suitEl);
      grid.appendChild(btn);
    });
  });
  updatePickerCount();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 選択済みカードの表示欄
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function suitOf(cs) { return cs ? cs[1] : null; }

function renderSlot(el, cs) {
  if (!cs) {
    // 未選択状態にリセットする
    el.innerHTML = '?';
    el.className = el.className.replace(/\s*(spade|heart|diamond|club|filled)/g, '');
    el.classList.remove('filled');
  } else {
    // スート色クラスと filled クラスを付与する
    const suit = suitOf(cs);
    el.className = el.className.replace(/\s*(spade|heart|diamond|club)/g, '');
    el.classList.add(SUIT_CLASS[suit], 'filled');
    // ランクを上・スートを下に並べる
    el.innerHTML = `<span class="cs-rank">${cs[0]}</span><span class="cs-suit">${SUIT_SYMBOLS[suit]}</span>`;
  }
}

function updateCardSlots() {
  heroCards.forEach((c, i) => renderSlot(document.getElementById(`hero-card-${i}`), c));
  boardCards.forEach((c, i) => renderSlot(document.getElementById(`board-card-${i}`), c));
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ハンドレンジ選択グリッド
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const RANK_LABELS = RANKS; // A K Q J T 9 8 7 6 5 4 3 2

// マトリックスのセル位置からレンジキーを生成する
function rangeKey(ri, ci) {
  // ri = 行インデックス（0=A...12=2）、ci = 列インデックス
  if (ri === ci) return RANK_LABELS[ri] + RANK_LABELS[ci];        // ペア
  if (ri < ci)  return RANK_LABELS[ri] + RANK_LABELS[ci] + 's';  // スーテッド
  return RANK_LABELS[ci] + RANK_LABELS[ri] + 'o';                 // オフスーツ
}

// セルのタイプを返す（pair / suited / offsuit）
function cellType(ri, ci) {
  if (ri === ci) return 'pair';
  if (ri < ci)  return 'suited';
  return 'offsuit';
}

// レンジキーに対応するコンボ数を返す
function comboCount(key) {
  if (key.length === 2) return 6;  // ペア: 6コンボ
  if (key.endsWith('s')) return 4; // スーテッド: 4コンボ
  return 12;                        // オフスーツ: 12コンボ
}

const TOTAL_COMBOS = 1326; // C(52,2)

function buildMatrix(oppNum, rootId) {
  const root = document.getElementById(rootId);
  root.innerHTML = '';

  // クリアボタンをセクションヘッダーの右肩に配置する
  const headerActions = document.getElementById(`opp${oppNum}-header-actions`);
  if (headerActions) {
    const clearBtn = document.createElement('button');
    clearBtn.textContent = 'クリア';
    clearBtn.className = 'text-xs text-gray-400 hover:text-red-500 border border-gray-200 hover:border-red-300 rounded px-2 py-0.5 transition-colors';
    clearBtn.setAttribute('aria-label', 'レンジをクリア');
    clearBtn.onclick = () => { oppRanges[oppNum].clear(); refreshMatrix(oppNum); updateCalcButton(); };
    headerActions.appendChild(clearBtn);
  }

  // コンボ数ラベルを作成する
  const countLabel = document.createElement('p');
  countLabel.className = 'text-xs text-gray-500 mb-2';
  countLabel.id = `opp${oppNum}-count`;
  countLabel.textContent = '選択中: 0 コンボ (0.0%)';
  root.appendChild(countLabel);

  // スマホ用レンジプレビュー（タップするとモーダルが開く）
  const previewWrap = document.createElement('div');
  previewWrap.id = `opp${oppNum}-preview-wrap`;
  previewWrap.className = 'sm:hidden cursor-pointer rounded-lg overflow-hidden border border-gray-200 active:opacity-60 transition-opacity';
  previewWrap.setAttribute('role', 'button');
  previewWrap.setAttribute('aria-label', `相手${oppNum}のレンジを選択する`);
  previewWrap.onclick = () => openRangePicker(oppNum);

  const previewGrid = document.createElement('div');
  previewGrid.className = 'grid grid-cols-[repeat(13,1fr)] gap-px w-full';
  previewGrid.id = `opp${oppNum}-preview-grid`;

  for (let ri = 0; ri < 13; ri++) {
    for (let ci = 0; ci < 13; ci++) {
      const key = rangeKey(ri, ci);
      const type = cellType(ri, ci);
      const cell = document.createElement('div');
      cell.className = `range-preview-cell ${type}`;
      cell.dataset.key = key;
      cell.textContent = key;
      previewGrid.appendChild(cell);
    }
  }

  previewWrap.appendChild(previewGrid);
  root.appendChild(previewWrap);

  // レンジ表を横スクロール可能なコンテナで囲む（スマホでは非表示）
  const wrapper = document.createElement('div');
  wrapper.className = 'overflow-x-auto select-none hidden sm:block';

  const grid = document.createElement('div');
  grid.className = 'grid grid-cols-[repeat(13,1fr)] gap-px w-full';
  grid.id = `opp${oppNum}-grid`;
  grid.style.minWidth = '280px';

  // 13×13 のセルを生成する
  for (let ri = 0; ri < 13; ri++) {
    for (let ci = 0; ci < 13; ci++) {
      const key = rangeKey(ri, ci);
      const type = cellType(ri, ci);
      const cell = document.createElement('div');
      cell.className = `range-cell ${type}`;
      cell.dataset.key = key;
      cell.dataset.opp = oppNum;
      cell.textContent = key;
      cell.setAttribute('aria-label', key);
      grid.appendChild(cell);
    }
  }

  wrapper.appendChild(grid);
  root.appendChild(wrapper);

  attachDragHandlers(oppNum, grid);
}

// ピッカーの選択枚数表示を更新する
function updatePickerCount() {
  const el = document.getElementById('picker-count');
  if (el) el.textContent = `選択中: ${pickerSelected.size} 枚`;
}

// ピッカーでカードをトグル選択する
function togglePickerCard(cs) {
  if (pickerSelected.has(cs)) {
    pickerSelected.delete(cs);
  } else {
    pickerSelected.add(cs);
  }
  document.getElementById('picker-error').textContent = '';
  renderPickerGrid();
}

// 選択を確定してスロットに反映する
function confirmPicker() {
  if (!pickerTarget) return;
  const { type } = pickerTarget;
  const selected = [...pickerSelected];
  const n = selected.length;
  const errEl = document.getElementById('picker-error');

  if (type === 'hero') {
    if (n !== 2) {
      errEl.textContent = 'ハンドは2枚選択してください。';
      return;
    }
    heroCards[0] = selected[0];
    heroCards[1] = selected[1];
  } else {
    if (n === 1 || n === 2) {
      errEl.textContent = 'フロップは3枚まとめて入力してください（1枚・2枚は不可）。';
      return;
    }
    // ボードスロットに順番どおり割り当てる
    for (let i = 0; i < 5; i++) boardCards[i] = selected[i] ?? null;
  }

  updateCardSlots();
  updateCalcButton();
  closePicker();
}

// ヒーローのハンドをクリアする
function clearHeroCards() {
  heroCards[0] = null;
  heroCards[1] = null;
  updateCardSlots();
  updateCalcButton();
}

// ボードカードをすべてクリアする
function clearBoardCards() {
  for (let i = 0; i < 5; i++) boardCards[i] = null;
  updateCardSlots();
  updateCalcButton();
}

function refreshMatrix(oppNum) {
  const grid = document.getElementById(`opp${oppNum}-grid`);
  if (!grid) return;
  // 選択状態を現在のレンジに合わせて更新する
  grid.querySelectorAll('.range-cell').forEach(cell => {
    const selected = oppRanges[oppNum].has(cell.dataset.key);
    cell.classList.toggle('selected', selected);
  });
  refreshMobilePreview(oppNum);
  updateComboCount(oppNum);
}

// スマホ用プレビューグリッドの選択状態を同期する
function refreshMobilePreview(oppNum) {
  const grid = document.getElementById(`opp${oppNum}-preview-grid`);
  if (!grid) return;
  grid.querySelectorAll('.range-preview-cell').forEach(cell => {
    cell.classList.toggle('selected', oppRanges[oppNum].has(cell.dataset.key));
  });
}

function updateComboCount(oppNum) {
  let total = 0;
  oppRanges[oppNum].forEach(key => total += comboCount(key));
  const pct = ((total / TOTAL_COMBOS) * 100).toFixed(1);
  const text = `選択中: ${total} コンボ (${pct}%)`;

  const label = document.getElementById(`opp${oppNum}-count`);
  if (label) label.textContent = text;

  // レンジモーダルが同じ相手で開いていれば、モーダルのカウントも更新する
  if (rangeModalOpp === oppNum) {
    const modalCount = document.getElementById('range-modal-count');
    if (modalCount) modalCount.textContent = text;
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ドラッグ / タッチ操作によるセル選択
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function attachDragHandlers(oppNum, grid) {
  let isDragging = false;
  let dragMode = null;    // 'select'（選択）| 'deselect'（解除）

  // 指定座標にあるセル要素を返す
  function cellAt(x, y) {
    const el = document.elementFromPoint(x, y);
    return el && el.classList.contains('range-cell') && el.dataset.opp == oppNum ? el : null;
  }

  // ドラッグ開始時の処理（select / deselect モードを決定する）
  function startDrag(cell) {
    isDragging = true;
    const key = cell.dataset.key;
    dragMode = oppRanges[oppNum].has(key) ? 'deselect' : 'select';
    applyDragToCell(cell);
  }

  // ドラッグ中にセルへ選択/解除を適用する
  function applyDragToCell(cell) {
    const key = cell.dataset.key;
    if (dragMode === 'select') {
      if (!oppRanges[oppNum].has(key)) {
        oppRanges[oppNum].add(key);
        cell.classList.add('selected');
        cell.classList.remove('drag-preview');
      }
    } else {
      if (oppRanges[oppNum].has(key)) {
        oppRanges[oppNum].delete(key);
        cell.classList.remove('selected', 'drag-preview');
      }
    }
  }

  // ドラッグ終了時の処理
  function endDrag() {
    isDragging = false;
    dragMode = null;
    updateComboCount(oppNum);
    updateCalcButton();
  }

  // マウスイベント
  grid.addEventListener('mousedown', e => {
    const cell = e.target.closest('.range-cell');
    if (!cell || cell.dataset.opp != oppNum) return;
    e.preventDefault();
    startDrag(cell);
  });
  grid.addEventListener('mousemove', e => {
    if (!isDragging) return;
    const cell = cellAt(e.clientX, e.clientY);
    if (cell) applyDragToCell(cell);
  });
  document.addEventListener('mouseup', () => { if (isDragging) endDrag(); });

  // タッチイベント
  grid.addEventListener('touchstart', e => {
    const t = e.touches[0];
    const cell = cellAt(t.clientX, t.clientY);
    if (!cell || cell.dataset.opp != oppNum) return;
    e.preventDefault();
    startDrag(cell);
  }, { passive: false });
  grid.addEventListener('touchmove', e => {
    if (!isDragging) return;
    e.preventDefault();
    const t = e.touches[0];
    const cell = cellAt(t.clientX, t.clientY);
    if (cell) applyDragToCell(cell);
  }, { passive: false });
  grid.addEventListener('touchend', () => { if (isDragging) endDrag(); });
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// レンジピッカーモーダル（スマホ用）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function openRangePicker(oppNum) {
  rangeModalOpp = oppNum;
  document.getElementById('range-modal-title').textContent = `相手${oppNum} のレンジ`;
  // クリアボタンのハンドラを対象の相手番号に合わせて設定する
  document.getElementById('range-modal-clear').onclick = () => {
    oppRanges[oppNum].clear();
    buildRangeModalGrid(oppNum);
    updateComboCount(oppNum);
    updateCalcButton();
  };
  buildRangeModalGrid(oppNum);
  updateComboCount(oppNum);
  document.getElementById('range-modal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeRangePicker() {
  // モーダルのグリッド選択状態をインライングリッドに同期する
  if (rangeModalOpp !== null) refreshMatrix(rangeModalOpp);
  rangeModalOpp = null;
  document.getElementById('range-modal').classList.add('hidden');
  document.body.style.overflow = '';
  updateCalcButton();
}

// モーダル内の 13×13 グリッドを構築する（ハンドラは初期化時に一度だけ付与するため、ここでは付与しない）
function buildRangeModalGrid(oppNum) {
  const grid = document.getElementById('range-modal-grid');
  grid.innerHTML = '';
  for (let ri = 0; ri < 13; ri++) {
    for (let ci = 0; ci < 13; ci++) {
      const key = rangeKey(ri, ci);
      const type = cellType(ri, ci);
      const cell = document.createElement('div');
      cell.className = `range-cell ${type}${oppRanges[oppNum].has(key) ? ' selected' : ''}`;
      cell.dataset.key = key;
      cell.dataset.opp = String(oppNum);
      cell.textContent = key;
      cell.setAttribute('aria-label', key);
      grid.appendChild(cell);
    }
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 相手の人数切り替え
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function setNumOpponents(n) {
  // 減少した場合、非表示になる相手のレンジをクリアする
  for (let i = n + 1; i <= 3; i++) {
    oppRanges[i].clear();
    const section = document.getElementById(`opp${i}-section`);
    if (section) section.classList.add('hidden');
  }
  numOpponents = n;
  // 増加した相手のセクションを表示し、マトリックスが未生成なら構築する
  for (let i = 2; i <= n; i++) {
    const section = document.getElementById(`opp${i}-section`);
    if (section) section.classList.remove('hidden');
    if (!document.getElementById(`opp${i}-grid`)) {
      buildMatrix(i, `opp${i}-matrix-root`);
    }
  }
  // 人数選択ボタンのアクティブ状態を更新する
  for (let i = 1; i <= 3; i++) {
    const btn = document.getElementById(`opp-count-btn-${i}`);
    if (!btn) continue;
    if (i === n) {
      btn.classList.add('bg-indigo-600', 'text-white', 'border-indigo-600');
      btn.classList.remove('bg-white', 'text-gray-600', 'border-gray-200', 'hover:text-indigo-600', 'hover:border-indigo-300');
    } else {
      btn.classList.remove('bg-indigo-600', 'text-white', 'border-indigo-600');
      btn.classList.add('bg-white', 'text-gray-600', 'border-gray-200', 'hover:text-indigo-600', 'hover:border-indigo-300');
    }
  }
  updateCalcButton();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 計算ボタンの有効/無効状態を更新する
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function updateCalcButton() {
  const heroReady = heroCards[0] && heroCards[1];
  const opp1Ready = oppRanges[1].size > 0;
  const btn  = document.getElementById('calc-btn');
  const hint = document.getElementById('calc-hint');

  if (heroReady && opp1Ready) {
    btn.disabled = false;
    hint.textContent = '';
  } else {
    btn.disabled = true;
    // 未入力項目に応じてヒントメッセージを表示する
    if (!heroReady && !opp1Ready) {
      hint.textContent = 'ハンド2枚と相手1のレンジを入力してください。';
    } else if (!heroReady) {
      hint.textContent = 'あなたのハンドを2枚選択してください。';
    } else {
      hint.textContent = '相手1 のレンジを1コンボ以上選択してください。';
    }
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// エクイティ計算
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async function runCalculation() {
  const btn = document.getElementById('calc-btn');
  const label = document.getElementById('calc-label');
  const spinner = document.getElementById('calc-spinner');
  const errEl = document.getElementById('result-error');

  // 計算中はボタンを無効化してスピナーを表示する
  btn.disabled = true;
  label.textContent = '計算中...';
  spinner.classList.remove('hidden');
  errEl.classList.add('hidden');

  // 有効な相手のみリクエストに含める
  const opponents = [];
  for (let i = 1; i <= numOpponents; i++) {
    if (oppRanges[i].size > 0) {
      opponents.push({ range_keys: [...oppRanges[i]] });
    }
  }

  const body = {
    hero_hand: heroCards.filter(Boolean),
    board: boardCards.filter(Boolean),
    opponents,
  };

  try {
    const res = await fetch('/equity-calculator/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      errEl.textContent = data.error || '計算に失敗しました。';
      errEl.classList.remove('hidden');
      setResults(null);
    } else {
      setResults(data);
    }
  } catch (e) {
    errEl.textContent = 'ネットワークエラーが発生しました。';
    errEl.classList.remove('hidden');
    setResults(null);
  } finally {
    // 計算完了後にボタン状態を元に戻す
    btn.disabled = false;
    label.textContent = '計算する';
    spinner.classList.add('hidden');
    updateCalcButton();
  }
}

// 計算結果を画面に反映する
function setResults(data) {
  const fmt = v => `${v.toFixed(2)}%`;
  document.getElementById('result-equity').textContent = data ? fmt(data.equity)    : '--.--%';
  document.getElementById('result-win').textContent    = data ? fmt(data.win_rate)  : '--.--%';
  document.getElementById('result-chop').textContent   = data ? fmt(data.chop_rate) : '--.--%';

  // エクイティの95%信頼区間の誤差幅 (±1.96 * sqrt(p*(1-p)/N)) を表示する
  const marginEl = document.getElementById('result-margin');
  if (marginEl) {
    if (data) {
      const p = data.equity / 100;
      const margin = 1.96 * Math.sqrt(p * (1 - p) / 200_000) * 100;
      marginEl.textContent = `±${margin.toFixed(2)}%`;
    } else {
      marginEl.textContent = '±0.22%';
    }
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 初期化
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// モーダルの背景クリックでピッカーを閉じる
document.getElementById('picker-modal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closePicker();
});

// レンジモーダルの背景クリックで閉じる
document.getElementById('range-modal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeRangePicker();
});

// 相手1のマトリックスを生成して初期状態を設定する
buildMatrix(1, 'opp1-matrix-root');
setNumOpponents(1);

// モーダルグリッドのドラッグハンドラを一度だけ付与する
// ※ buildRangeModalGrid を呼ぶたびに付与すると累積して競合が起きるため、ここで1回のみ設定する
(function () {
  const grid = document.getElementById('range-modal-grid');
  let isDragging = false;
  let dragMode = null;

  // 指定座標にある、現在の相手に属するセルを返す
  function cellAt(x, y) {
    const el = document.elementFromPoint(x, y);
    return el && el.classList.contains('range-cell') && rangeModalOpp !== null && el.dataset.opp == rangeModalOpp
      ? el : null;
  }

  // ドラッグ開始時の処理
  function startDrag(cell) {
    if (rangeModalOpp === null) return;
    isDragging = true;
    const key = cell.dataset.key;
    dragMode = oppRanges[rangeModalOpp].has(key) ? 'deselect' : 'select';
    applyDragToCell(cell);
  }

  // ドラッグ中にセルへ選択/解除を適用する
  function applyDragToCell(cell) {
    if (rangeModalOpp === null) return;
    const key = cell.dataset.key;
    if (dragMode === 'select') {
      if (!oppRanges[rangeModalOpp].has(key)) {
        oppRanges[rangeModalOpp].add(key);
        cell.classList.add('selected');
        cell.classList.remove('drag-preview');
      }
    } else {
      if (oppRanges[rangeModalOpp].has(key)) {
        oppRanges[rangeModalOpp].delete(key);
        cell.classList.remove('selected', 'drag-preview');
      }
    }
  }

  // ドラッグ終了時の処理
  function endDrag() {
    isDragging = false;
    dragMode = null;
    if (rangeModalOpp !== null) updateComboCount(rangeModalOpp);
    updateCalcButton();
  }

  // マウスイベント
  grid.addEventListener('mousedown', e => {
    const cell = e.target.closest('.range-cell');
    if (!cell) return;
    e.preventDefault();
    startDrag(cell);
  });
  grid.addEventListener('mousemove', e => {
    if (!isDragging) return;
    const cell = cellAt(e.clientX, e.clientY);
    if (cell) applyDragToCell(cell);
  });
  document.addEventListener('mouseup', () => { if (isDragging) endDrag(); });

  // タッチイベント
  grid.addEventListener('touchstart', e => {
    const t = e.touches[0];
    const cell = cellAt(t.clientX, t.clientY);
    if (!cell) return;
    e.preventDefault();
    startDrag(cell);
  }, { passive: false });
  grid.addEventListener('touchmove', e => {
    if (!isDragging) return;
    e.preventDefault();
    const t = e.touches[0];
    const cell = cellAt(t.clientX, t.clientY);
    if (cell) applyDragToCell(cell);
  }, { passive: false });
  grid.addEventListener('touchend', () => { if (isDragging) endDrag(); });
}());
