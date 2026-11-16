/* 中大吃什麼 — 共用函式（首頁與店家頁都會載入）
 * 時間一律以台灣時間 Asia/Taipei 計算，不受瀏覽者電腦時區影響。 */
(function () {
  const DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

  function taipeiNow() {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Taipei", weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).formatToParts(new Date());
    const get = (t) => parts.find((p) => p.type === t).value;
    return { day: get("weekday").slice(0, 3).toLowerCase(), minutes: (+get("hour") % 24) * 60 + +get("minute") };
  }

  const toMin = (t) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
  const pretty = (r) => r.replace("-", "–");

  /** 回傳 { state: "open" | "soon" | "closed" | "unknown", label } */
  function openStatus(hours) {
    if (!hours) return { state: "unknown", label: "營業時間待確認" };
    const now = taipeiNow();
    const today = hours[now.day] || [];
    if (!today.length) return { state: "closed", label: "今日公休" };
    for (const r of today) {
      let [s, e] = r.split("-");
      if (now.minutes >= toMin(s) && now.minutes < toMin(e)) {
        let left = toMin(e) - now.minutes;
        // 營業到 24:00 且隔天 00:00 接著開 → 其實是跨夜，顯示真正的打烊時間
        if (e === "24:00") {
          const tomorrow = hours[DAYS[(DAYS.indexOf(now.day) + 1) % 7]] || [];
          const cont = tomorrow.find((x) => x.startsWith("00:00-"));
          if (cont) { e = cont.split("-")[1]; left += toMin(e); }
        }
        return left <= 30
          ? { state: "soon", label: `快打烊・${e} 休息` }
          : { state: "open", label: `營業中・至 ${e}` };
      }
    }
    const next = today.map((r) => r.split("-")[0]).find((s) => toMin(s) > now.minutes);
    return next ? { state: "closed", label: `休息中・${next} 開` } : { state: "closed", label: "今日已打烊" };
  }

  /** 給人看的時段：拿掉前一晚延續過來的 00:00-xx，並把 xx-24:00 接上隔天的 00:00-yy 顯示成 xx–yy */
  function displayRanges(hours, day) {
    const i = DAYS.indexOf(day);
    const prev = hours[DAYS[(i + 6) % 7]] || [], next = hours[DAYS[(i + 1) % 7]] || [];
    const prevRunsLate = prev.some((r) => r.endsWith("-24:00"));
    return (hours[day] || [])
      .filter((r) => !(r.startsWith("00:00-") && prevRunsLate))
      .map((r) => {
        const cont = r.endsWith("-24:00") && next.find((x) => x.startsWith("00:00-"));
        return cont ? r.split("-")[0] + "–" + cont.split("-")[1] : pretty(r);
      });
  }

  function todayHours(hours) {
    if (!hours) return "營業時間待確認";
    const r = displayRanges(hours, taipeiNow().day);
    return r.length ? "今日 " + r.join("、") : "今日公休";
  }

  const TILE = {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    opt: { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' },
  };

  function marker(lat, lng, color) {
    return L.circleMarker([lat, lng], {
      radius: 9, color: "#fff", weight: 2.5, fillColor: color, fillOpacity: 1,
    });
  }

  window.NCU = { DAYS, taipeiNow, openStatus, todayHours, TILE, marker };
})();
