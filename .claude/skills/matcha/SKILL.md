---
name: matcha
description: 讀取 MATCHA 繁中版（matcha-jp.com/tw，給台灣讀者的日本旅遊媒體）的公開資料，提供五個獨立指令：新聞區列表（news）、一般文章 RSS（feed）、首頁各區塊列表（home）、每月文章 sitemap（sitemap）、文章內頁資訊（article）。需要 MATCHA 文章原始資料時使用。
---

# MATCHA 繁中版

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py <指令> ...
```

- 輸出是一個 JSON：`{"source", "command", "fetched_at", "params", "items", "errors"}`，印到 stdout；進度印到 stderr。整個指令失敗時退出碼為 1。
- 日期參數 `YYYY-MM-DD` 一律是台灣時間，`--since`／`--until` 都包含當天。輸出的 `*_at` 是 UTC（`...Z`），`*_date` 是 `YYYY-MM-DD`。
- 不需要金鑰或任何設定。
- 網站只寫日本。

## news：新聞區列表

「本月在地第一手情報」（`/tw/news`），全部是編輯部撰寫的短新聞。

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py news --max-pages 3
```

| 參數 | 預設 | 說明 |
|---|---|---|
| `--max-pages` | 1 | 頁數上限，每頁 12 篇 |

```json
{"id": "27745", "url": "https://matcha-jp.com/tw/27745", "title": "...", "author": null,
 "published_date": "2026-10-09", "places": []}
```

- 由新到舊排列。
- `published_date` 是列表上顯示的日期，沒有時間。
- 新聞區的文章不在 RSS 裡。

## feed：一般文章 RSS

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py feed
```

```json
{"id", "url", "title", "published_at", "categories", "description"}
```

- 固定是最新 30 篇，沒有參數。
- `description` 是開頭的摘要，以「...」結尾。
- `url` 都是 matcha-jp.com；要知道是不是 Locally 文章，請用 `article` 查。

## home：首頁各區塊列表

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py home
```

```json
{"id", "url", "title", "author", "published_date", "places", "section": "熱門文章", "rank": 1}
```

- 三個區塊：`熱門文章`、`MATCHA編輯部推薦` 各 6 篇；`本月在地第一手情報` 約 5 篇。
- `rank` 是在區塊裡的排列順序；網站沒有說明怎麼排序。
- 只是抓取當下的快照，網站沒有提供歷史資料，也沒有觀看數。

## sitemap：每月文章 sitemap

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py sitemap 2026-09 2026-10
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py sitemap --since 2025-01-01
```

| 參數 | 說明 |
|---|---|
| `months`（可多個） | YYYY-MM |
| `--since` / `--until` | 挑選 sitemap 月份檔：列出索引中落在這段日期所屬月份的檔案（不是逐篇過濾） |

```json
{"id", "url", "title", "modified_date": "2026-09-29", "sitemap_month": "2026-09", "geo": "沖繩縣, 日本"}
```

- `modified_date` 是 sitemap 的 `lastmod`，代表**更新日**，不是發布日。
- `title` 取自 sitemap 圖片說明欄位，內容和文章標題相同。
- 不存在的月份回傳空清單。

## article：文章內頁資訊

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py article 27745 https://matcha-jp.com/tw/27744
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py feed | uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/matcha.py article --from -
```

- 參數是文章 ID 或 `matcha-jp.com/tw/<ID>` 網址。`--from FILE` 讀前一個指令輸出的 `items[].id`；`-` 代表 stdin。
- 每篇一次請求，最多同時 3 個，請求開始間隔至少 1 秒。

```json
{"id", "url", "final_url", "locally": true, "title", "published_at", "modified_at",
 "keywords", "description", "lead"}
```

- `locally` 為 `true` 代表網址會轉到 `locally.matcha-jp.com`，也就是「Locally by MATCHA」文章，由地方業者或自治體撰寫的贊助內容。
- 頁面上的「本服務包含贊助廣告」是全站共用的聲明，每一頁都有。
- `keywords` 是 meta keywords，編輯部文章大多是空的。
- `lead` 是內文第一段。
- 讀取失敗的文章列在 `errors`，其他文章照常處理。

## 要知道的事

- 資料來自公開網頁和 RSS，沒有官方 API。網頁結構改變時會報錯，不會默默回傳空結果。
- robots.txt 只禁止 `/search` 和 `/preview`，這個技能不會碰這兩個路徑。
