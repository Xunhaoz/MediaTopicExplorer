---
name: bubujp
description: 讀取步步日本（www.bubu-jp.com，給台灣讀者的日本旅遊媒體）的公開資料，提供三個獨立指令：文章清單與站內搜尋（posts）、各時間區間的文章瀏覽數排行（popular）、分類與標籤清單（terms）。需要步步日本文章或瀏覽數原始資料時使用。
---

# 步步日本

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/bubujp.py <指令> ...
```

- 輸出是一個 JSON：`{"source", "command", "fetched_at", "params", "items", "errors"}`，印到 stdout；進度印到 stderr。整個指令失敗時退出碼為 1。
- 日期參數 `YYYY-MM-DD` 一律是台灣時間，`--since`／`--until` 都包含當天。輸出的 `*_at` 是 UTC（`...Z`）。
- 不需要金鑰或任何設定。

## posts：文章清單

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/bubujp.py posts --since 2026-10-01 --max 300
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/bubujp.py posts --search 紅葉 --max 20
```

| 參數 | 預設 | 說明 |
|---|---|---|
| `--max` | 100 | 篇數上限，每 100 篇一頁 |
| `--search` | | 站內搜尋關鍵字（WordPress 搜尋，比對標題和內文） |
| `--since` / `--until` | | 發布時間範圍 |
| `--category` / `--tag` | | 分類或標籤 ID，多個用逗號分隔；ID 用 `terms` 查 |

```json
{"id": "36015", "url": "https://www.bubu-jp.com/archives/36015", "title": "...",
 "published_at": "2026-10-07T05:32:17Z", "modified_at": "...Z",
 "category_ids": ["40"], "tag_ids": ["28", "2435"], "description": "..."}
```

- 由新到舊排列。全站大約 1,600 篇。
- `category_ids`、`tag_ids` 的名稱用 `terms` 查。
- `description` 是 WordPress 摘要（純文字），不是全文。

## popular：瀏覽數排行

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/bubujp.py popular --range last7days --max 500
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/bubujp.py popular --days 3 --max 50
```

| 參數 | 預設 | 說明 |
|---|---|---|
| `--range` | last7days | `last24hours`、`last7days`、`last30days`、`all`（累計） |
| `--days` | | 改用自訂區間：最近 N 天，會覆蓋 `--range` |
| `--max` | 100 | 篇數上限 |
| `--fresh` | 關 | 只列在統計區間內發布的文章 |
| `--category` | | 分類 ID，多個用逗號分隔；前面加 `-` 代表排除 |

```json
{"id", "url", "title", "published_at", "category_ids", "tag_ids", "pageviews"}
```

- 依 `pageviews` 由高到低排列。
- `pageviews` 是網站上 WordPress Popular Posts 外掛統計的頁面瀏覽數，包含所有流量來源（搜尋、社群、廣告、站外導流）。
- 只有一次快照，沒有歷史。

## terms：分類與標籤

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/bubujp.py terms categories
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/bubujp.py terms tags
```

```json
{"id": "2349", "name": "三重縣", "parent_id": "1862", "count": 6}
```

- `parent_id` 是上層分類 ID，`null` 代表頂層。
- 分類約 75 個，頂層是好玩、好吃、好買、好住、好推薦、優惠券、張維中、步步編輯台、地區、未分類；地區底下是日本各地區和縣市。
- 標籤約 2,200 個，全部抓完約 15 秒。

## 要知道的事

- 每次請求間隔至少 0.5 秒，依序翻頁。
- 只有日本旅遊內容，繁體中文。
- 資料來自網站公開的 WordPress API，不是正式對外服務，可能隨時改變或關閉。
