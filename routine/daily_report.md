# 每日旅遊話題洞察報告：routine 執行說明

給 Claude routine 讀的任務說明。routine 的 prompt 只要寫「依照 routine/daily_report.md 執行」。

## 基本設定

- 服務對象：台灣旅遊社群 @chictrip.tw 的創作者。受眾是台灣自由行旅客，主力日本、韓國，也有泰國、越南、港澳、歐洲、台灣國旅。
- 日期一律用台灣時間（`TZ=Asia/Taipei date +%F`）。以下 `TODAY` 是今天，「下週」是今天之後的下一個週一到週日，「下月」是下一個日曆月。
- 研究過程的原始資料放在 `tmp/TODAY/`（已在 .gitignore，不 commit）。
- 只 commit `reports/travel_topics_TODAY.html` 和 `index.html`，直接 push 到 `main`，不要開 `claude/` 分支或 PR。
- 不要修改 `.claude/skills/`、`scripts/`、`.github/`、`routine/`。

## 資料來源（skills）

都在 `.claude/skills/`，用法看各自的 SKILL.md。在專案根目錄執行 `uv run --project .claude/skills .claude/skills/<name>/scripts/<name>.py ...`（YouTube 是 `youtube/scripts/yt.py`）。

- YouTube 不需要在環境裡找金鑰。雲端環境的 network secret 會自動補上，直接呼叫即可。如果回 403，就在報告頁尾註明「YouTube 資料缺漏」，其他部分照常完成。
- YouTube search 一次扣 100 配額，整個 routine 合計控制在 40 次以內。
- PTT 存在的旅遊看板：Japan_Travel、Korea_Travel、Travel、Thailand、Hong_Kong、EuropeTravel。

## 團隊分工

用 Agent 工具平行啟動三位研究員（背景執行），全部回報後再啟動圖文作家。每位研究員的 prompt 都要帶入：TODAY、下週和下月的具體日期、服務對象、輸出路徑，以及以下規則：只用真實抓到的資料，不要捏造數字；查不到就標「待確認」；每個話題附 1–3 個來源網址，盡量附一張真實圖片網址（來源頁的 og:image，YouTube 用 `https://i.ytimg.com/vi/<id>/hqdefault.jpg`）。

每位研究員都要找四類話題：
- 熱門：當下廣泛討論的景點、玩法、購物、文化、特殊體驗。
- 趨勢：近兩週和前兩週相比，討論量正在上升的主題。
- 週期：去年同期、上個月同期、上次同一個假日大家在討論什麼。
- 候選熱門（重點）：還沒熱門，但很可能爆紅。

每則話題都要寫：類別、適用時段、一句洞察、量化證據、來源。

1. **社群資料分析師**（PTT＋YouTube）→ `tmp/TODAY/analyst_social.md`
   - 量化指標：推文數、文章數、觀看數、成長倍數。
   - 週期話題用 PTT search 查去年同期的文章。
2. **內容分析師**（步步日本、MATCHA、Funliday、PR TIMES）→ `tmp/TODAY/analyst_media.md`
   - 用步步日本 popular 的 last7days 與 last30days 比較趨勢。
   - 從 PR TIMES 找下週到下月開幕、開始的新設施、活動、限定商品，再用 bubujp posts --search 確認台灣媒體是否已經報導。
3. **行銷企劃**（WebSearch／WebFetch）→ `tmp/TODAY/planner_web.md`
   - 檔期行事曆：台灣連假、購物節、日韓泰的節日與季節活動、旅展、航空促銷。
   - 新航線、入境與免稅新制、匯率。
   - 候選話題要附公布日期。
4. **圖文作家**（三份研究完成後）→ `reports/travel_topics_TODAY.html`
   - 把三份研究整合成一個 HTML 檔，跨檔案重複的話題合併成一張卡。不加入研究檔裡沒有的事實。
   - **版面與 CSS 完全沿用 `reports/` 裡最新一份報告**：區塊順序、卡片樣式、深色模式、手機寬度單欄都照舊。區塊順序是：這週先做 → 檔期行事曆 → ⭐候選熱門 → 熱門 → 趨勢 → 週期 → 方法與限制。
   - 候選熱門每則要有：爆紅可能性（高／中高／中）、為何會紅、建議切角、最佳發文時間。
   - 跟前一份報告比較，在新出現或明顯升溫的話題上標「NEW」或「↑」。
   - `<head>` 必須有 `<title>旅遊話題洞察 TODAY</title>` 和 `<meta name="description" content="一句話總結今天最重要的 2–3 個題目">`，首頁列表會用到這兩個欄位。
   - 圖片外連，加上 `loading="lazy" referrerpolicy="no-referrer"`，並設 onerror 讓失效的圖片變成色塊佔位。
   - 完成後用 curl 檢查圖片網址，失效的就換掉或移除。

## 收尾

1. `python3 scripts/build_index.py`
2. 確認 `git status` 只有 `reports/travel_topics_TODAY.html` 和 `index.html` 有變更，而且沒有任何憑證或 `tmp/` 檔案。
3. `git add reports/travel_topics_TODAY.html index.html`，commit 訊息寫 `report: TODAY`，push 到 `main`。
4. 最後回覆五行內的摘要：今天的前三名題目、各區塊的話題數、缺漏的資料來源。
