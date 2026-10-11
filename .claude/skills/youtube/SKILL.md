---
name: youtube
description: 透過官方 YouTube Data API v3 讀取公開資料，提供五個獨立指令：關鍵字搜尋影片（search）、查影片統計（stats）、查頻道資訊（channels）、列頻道上傳清單（uploads）、抓影片頂層留言（comments）。需要 YouTube 影片、頻道或留言的原始資料時使用。
---

# YouTube Data API

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/yt.py <指令> ...
```

- 輸出是一個 JSON：`{"source", "command", "fetched_at", "params", "items", "errors"}`，印到 stdout；進度印到 stderr。整個指令失敗時（例如配額用完、憑證錯誤）退出碼為 1。
- 日期參數 `YYYY-MM-DD` 一律是台灣時間，`--since`／`--until` 都包含當天。輸出的 `*_at` 是 UTC（`...Z`）。
- 憑證依序找：環境變數 `YOUTUBE_API_KEY` → 環境變數 `YOUTUBE_CREDENTIALS`（服務帳戶 JSON 路徑）→ 專案根目錄的 `youtube-service-account.json`。都沒有時不帶憑證送出，由雲端環境的 network secret 補上（回 403 代表 secret 沒設好）。
- 影片 ID 的地方都可以給網址（`watch?v=`、`youtu.be/`、`/shorts/`、`/live/`）。

## search：關鍵字搜尋影片

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/yt.py search "京都 紅葉" --max 50 --order viewCount --since 2026-09-11
```

| 參數 | 預設 | 說明 |
|---|---|---|
| `query` | | 關鍵字 |
| `--max` | 50 | 筆數上限，每 50 筆一頁 |
| `--order` | relevance | `relevance`、`date`、`viewCount`、`rating` |
| `--since` / `--until` | | 發布時間範圍 |
| `--region` | 不限 | regionCode，例如 `TW` |
| `--lang` | 不限 | relevanceLanguage，例如 `zh-Hant` |
| `--duration` | any | `short`（<4 分）、`medium`（4–20 分）、`long`（>20 分） |
| `--channel` | | 只搜這個頻道 ID |

```json
{"id", "url", "title", "published_at", "description", "channel_id", "channel_title"}
```

- 不含觀看數等統計。
- 結果是 YouTube 排序後的樣本，不是完整清單。
- `regionCode` 的意思是「在該地區可以觀看」。

## stats：影片統計

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/yt.py stats 7ohLKmys6hg https://youtu.be/SjgFmqEyucU
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/yt.py search "京都 紅葉" | uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/yt.py stats --from -
```

- `--from FILE` 讀前一個指令輸出的 `items[].id`（search、uploads 的輸出都能直接用），或每行一個 ID 的文字檔；`-` 代表 stdin。
- 重複的 ID 會去除，每 50 支一批。

```json
{"id", "url", "title", "published_at", "tags", "description", "channel_id", "channel_title",
 "duration_seconds", "live", "views", "likes", "comments", "category_id", "topic_categories"}
```

- `likes`、`comments` 是 `null` 代表創作者隱藏或關閉了，不是 0。
- `live` 是 `none`、`live` 或 `upcoming`。
- 查不到的影片（私人、已刪除、會員限定或不存在）列在 `errors`。
- API 沒有標示 Shorts 的欄位。
- 2026-08-24 起 viewCount 改計法：開始播放就算一次，包括自動播放和懸停預覽。

## channels：頻道資訊

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/yt.py channels @joeman UCmArFxfDybtCbo0Fa0Z2xxA
```

- 參數是 `@handle`、頻道網址或 `UC` 開頭的頻道 ID。中文名稱無法解析。

```json
{"id", "url", "title", "published_at", "description", "handle", "subscribers", "video_count",
 "view_count", "uploads_playlist_id"}
```

- `subscribers` 是 `null` 代表頻道隱藏了訂閱數。
- 解析失敗的頻道列在 `errors`，其他頻道照常處理。

## uploads：頻道上傳清單

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/yt.py uploads @joeman UCmArFxfDybtCbo0Fa0Z2xxA --max 30 --since 2026-09-11
```

| 參數 | 預設 | 說明 |
|---|---|---|
| `channels`（可多個） | | 同 `channels` |
| `--max` | 50 | 每個頻道的影片數上限 |
| `--since` / `--until` | | 發布時間範圍；遇到比 `--since` 舊的就停止翻頁 |

```json
{"id", "url", "title", "published_at", "channel_id", "channel_title"}
```

- 每個頻道由新到舊，包含 Shorts 和直播；不含私人和會員限定影片。
- 解析失敗的頻道列在 `errors`。

## comments：頂層留言

```bash
uv run --project ${CLAUDE_SKILL_DIR}/.. ${CLAUDE_SKILL_DIR}/scripts/yt.py comments 7ohLKmys6hg --max 200 --order relevance
```

| 參數 | 預設 | 說明 |
|---|---|---|
| `video_ids`（可多個） | | 影片 ID 或網址；也可以用 `--from` |
| `--max` | 100 | 每支影片的留言數上限，每 100 則一頁 |
| `--order` | relevance | `relevance`（熱門）或 `time`（最新） |

```json
{"id", "url", "text", "published_at", "video_id", "likes", "replies"}
```

- 只有頂層留言；`replies` 是回覆數，回覆內容不展開。
- 不輸出留言者名稱和頻道。
- 留言關閉或影片不存在時，該影片列在 `errors`（`commentsDisabled`、`videoNotFound`）。
- YouTube 開發者政策規定，API 取得的資料最多保存 30 天。

## 配額

每天配額在太平洋時間午夜重置（台灣時間 15:00 或 16:00）。

- 一般額度每天 10,000 units：`stats`、`channels`、`uploads`、`comments` 每次呼叫 1 unit。
- 搜尋有獨立額度，每天 100 次：`search` 每翻一頁用 1 次。
- 用完時指令會以 `quotaExceeded` 錯誤結束。
