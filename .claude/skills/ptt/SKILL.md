---
name: ptt
description: 讀取 PTT（www.ptt.cc 網頁版）看板的文章列表，提供兩個獨立指令：看板最新文章列表（list）、看板站內搜尋（search）。輸出標題、分類、作者、推文數、發文時間，不含內文與留言。需要 PTT 看板文章原始資料時使用。
---

# PTT

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/ptt.py <指令> ...
```

- 輸出是一個 JSON：`{"source", "command", "fetched_at", "params", "items", "errors"}`，印到 stdout；進度印到 stderr。整個指令失敗時退出碼為 1。
- 日期參數 `YYYY-MM-DD` 一律是台灣時間，`--since`／`--until` 都包含當天。輸出的 `*_at` 是 UTC（`...Z`）。
- 不需要金鑰或登入（程式會帶 `over18` cookie）。
- 看板名稱用英文，大小寫要正確，例如 `Japan_Travel`、`Korea_Travel`。

## list：看板最新文章

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/ptt.py list Japan_Travel --since 2026-09-27
```

| 參數 | 預設 | 說明 |
|---|---|---|
| `board` | | 看板名稱 |
| `--since` / `--until` | | 發文時間範圍；翻到整頁都比 `--since` 舊就停 |
| `--max-pages` | 20 | 頁數上限。每頁約 20 篇，最新一頁通常不滿 |

由新到舊排列。

## search：看板站內搜尋

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/ptt.py search Japan_Travel esim --max-pages 3
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/ptt.py search Japan_Travel recommend:50
```

| 參數 | 預設 | 說明 |
|---|---|---|
| `board` | | 看板名稱 |
| `query` | | 關鍵字（比對標題），或 PTT 搜尋語法：`author:ID`、`recommend:N`（推文數 ≥ N）、`thread:標題`（同標題討論串） |
| `--max-pages` | 1 | 頁數上限，每頁約 20 篇，從最新開始；到最後一頁會自動停 |

由新到舊排列。可以搜到多年前的文章。

## items 欄位

```json
{"id": "M.1791703099.A.219", "url": "https://www.ptt.cc/bbs/Japan_Travel/M.1791703099.A.219.html",
 "title": "[問題] 福岡-下關交通問題", "author": "chenpei666", "published_at": "2026-10-11T07:18:19Z",
 "board": "Japan_Travel", "tag": "問題", "is_reply": false, "nrec": 0}
```

| 欄位 | 說明 |
|---|---|
| `id` | 文章檔名 |
| `title` | 完整標題，包含 `Re:` 和 `[分類]` |
| `author` | PTT 帳號 ID |
| `published_at` | 發文時間，取自文章檔名 `M.<unix 時間>`，精確到秒 |
| `tag` | 標題中括號裡的分類，例如 `問題`、`遊記`、`資訊`；沒有就是 `null` |
| `is_reply` | 標題開頭是 `Re:` 或 `Fw:` |
| `nrec` | 列表頁顯示的推文數，是推減噓的淨值。`爆`（100 以上）記為 100；`X1`–`X9`（噓比推多 10–90）記為 -10 到 -90；`XX` 記為 -100；空白記為 0 |

- 只有列表頁上看得到的資訊，不含內文、留言內容、瀏覽數。
- 置底公告和已刪除的文章不會列出。

## 要知道的事

- 每次請求間隔至少 0.8 秒，依序翻頁。
- 資料來自 PTT 網頁版的 HTML，不是 API。版面改變時會報錯，不會默默回傳空清單。
