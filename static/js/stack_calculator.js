(() => {
  // ---- ユーティリティ ----
  const parseNum = (val) => {
    const n = parseInt(val.replace(/[,，\s]/g, ""), 10);
    return isNaN(n) ? null : n;
  };

  const formatNum = (val) => {
    const raw = val.replace(/[^\d]/g, "");
    if (!raw) return "";
    return parseInt(raw, 10).toLocaleString("ja-JP");
  };

  // ---- 要素取得 ----
  const stackEl = document.getElementById("stack");
  const sbEl = document.getElementById("sb");
  const bbEl = document.getElementById("bb");
  const anteEl = document.getElementById("ante");
  const bbError = document.getElementById("bb-error");
  const bbResult = document.getElementById("bb-result");
  const mCard = document.getElementById("m-card");
  const mLabel = document.getElementById("m-label");
  const mResult = document.getElementById("m-result");
  const mZone = document.getElementById("m-zone");
  const anteAdjust = document.getElementById("ante-adjust");

  // ---- 数値フォーマット（入力中にカンマ区切り） ----
  [stackEl, sbEl, bbEl].forEach((el) => {
    el.addEventListener("input", function () {
      const fromEnd = this.value.length - this.selectionStart;
      this.value = formatNum(this.value);
      const newPos = Math.max(0, this.value.length - fromEnd);
      this.setSelectionRange(newPos, newPos);
      calculate();
    });
  });

  // ---- アンティ切り替え ----
  anteEl.addEventListener("change", () => {
    anteAdjust.classList.toggle("hidden", !anteEl.checked);
    calculate();
  });

  // ---- 個別クリアボタン ----
  [
    { id: "clear-stack", el: stackEl },
    { id: "clear-sb", el: sbEl },
    { id: "clear-bb", el: bbEl },
  ].forEach(({ id, el }) => {
    document.getElementById(id).addEventListener("click", () => {
      el.value = "";
      calculate();
    });
  });

  // ---- アンティ額 ----
  const getAnte = (bb) => (anteEl.checked ? bb : 0);

  // ---- スタック調整 ----
  const adjustStack = (dir, unit) => {
    const sb = parseNum(sbEl.value);
    const bb = parseNum(bbEl.value);

    let amount;
    if (unit === "sb") amount = sb;
    else if (unit === "bb") amount = bb;
    else if (unit === "bbante") amount = bb !== null ? bb + getAnte(bb) : null;

    if (!amount) return;

    const current = parseNum(stackEl.value) ?? 0;
    stackEl.value = formatNum(String(Math.max(0, current + dir * amount)));
    calculate();
  };

  [
    { id: "btn-sub-sb", dir: -1, unit: "sb" },
    { id: "btn-add-sb", dir: 1, unit: "sb" },
    { id: "btn-sub-bb", dir: -1, unit: "bb" },
    { id: "btn-add-bb", dir: 1, unit: "bb" },
    { id: "btn-sub-bbante", dir: -1, unit: "bbante" },
    { id: "btn-add-bbante", dir: 1, unit: "bbante" },
  ].forEach(({ id, dir, unit }) => {
    document
      .getElementById(id)
      .addEventListener("click", () => adjustStack(dir, unit));
  });

  // ---- 全リセット ----
  document.getElementById("btn-reset").addEventListener("click", () => {
    stackEl.value = "";
    sbEl.value = "";
    bbEl.value = "";
    bbError.classList.add("hidden");
    bbResult.textContent = "---";
    resetMCard();
  });

  // ---- 計算 ----
  const calculate = () => {
    const stack = parseNum(stackEl.value);
    const sb = parseNum(sbEl.value);
    const bb = parseNum(bbEl.value);

    // BB バリデーション
    if (bb !== null && bb <= 0) {
      bbError.classList.remove("hidden");
      bbResult.textContent = "---";
      resetMCard();
      return;
    }
    bbError.classList.add("hidden");

    // BB 換算
    bbResult.textContent =
      stack !== null && bb !== null ? (stack / bb).toFixed(1) : "---";

    // M 値
    if (stack !== null && sb !== null && bb !== null) {
      const pot = sb + bb + getAnte(bb);
      const m = stack / pot;
      mResult.textContent = m.toFixed(1);
      applyMZone(m);
    } else {
      resetMCard();
    }
  };

  // ---- M 値ゾーン定義 ----
  const ZONES = [
    {
      min: 20,
      cardCls: "bg-green-50 border-green-300",
      resultCls: "text-green-800",
      labelCls: "text-green-700",
      zoneCls: "text-green-600",
      name: "通常プレイ可",
    },
    {
      min: 10,
      cardCls: "bg-yellow-50 border-yellow-300",
      resultCls: "text-yellow-800",
      labelCls: "text-yellow-700",
      zoneCls: "text-yellow-600",
      name: "アグレッシブなプレイを推奨",
    },
    {
      min: 5,
      cardCls: "bg-orange-50 border-orange-300",
      resultCls: "text-orange-800",
      labelCls: "text-orange-700",
      zoneCls: "text-orange-600",
      name: "プッシュ/フォールド圏内",
    },
    {
      min: 0,
      cardCls: "bg-red-50 border-red-300",
      resultCls: "text-red-800",
      labelCls: "text-red-700",
      zoneCls: "text-red-600",
      name: "危機的な状況",
    },
  ];

  const applyMZone = (m) => {
    const z = ZONES.find((z) => m >= z.min);
    mCard.className = `rounded-xl p-3 text-center transition-all duration-200 border ${z.cardCls}`;
    mResult.className = `text-xl font-bold ${z.resultCls}`;
    mLabel.className = `text-xs font-semibold uppercase tracking-wider mb-1 ${z.labelCls}`;
    mZone.className = `text-xs mt-0.5 ${z.zoneCls}`;
    mZone.textContent = z.name;
  };

  const resetMCard = () => {
    mCard.className =
      "bg-gray-50 border border-gray-200 rounded-xl p-3 text-center transition-all duration-200";
    mResult.className = "text-xl font-bold text-gray-800";
    mLabel.className =
      "text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1";
    mZone.className = "text-xs text-gray-400 mt-0.5";
    mZone.innerHTML = "&nbsp;";
    mResult.textContent = "---";
  };
})();
