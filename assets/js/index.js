/* 首頁：讀取 data/*.json → 分類分頁、區域篩選、營業中篩選、卡片列表、地圖
 * 首頁沒有任何寫死的店家資料；新增店家只需要改 data/shops.json。 */
(async function () {
  const load = (f) => fetch(`data/${f}.json`, { cache: "no-cache" }).then((r) => r.json());
  let categories, areas, shops;
  try {
    [categories, areas, shops] = await Promise.all([load("categories"), load("areas"), load("shops")]);
  } catch (e) {
    document.getElementById("cards").innerHTML =
      '<p class="empty">資料載入失敗。若是直接用檔案開啟，請改用 <code>python3 -m http.server</code> 預覽。</p>';
    return;
  }

  const catById = Object.fromEntries(categories.map((c) => [c.id, c]));
  const areaById = Object.fromEntries(areas.map((a) => [a.id, a]));
  const state = {
    cat: categories.some((c) => c.id === location.hash.slice(1)) ? location.hash.slice(1) : "all",
    area: "all",
    openOnly: false,
  };
  shops.forEach((s) => (s._status = NCU.openStatus(s.hours)));

  /* ---- 地圖 ---- */
  let map = null;
  const markers = {};
  if (window.L) {
    map = L.map("map", { scrollWheelZoom: false }).setView([24.9648, 121.1920], 17);
    L.tileLayer(NCU.TILE.url, NCU.TILE.opt).addTo(map);
    shops.forEach((s) => {
      const c = catById[s.category];
      markers[s.id] = NCU.marker(s.lat, s.lng, c.color).bindPopup(
        `<strong>${s.name}</strong><br>${c.label}・${areaById[s.area].label}<br><a href="shops/${s.id}.html">看店家 →</a>`
      );
    });
  }

  /* ---- 控制列 ---- */
  const tabs = document.getElementById("tabs");
  const chips = document.getElementById("areas");
  const openToggle = document.getElementById("open-only");

  function renderTabs() {
    const count = (id) => shops.filter((s) => id === "all" || s.category === id).length;
    tabs.innerHTML = [{ id: "all", label: "全部", color: "var(--ink)" }, ...categories]
      .map((c) => `<button role="tab" data-cat="${c.id}" aria-selected="${state.cat === c.id}" style="--c:${c.color}">
          ${c.label}<span class="count">${count(c.id)}</span></button>`).join("");
  }
  function renderChips() {
    chips.innerHTML = [{ id: "all", label: "全部區域" }, ...areas]
      .map((a) => `<button data-area="${a.id}" aria-pressed="${state.area === a.id}">${a.label}</button>`).join("");
  }

  tabs.addEventListener("click", (e) => {
    const b = e.target.closest("[data-cat]"); if (!b) return;
    state.cat = b.dataset.cat;
    history.replaceState(null, "", state.cat === "all" ? location.pathname : `#${state.cat}`);
    update();
  });
  chips.addEventListener("click", (e) => {
    const b = e.target.closest("[data-area]"); if (!b) return;
    state.area = b.dataset.area; update();
  });
  openToggle.addEventListener("change", () => { state.openOnly = openToggle.checked; update(); });

  /* ---- 卡片 ---- */
  function card(s) {
    const c = catById[s.category];
    const rec = (s.recommend || [])[0];
    return `<a class="card" href="shops/${s.id}.html" style="--c:${c.color}" data-id="${s.id}">
      <div class="card-top"><span class="pill" style="--c:${c.color}">${c.label}</span><span class="area">${areaById[s.area].label}</span></div>
      <h3>${s.name}</h3>
      ${rec ? `<p class="rec"><span>推薦</span>${rec}</p>` : ""}
      <div class="card-foot">
        <span class="status" data-state="${s._status.state}">${s._status.label}</span>
      </div>
      <p class="card-today">${NCU.todayHours(s.hours)}</p>
    </a>`;
  }

  function update() {
    renderTabs(); renderChips();
    const list = shops
      .filter((s) => state.cat === "all" || s.category === state.cat)
      .filter((s) => state.area === "all" || s.area === state.area)
      .filter((s) => !state.openOnly || s._status.state === "open" || s._status.state === "soon")
      // 營業中的排前面，其餘照名稱
      .sort((a, b) => (rank(a) - rank(b)) || a.name.localeCompare(b.name, "zh-Hant"));

    const box = document.getElementById("cards");
    if (list.length) {
      box.innerHTML = list.map(card).join("");
    } else {
      const c = catById[state.cat];
      box.innerHTML = `<p class="empty">${c && !shops.some((s) => s.category === c.id)
        ? `「${c.label}」還沒有收錄店家。<br>把筆記放進 <code>raw/</code>，請 AI 依 <code>CLAUDE.md</code> 新增即可。`
        : "目前沒有符合條件的店家，換個篩選試試。"}</p>`;
    }
    document.getElementById("result-count").textContent = `${list.length} 間`;

    if (map) {
      Object.values(markers).forEach((m) => m.remove());
      list.forEach((s) => markers[s.id].addTo(map));
      if (list.length) map.fitBounds(L.latLngBounds(list.map((s) => [s.lat, s.lng])).pad(0.35), { maxZoom: 18 });
    }
  }
  const rank = (s) => ({ open: 0, soon: 1, closed: 2, unknown: 3 }[s._status.state]);

  // 卡片 hover 時在地圖上高亮
  document.getElementById("cards").addEventListener("mouseover", (e) => {
    const card = e.target.closest(".card"); if (!card || !map) return;
    const m = markers[card.dataset.id]; if (m) m.openPopup();
  });

  document.getElementById("updated").textContent =
    shops.map((s) => s.verified).sort().slice(-1)[0] || "—";
  update();
})();
