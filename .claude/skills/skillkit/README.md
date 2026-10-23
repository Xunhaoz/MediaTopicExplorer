# skillkit

`.claude/skills/` 底下各資料來源 skill 的共用套件。規範寫成程式碼，新 skill 只要用這個套件，就自動符合規範。

## 環境

`.claude/skills/` 是一個 uv 專案（`pyproject.toml` + `uv.lock`），所有 skill 共用同一個環境：

```bash
uv run --project .claude/skills .claude/skills/<skill>/scripts/<skill>.py <指令> ...
```

腳本開頭**不要**寫 PEP 723 依賴宣告；有宣告的話，uv 會改用宣告建立的獨立環境，`import skillkit` 會失敗。
新增依賴：`uv add --project .claude/skills <套件>`。

## 規範

| 項目 | 規則 | 由誰負責 |
|---|---|---|
| 輸出 | stdout 一個 JSON：`{"source", "command", "fetched_at", "params", "items", "errors"}` | `cli.run` |
| 部分失敗 | 成功的照常放 `items`；失敗的放 `errors: [{"input", "error"}]`，退出碼仍是 0 | 指令函式回傳 `(items, errors)` |
| 整體失敗 | 訊息印到 stderr，退出碼 1 | 丟 `SkillError`；httpx 錯誤由 `run` 攔截 |
| 日期參數 | `YYYY-MM-DD`，一律台灣時間；`--since`／`--until` 都包含當天 | `cli.add_since_until`、`since_utc`、`until_utc`、`in_range` |
| 時間輸出 | 完整時間 `*_at`，UTC，`2026-10-11T07:18:19Z`；只有日期 `*_date`，`YYYY-MM-DD` | `schema.UtcDatetime`、`timeutil.to_utc` |
| 欄位名稱 | 共用欄位定義在 `schema.Item`；子類別只能新增欄位，`extra="forbid"` 讓拼錯直接報錯 | `schema.Item` |
| `id` | 一律字串；指向其他東西的 ID 用 `<東西>_id` | `schema.Item` |
| 參數名稱 | `--max` 筆數、`--max-pages` 頁數、`--since`／`--until` 日期、`--from` 讀前一個指令的輸出 | `cli.add_*` |
| HTTP | 每個來源一個 `Http(delay, concurrency)`：逾時、重試（連線錯誤、429、5xx）、請求間隔、同時請求數上限 | `http.Http` |
| HTML 解析 | selectolax（lexbor）CSS selector，不用正規表示式解析 HTML | `htmlparse.parse_html` |
| 解析失敗 | 頁面有內容卻解析不到東西，丟錯，不要回傳空清單 | `cli.ensure_parsed` |

### `Item` 共用欄位

`id`、`url`、`title`、`author`、`published_at`、`published_date`、`modified_at`、`modified_date`、
`categories`、`tags`（名稱或 slug；放 ID 時用 `category_ids`、`tag_ids`）、`description`（來源提供的摘要）、`text`（全文）。

只輸出建構時有給的欄位；明確給 `None` 的會輸出成 `null`，代表「來源有這個欄位但值是空的或被隱藏」。

### 各來源的請求設定

| 來源 | delay（秒） | concurrency |
|---|---|---|
| youtube | 0 | 4 |
| prtimes | 1 | 4 |
| funliday | 0.5 | 4 |
| matcha | 1 | 3 |
| bubujp | 0.5 | 1 |
| ptt | 0.8 | 1 |
| brave | 1 | 1 |

`delay` 是相鄰兩次請求「開始」的最短間隔，跨執行緒共用，所以平行時每秒請求數仍不會超過 `1 / delay`。
