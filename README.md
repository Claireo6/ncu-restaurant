# 中大吃什麼 🍜

國立中央大學周邊美食地圖：後門、宵夜街一帶的店家，依時段分成**早午餐／午晚餐／點心**，即時顯示是否營業，並附地圖與 Google Maps 導航。

**網站**：https://<Claireo6>.github.io/ncu-eats/

## 這個專案的設計

這不只是一個網頁，而是一套**讓 AI 能照同一套規則持續新增內容**的系統。規則寫在 [`CLAUDE.md`](CLAUDE.md)。

```
raw/*.md（我寫的筆記）──AI 依 CLAUDE.md 整理──▶ data/shops.json ──build.py──▶ shops/*.html
                                                          └──────────▶ index.html（列表＋地圖）
```

- **raw/**：我親自寫的店家筆記，是唯一的事實來源
- **data/**：結構化資料；分類、區域也是資料，新增分類不用改程式
- **templates/ + scripts/build.py**：所有店家頁從同一個模板產生，格式永遠一致
- **build.py 會檢查資料**：座標超出中大周邊、營業時間格式錯誤、分類不存在、沒有對應筆記、網路資料沒留來源……都會被擋下，避免 AI 編造資料

## 新增一間店

1. 複製 `raw/_TEMPLATE.md` 填好（店名、位置、座標最重要；座標在 Google Maps 對店家按右鍵即可複製）
2. 對 AI 說：

   ```
   請讀 CLAUDE.md，把 raw/2026-11-20-xxx.md 新增到網站
   ```

3. AI 會依 CLAUDE.md 更新 `data/shops.json`、執行 `python3 scripts/build.py`、跑檢查清單
4. commit & push，GitHub Pages 會自動更新

**只知道店名也可以**：給 AI「店名＋位置＋推薦」，它會依 CLAUDE.md §7.2 到 Google 地圖查地址、座標和營業時間，並把來源網址記在 raw 筆記裡（推薦和評價仍然只由我決定）：

```
請讀 CLAUDE.md，這幾間店只有店名和推薦，幫我上網查好其他資料後新增：
店名：來客 / 位置：宵夜街 / 推薦：紅燒豬腱飯
```

其他常用指令見 CLAUDE.md §11。

## 延伸方向

| 想做的事 | 要改的地方 |
|---|---|
| 新增分類（例如「宵夜」） | `data/categories.json` 加一筆 |
| 新增區域（例如「前門」） | `data/areas.json` 加一筆 |
| 每間店加上照片、評分等新欄位 | 依 CLAUDE.md §6.5：文件 → build.py 欄位表 → 模板 |
| 換整體配色 | `assets/css/style.css` 的 `:root` 變數 |

## 本機預覽

```bash
python3 scripts/build.py        # 檢查資料並產生店家頁
python3 -m http.server          # 開 http://localhost:8000
```

（首頁用 `fetch` 讀取 JSON，直接雙擊 index.html 會無法載入資料。）

## 部署到 GitHub Pages

1. 在 GitHub 建立新的 public repository，名稱 `ncu-eats`
2. 上傳整個資料夾：

   ```bash
   git init
   git add .
   git commit -m "feat: 中大吃什麼 初版"
   git branch -M main
   git remote add origin https://github.com/<你的帳號>/ncu-eats.git
   git push -u origin main
   ```

3. Repo → **Settings → Pages** → Source 選 **Deploy from a branch**，Branch 選 `main` / `/ (root)` → Save
4. 約 1 分鐘後網站上線：`https://<你的帳號>.github.io/ncu-eats/`

## 技術

純 HTML／CSS／JavaScript，無框架、無打包。地圖使用 [Leaflet](https://leafletjs.com/) + [OpenStreetMap](https://www.openstreetmap.org/)，不需要任何 API key。建置腳本只用 Python 標準函式庫。
