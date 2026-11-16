/* 店家頁：營業狀態、今天的營業時間高亮、小地圖 */
(function () {
  const d = JSON.parse(document.getElementById("page-data").textContent);

  const st = NCU.openStatus(d.hours);
  const el = document.querySelector("[data-status]");
  el.textContent = st.label;
  el.dataset.state = st.state;

  const today = NCU.taipeiNow().day;
  const row = document.querySelector(`.hours tr[data-day="${today}"]`);
  if (row) row.classList.add("today");

  if (window.L) {
    const map = L.map("shop-map", { scrollWheelZoom: false }).setView([d.lat, d.lng], 18);
    L.tileLayer(NCU.TILE.url, NCU.TILE.opt).addTo(map);
    NCU.marker(d.lat, d.lng, d.color).addTo(map).bindTooltip(d.name, { permanent: true, direction: "top", offset: [0, -8] });
  }
})();
