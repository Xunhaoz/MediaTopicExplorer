---
name: funliday
description: 讀取 Funliday 旅遊部落格（www.funliday.com/posts/）的文章資料，提供兩個獨立指令：列出 sitemap 裡的文章網址與最後修改時間（sitemap）、抓文章的標題、發布與修改時間、分類、摘要（meta）。需要 Funliday 文章原始資料時使用。
---

# Funliday 部落格

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/funliday.py <指令> ...
```

- 輸出是一個 JSON：`{"source", "command", "fetched_at", "params", "items", "errors"}`，印到 stdout；進度印到 stderr。整個指令失敗時退出碼為 1。
- 日期參數 `YYYY-MM-DD` 一律是台灣時間，`--since`／`--until` 都包含當天。輸出的 `*_at` 是 UTC（`...Z`）。
- 不需要金鑰或任何設定。

## sitemap：文章網址清單

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/funliday.py sitemap --since 2026-10-01
```

| 參數 | 說明 |
|---|---|
| `--since` / `--until` | **最後修改時間**範圍（sitemap 沒有發布時間） |

```json
{"id": "oy_toner", "url": "https://www.funliday.com/posts/oy_toner/", "modified_at": "2026-10-11T01:03:10Z"}
```

- 依 `modified_at` 由新到舊排列。全站大約 2,600 篇，一次約 2–5 秒。
- `id` 是網址最後一段 slug。
- 2026-09-21 全站約 640 篇的 `modified_at` 被批次更新；那天的值不代表內容真的被改過。

## meta：文章資訊

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/funliday.py meta https://www.funliday.com/posts/oy_toner/
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/funliday.py sitemap --since 2026-10-09 | uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/funliday.py meta --from -
```

- 參數是文章網址。`--from FILE` 讀前一個指令輸出的 `items[].url`，或每行一個網址的文字檔；`-` 代表 stdin。
- 重複的網址會去除。

```json
{"id": "oy_toner", "url": "...", "title": "...", "published_at": "2026-09-18T00:20:14Z",
 "modified_at": "2026-10-11T01:03:10Z", "categories": ["korea-tw-shopping", "korea-travel"], "description": "..."}
```

- `published_at`、`modified_at` 取自文章頁的 `article:published_time`、`article:modified_time`。
- `categories` 是 WordPress 分類 slug，取自文章本身的 `<article>` 標籤，不含頁面選單和相關文章的分類。
- `description` 是 `og:description`，不是全文。
- 404、逾時等失敗的網址會列在 `errors`，其他網址照常處理。

## 要知道的事

- 一篇一個請求，最多同時 4 個，請求開始間隔至少 0.5 秒，大約每秒 1–2 篇。
- 沒有公開的瀏覽數或互動數（網站的 `/analytics/pageview` 只收資料不回傳，不要去呼叫它）。
- REST API 要登入、RSS 關閉、列表頁由 JS 載入，所以只能用 sitemap 和文章頁 meta。
- 資料來自網頁結構，不是官方 API。結構改變時會報錯，不會默默回傳空結果。
