---
name: prtimes
description: 用關鍵字搜尋 PR TIMES（prtimes.jp，日本新聞稿平台）的新聞稿，可限定發布日期，可附全文。需要日本企業、設施、活動的新聞稿原始資料時使用。
---

# PR TIMES 新聞稿搜尋

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/prtimes.py search 紅葉 イルミネーション --since 2026-10-04
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/prtimes.py search ちいかわ --max-pages 3 --text
```

- 輸出是一個 JSON：`{"source", "command", "fetched_at", "params", "items", "errors"}`，印到 stdout；進度印到 stderr。整個指令失敗時退出碼為 1。
- 日期參數 `YYYY-MM-DD` 一律是台灣時間，`--since`／`--until` 都包含當天。輸出的 `*_at` 是 UTC（`...Z`）。
- 不需要金鑰或任何設定。

## search

| 參數 | 預設 | 說明 |
|---|---|---|
| `keywords`（可多個） | | 日文關鍵字，會同時比對標題和內文 |
| `--since` / `--until` | | 發布時間範圍 |
| `--max-pages` | 10 | 每個關鍵字的頁數上限，每頁 50 則 |
| `--text` | 關 | 附上新聞稿全文（HTML 轉成純文字） |

```json
{"id": "000000011.000166935", "url": "https://prtimes.jp/main/html/rd/p/000000011.000166935.html",
 "title": "...", "published_at": "2026-10-11T06:08:30Z", "company": "株式会社...",
 "keywords": ["観光", "紅葉"], "text": "（有 --text 才會有）"}
```

- 由新到舊排列。多個關鍵字命中同一則時只出現一次，`keywords` 列出所有命中的字。
- `published_at` 取自 API 的 `updated_at.origin`（原始為日本時間），轉成 UTC。

## 要知道的事

- 資料來源是網站「もっと見る」按鈕呼叫的 `/api/search_release.php`，不是官方公開 API，格式可能隨時改變。
- 速度不穩定：每頁快的時候約 1 秒，但常有一頁要 10–20 秒。
- 多個關鍵字會平行查詢（最多同時 4 個，請求開始間隔至少 1 秒），同一個關鍵字的頁則依序翻。總耗時大約取決於頁數最多的那個關鍵字。
- 關鍵字也會比對內文，所以結果包含很多只是順帶提到的稿件。
- 沒有互動數（觀看、分享）；API 的分類欄位都是空的。
- 每頁 50 則的全文加起來很大，`--text` 搭配大量頁數時，輸出可能有數 MB。
- 內容幾乎都是在日本發布的稿件。
