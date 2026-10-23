---
name: brave
description: 透過官方 Brave Search API 搜尋整個網路，提供兩個獨立指令：網頁搜尋（web）和新聞搜尋（news），可限定國家、語言和發布時間。需要一般網頁或新聞的搜尋結果（標題、網址、摘要、發布時間、網站）時使用，例如查景點最新資訊、找某主題的報導或官方網站。Google 官方網頁搜尋 API 已停止開放，要「Google 一下」時也用這個。
---

# Brave Search API

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/brave.py <指令> ...
```

- 輸出是一個 JSON：`{"source", "command", "fetched_at", "params", "items", "errors"}`，印到 stdout；進度印到 stderr。整個指令失敗時（例如額度用完、憑證錯誤）退出碼為 1。
- 日期參數 `YYYY-MM-DD` 一律是台灣時間，`--since`／`--until` 都包含當天。輸出的 `*_at` 是 UTC（`...Z`）。
- 憑證用環境變數 `BRAVE_API_KEY`。沒有時不帶憑證送出，由雲端環境的 network secret 補上（回 401／422 代表 secret 沒設好）。
- 請求間隔 1 秒（免費方案每秒 1 次），翻頁是依序進行。

## web：網頁搜尋

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/brave.py web "京都 紅葉 見頃 2026" --max 40 --country JP --lang jp --since 2026-10-01
```

## news：新聞搜尋

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/brave.py news "日本 免稅 新制" --max 50 --freshness pm
```

兩個指令的參數相同：

| 參數 | 預設 | 說明 |
|---|---|---|
| `query` | | 關鍵字；可用 `site:`、`-排除`、`"完整詞組"` 等搜尋運算子 |
| `--max` | web 20、news 50 | 筆數上限；web 每 20 筆、news 每 50 筆一頁，最多 10 頁 |
| `--country` | 由 API 決定 | 2 碼國家代碼，例如 `TW`、`JP` |
| `--lang` | 不限 | `search_lang`，內容語言，例如 `zh-hant`、`jp`、`en` |
| `--freshness` | 不限 | `pd`、`pw`、`pm`、`py`：過去 1 天、7 天、31 天、1 年 |
| `--since` / `--until` | | 發布時間範圍；不能和 `--freshness` 一起用 |
| `--safesearch` | API 預設 | `off`、`moderate`、`strict` |
| `--snippets` | 關 | 每筆多回傳最多 5 段摘錄，放在 `snippets` |

web 的輸出：

```json
{"id", "url", "title", "description", "published_at", "site", "site_name", "snippets"}
```

news 的輸出多兩個欄位：

```json
{..., "breaking", "thumbnail_url"}
```

- `id` 就是網址；結果以網址去重。
- `published_at` 來自 Brave 的 `page_age`，原始值沒有時區，視為 UTC；沒有時是 `null`。
- 用 `--since`／`--until` 時，沒有 `published_at` 的結果無法判斷，會保留。
- `site` 是網域（例如 `www.japan-guide.com`）；`site_name` 是 Brave 判斷的網站名稱，可能是 `null`。
- `description` 可能含 `<strong>` 等 HTML 標籤，是關鍵字的標示。
- 結果是 Brave 排序後的樣本，不是完整清單；最多翻到第 10 頁。

## 額度

依 Brave 帳號方案而定，在 [API dashboard](https://api-dashboard.search.brave.com/) 查用量。每翻一頁算 1 次請求；額度用完時指令會以 429 錯誤結束。
