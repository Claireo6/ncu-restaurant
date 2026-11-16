#!/usr/bin/env python3
"""中大吃什麼 — 建置與檢查腳本（只用 Python 標準函式庫）

用法：
    python3 scripts/build.py           檢查資料 → 整理 shops.json 格式 → 產生 shops/*.html
    python3 scripts/build.py --check   只檢查資料，不寫入任何檔案

規則來源：CLAUDE.md。這支腳本是 CLAUDE.md 裡「資料規則」的機器版，
任何檢查失敗都必須修正資料，而不是修改這支腳本來放水。
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SHOPS_DIR = ROOT / "shops"
TEMPLATE = ROOT / "templates" / "shop.html"

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_LABEL = {"mon": "一", "tue": "二", "wed": "三", "thu": "四", "fri": "五", "sat": "六", "sun": "日"}
FIELD_ORDER = ["id", "name", "category", "area", "address", "lat", "lng", "hours",
               "recommend", "items", "review", "notes", "web_ref", "source", "verified"]
REQUIRED = ["id", "name", "category", "area", "lat", "lng", "source", "verified"]

# 中央大學周邊的合理範圍（約 2.5 km 見方）。座標落在外面＝幾乎一定是抄錯或 AI 亂編。
BBOX = {"lat": (24.950, 24.985), "lng": (121.175, 121.210)}

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# 結束時間可以寫 24:00（營業到午夜）；超過午夜要拆到隔天，例如 00:00-02:00
RANGE_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-(([01]\d|2[0-3]):[0-5]\d|24:00)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 檢查
def validate(shops, categories, areas):
    errors = []
    cat_ids = {c["id"] for c in categories}
    area_ids = {a["id"] for a in areas}
    seen = set()

    for i, s in enumerate(shops):
        where = f"shops[{i}] ({s.get('id', '?')})"
        for f in REQUIRED:
            if s.get(f) in (None, ""):
                errors.append(f"{where}: 缺少必填欄位 `{f}`")
        unknown = set(s) - set(FIELD_ORDER)
        if unknown:
            errors.append(f"{where}: 未定義的欄位 {sorted(unknown)}（新欄位要先寫進 CLAUDE.md）")

        sid = s.get("id", "")
        if not ID_RE.match(sid or ""):
            errors.append(f"{where}: id 必須是小寫英數 kebab-case")
        if sid in seen:
            errors.append(f"{where}: id 重複")
        seen.add(sid)

        if s.get("category") not in cat_ids:
            errors.append(f"{where}: category `{s.get('category')}` 不在 data/categories.json")
        if s.get("area") not in area_ids:
            errors.append(f"{where}: area `{s.get('area')}` 不在 data/areas.json")

        for k in ("lat", "lng"):
            v = s.get(k)
            lo, hi = BBOX[k]
            if not isinstance(v, (int, float)) or not lo <= v <= hi:
                errors.append(f"{where}: {k}={v} 不在中大周邊範圍 {lo}~{hi}，請回 raw 筆記確認")

        h = s.get("hours")
        if h is not None:
            if set(h) != set(DAYS):
                errors.append(f"{where}: hours 必須剛好包含 {DAYS}（公休寫 []）")
            for d, ranges in h.items():
                for r in ranges or []:
                    if not RANGE_RE.match(r):
                        errors.append(f"{where}: hours.{d} 的 `{r}` 格式應為 HH:MM-HH:MM")
                    elif r[:5] >= r[6:]:
                        errors.append(f"{where}: hours.{d} 的 `{r}` 結束時間要晚於開始（跨夜請拆成兩天）")

        ref = s.get("web_ref")
        if ref is not None:
            if not isinstance(ref, dict) or not str(ref.get("url", "")).startswith("https://") or not ref.get("label"):
                errors.append(f"{where}: web_ref 必須是 {{\"label\": ..., \"url\": \"https://...\"}} 或 null")
            else:
                raw = ROOT / (s.get("source") or "")
                if raw.is_file() and ref["url"] not in raw.read_text(encoding="utf-8"):
                    errors.append(f"{where}: web_ref 的網址沒有記錄在 raw 筆記裡（網路資料必須留下來源）")

        src = s.get("source") or ""
        if src and not (ROOT / src).is_file():
            errors.append(f"{where}: source `{src}` 檔案不存在 — 每間店都必須有 raw 筆記")
        if s.get("verified") and not DATE_RE.match(s["verified"]):
            errors.append(f"{where}: verified 格式應為 YYYY-MM-DD")
    return errors


# ---------------------------------------------------------------- 格式化 shops.json
def dump_shops(shops):
    """固定欄位順序、hours 一天一行，讓 git diff 好讀。"""
    out = ["["]
    for i, s in enumerate(shops):
        lines = []
        for k in FIELD_ORDER:
            if k not in s:
                continue
            v = s[k]
            if k == "hours" and isinstance(v, dict):
                inner = ",\n".join(f'      "{d}": {json.dumps(v.get(d, []), ensure_ascii=False)}' for d in DAYS)
                lines.append(f'    "hours": {{\n{inner}\n    }}')
            else:
                lines.append(f'    "{k}": {json.dumps(v, ensure_ascii=False)}')
        out.append("  {\n" + ",\n".join(lines) + "\n  }" + ("," if i < len(shops) - 1 else ""))
    out.append("]")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- 產生頁面
def esc(x):
    return html.escape(str(x), quote=True)


def display_ranges(h, d):
    """與 common.js 的 displayRanges 相同：跨夜時段顯示成 19:00–01:30。"""
    i = DAYS.index(d)
    prev, nxt = h.get(DAYS[i - 1]) or [], h.get(DAYS[(i + 1) % 7]) or []
    prev_late = any(r.endswith("-24:00") for r in prev)
    out = []
    for r in h.get(d) or []:
        if r.startswith("00:00-") and prev_late:
            continue
        cont = next((x for x in nxt if x.startswith("00:00-")), None) if r.endswith("-24:00") else None
        out.append(r[:5] + "–" + cont[6:] if cont else r.replace("-", "–"))
    return out


def hours_rows(h):
    if not h:
        return '<tr><td colspan="2" class="pending">營業時間待確認</td></tr>'
    rows = []
    for d in DAYS:
        r = display_ranges(h, d)
        txt = "、".join(r) if r else "公休"
        cls = "" if r else ' class="closed"'
        rows.append(f'<tr data-day="{d}"><th>週{DAY_LABEL[d]}</th><td{cls}>{esc(txt)}</td></tr>')
    return "\n          ".join(rows)


def section(title, body):
    return f'<section class="block">\n        <h2>{title}</h2>\n        {body}\n      </section>'


def optional_sections(s):
    parts = []
    if s.get("items"):
        lis = "".join(
            f'<li><span>{esc(it["name"])}</span><span class="dots"></span>'
            f'<span>{esc(str(it["price"]) + " 元") if it.get("price") is not None else "—"}</span></li>'
            for it in s["items"])
        parts.append(section("吃過的品項", f'<ul class="menu">{lis}</ul>'))
    if s.get("review"):
        parts.append(section("評價", f'<p class="review">{esc(s["review"])}</p>'))
    if s.get("notes"):
        parts.append(section("備註", '<ul class="notes">' + "".join(f"<li>{esc(n)}</li>" for n in s["notes"]) + "</ul>"))
    return "\n      ".join(parts)


def provenance(s):
    ref = s.get("web_ref")
    base = f'資料確認日期 {esc(s["verified"])}・<a href="../{esc(s["source"])}">原始筆記</a>'
    if ref:
        base += f'・營業時間等資訊查自 <a href="{esc(ref["url"])}" target="_blank" rel="noopener">{esc(ref["label"])}</a>'
    return base


def render(s, tpl, cats, areas):
    c = cats[s["category"]]
    rec = s.get("recommend") or []
    rec_html = ("".join(f"<li>{esc(r)}</li>" for r in rec)) if rec else '<li class="pending">還沒有推薦</li>'
    page_data = json.dumps({"id": s["id"], "name": s["name"], "lat": s["lat"], "lng": s["lng"],
                            "hours": s.get("hours"), "color": c["color"]},
                           ensure_ascii=False).replace("</", "<\\/")
    values = {
        "NAME": esc(s["name"]),
        "CATEGORY_ID": esc(s["category"]),
        "CATEGORY": esc(c["label"]),
        "COLOR": esc(c["color"]),
        "AREA": esc(areas[s["area"]]["label"]),
        "RECOMMEND": rec_html,
        "HOURS_ROWS": hours_rows(s.get("hours")),
        "OPTIONAL_SECTIONS": optional_sections(s),
        "ADDRESS": esc(s.get("address") or ""),  # 沒有地址就留空，CSS 會隱藏整行
        "GMAP_URL": esc((s.get("web_ref") or {}).get("url") if "google.com/maps" in (s.get("web_ref") or {}).get("url", "")
                        else f"https://www.google.com/maps/search/?api=1&query={s['lat']},{s['lng']}"),
        "PROVENANCE": provenance(s),
        "GMAP_DIR_URL": esc(f"https://www.google.com/maps/dir/?api=1&destination={s['lat']},{s['lng']}"),
        "SOURCE": esc(s["source"]),
        "VERIFIED": esc(s["verified"]),
        "PAGE_DATA": page_data,
    }
    out = tpl
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{\w+\}\}", out)
    if left:
        raise SystemExit(f"模板中有未替換的變數：{left}")
    return out


def main():
    check_only = "--check" in sys.argv
    categories, areas, shops = load("categories.json"), load("areas.json"), load("shops.json")

    errors = validate(shops, categories, areas)
    if errors:
        print("✗ 資料檢查失敗：")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"✓ 資料檢查通過：{len(shops)} 間店")
    if check_only:
        return

    (DATA / "shops.json").write_text(dump_shops(shops), encoding="utf-8")

    tpl = TEMPLATE.read_text(encoding="utf-8")
    cats = {c["id"]: c for c in categories}
    area_map = {a["id"]: a for a in areas}
    SHOPS_DIR.mkdir(exist_ok=True)
    wanted = set()
    for s in shops:
        path = SHOPS_DIR / f"{s['id']}.html"
        path.write_text(render(s, tpl, cats, area_map), encoding="utf-8")
        wanted.add(path.name)
    for old in SHOPS_DIR.glob("*.html"):
        if old.name not in wanted:
            old.unlink()
            print(f"  已移除不在資料中的頁面：shops/{old.name}")
    print(f"✓ 已產生 {len(wanted)} 個店家頁面於 shops/")


if __name__ == "__main__":
    main()
