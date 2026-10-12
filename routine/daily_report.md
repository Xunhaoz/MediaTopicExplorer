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
- YouTube search 一次扣 100 配額，**整個 routine（所有 subagent 合計）控制在 40 次以內**。配額分配見下方各研究員；用不完的不能轉讓，用完就改用 stats／uploads／comments（成本低很多）。
- PTT 存在的旅遊看板：Japan_Travel、Korea_Travel、Travel、Thailand、Hong_Kong、EuropeTravel。
- 無頭瀏覽器：雲端環境預裝 Chromium 與 Playwright（`PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`，不要執行 `playwright install`）。WebFetch／curl 打不開的官方頁（例如觀光庁、國稅庁、EC ETIAS），可用 Playwright 以 `executablePath: '/opt/pw-browsers/chromium'`、`args: ['--no-sandbox']` 開啟後讀取頁面文字。遇到反爬或驗證頁（如 Challenge Validation）就放棄並標「待確認」，不要用偽裝瀏覽器特徵或解驗證的方式繞過；可改用該網站公開提供的下載（如 CSV）或其他來源。
- 搜尋回傳 0 筆時，換關鍵字（去掉修飾詞、換繁簡／日文原名／英文）至少重試兩次，再判斷是真的沒有供給；不要直接當作「內容缺口」。

## 團隊分工

資料量不足是這個 routine 最常見的問題，所以採「三波」流程：**第一波廣度掃描 → 第二波深挖 → 第三波整合與寫作**。每一波都用 Agent 工具平行啟動（背景執行），該波全部回報後才進下一波。

每位 subagent 的 prompt 都要帶入：TODAY、下週和下月的具體日期、服務對象、輸出路徑、配額，以及以下共同規則：

- 只用真實抓到的資料，不要捏造數字；查不到就標「待確認」。
- 每個話題附 1–3 個來源網址，盡量附一張真實圖片網址（來源頁的 og:image，YouTube 用 `https://i.ytimg.com/vi/<id>/hqdefault.jpg`）。
- 每則話題都要寫：類別、適用時段、一句洞察、量化證據、來源。
- 每份研究檔要有「原始資料」小節，列出實際跑過的查詢（關鍵字、看板、日期區間）和回傳筆數，方便事後檢查覆蓋度。
- 每個話題旁邊註明資料等級：【量化】有數字證據、【單點】只有一則來源、【推測】分析師的判斷。
- 回報時最後附「我沒查到但值得追的線索」清單（至少 3 條），給第二波用。

四類話題的定義（所有研究員通用）：
- 熱門：當下廣泛討論的景點、玩法、購物、文化、特殊體驗。
- 趨勢：近兩週和前兩週相比，討論量正在上升的主題。
- 週期：去年同期、上個月同期、上次同一個假日大家在討論什麼。
- 候選熱門（重點）：還沒熱門，但很可能爆紅。

### 第一波：廣度掃描（6 位，平行）

每位至少要產出：熱門 5、趨勢 4、週期 4、候選 5 則（資料真的不夠時寫明原因，不要灌水湊數）。

1. **PTT 分析師** → `tmp/TODAY/w1_ptt.md`
   - 掃 Japan_Travel、Korea_Travel、Travel、Thailand、Hong_Kong、EuropeTravel 全部六個看板，每板 list 至少抓 3 頁。
   - 用 search 查去年同期（TODAY 前後各兩週）與上個月同期的關鍵字文章，至少 8 組關鍵字。
   - 指標：推文數、文章數、標題關鍵字出現次數（近兩週 vs 前兩週）。PTT 只有列表頁推文數，趨勢倍數是標題比對，要如實標註樣本大小。
2. **YouTube 分析師** → `tmp/TODAY/w1_youtube.md`
   - search 配額最多 14 次，涵蓋日本、韓國、泰國、越南、港澳、歐洲、台灣國旅，每個地區至少 1 次；其餘用 stats、channels、uploads 追蹤台灣旅遊頻道的最新上傳與觀看數。
   - 指標：觀看數、發布天數內的日均觀看、頻道訂閱規模對比（找出「小頻道爆量」的影片）。
   - 挑 3–5 支高觀看影片抓 comments，整理觀眾真正在問什麼（需求缺口）。
3. **日本媒體分析師** → `tmp/TODAY/w1_jp_media.md`
   - 步步日本 popular 的 last7days、last30days（以及可用的其他區間）比較，算 7 天／30 天比值找出加速的文章；MATCHA 的 news／feed／home 看台灣讀者近期在看什麼；Funliday sitemap 找近期更新與新文章。
4. **日本新聞稿分析師** → `tmp/TODAY/w1_prtimes.md`
   - PR TIMES 至少 10 組關鍵字（開幕、限定、期間限定、聯名、新幹線、樂園、溫泉、機場、咖啡、甜點、燈飾、祭典等），找下週到下月的新設施、活動、限定商品。
   - 對每一項用 bubujp posts --search 與 matcha 確認台灣媒體是否已報導，輸出「已報導／未報導」對照表（註明查過哪些媒體）。
5. **行銷企劃（檔期與制度）** → `tmp/TODAY/w1_calendar.md`
   - WebSearch／WebFetch：檔期行事曆（台灣連假與補假、購物節、日韓泰的節日與季節活動、紅葉／花季預測、旅展、航空促銷）、新航線、入境與免稅新制、匯率（附來源與時間）。
   - 候選話題要附公布日期；制度類資訊必須查官方或主流媒體，來源衝突時兩邊都寫並標「待確認」。
6. **行銷企劃（非日本市場與新聞）** → `tmp/TODAY/w1_nonjp.md`
   - WebSearch／WebFetch：韓國、泰國、越南、港澳、歐洲、台灣國旅各至少 4 則近兩週的話題（新景點、交通、簽證、事件、價格變動、安全提醒、天災）。
   - 這是補齊 PTT／日本媒體覆蓋不到的地區，每個地區都要有結果；真的查不到才寫「待確認」並說明查過什麼。

### 第二波：深挖（3–6 位，平行）

第一波全部回報後，由主 agent 讀完六份檔案，**自己整理出「值得深挖的題目清單」**，依下列標準挑 6–10 個題目，再分給 3–6 位深挖研究員（一位可負責 2 個相關題目）：

- 第一波裡多個來源都提到、但證據還薄的題目；
- 第一波「我沒查到但值得追的線索」；
- 候選熱門裡爆紅可能性高、但缺少切角或最佳時機的題目；
- 為了多樣性補位：確保最後涵蓋至少 4 個國家／地區、至少 4 種內容類型（交通、美食、住宿、購物、體驗、文化、制度、安全…）。

深挖研究員的任務：對自己的題目做交叉驗證與延伸——換不同關鍵字與來源再查、找去年同期的對照、抓留言或討論串看真實需求、找出台灣創作者尚未做過的切角、確認時間窗口。YouTube search 每位最多 3 次（全 routine 合計仍不得超過 40 次，第一波已用的要扣掉）。輸出到 `tmp/TODAY/w2_<題目簡稱>.md`，每個題目一節：
- 發現（含量化證據與來源）
- 為什麼現在值得做／時間窗口
- 建議切角（至少 2 個不同角度）與最佳發文時間
- 風險或待確認

第一波資料已經充足、沒有值得深挖的題目時，至少仍要啟動 3 位深挖研究員處理候選熱門前幾名。

### 第三波：整合與寫作

1. **總編輯**（1 位）→ `tmp/TODAY/editor_brief.md`
   - 讀完第一、二波所有檔案，輸出：①跨檔重複話題的合併清單（保留各來源的證據）；②「這週先做」前 5 名與排序理由；③候選熱門依爆紅可能性排序；④來源之間的衝突清單（標待確認）；⑤覆蓋度檢查：各國家／地區、各內容類型的話題數，缺口要寫出來。
   - 不加入研究檔裡沒有的事實。
2. **圖文作家**（1 位，總編輯完成後）→ `reports/travel_topics_TODAY.html`
   - 依 `editor_brief.md` 和各研究檔整合成一個 HTML 檔，跨檔案重複的話題合併成一張卡。不加入研究檔裡沒有的事實。
   - **版面與 CSS 完全沿用 `reports/` 裡最新一份報告**：區塊順序、卡片樣式、深色模式、手機寬度單欄都照舊。區塊順序是：這週先做 → 檔期行事曆 → ⭐候選熱門 → 熱門 → 趨勢 → 週期 → 方法與限制。
   - 候選熱門每則要有：爆紅可能性（高／中高／中）、為何會紅、建議切角、最佳發文時間。
   - 跟前一份報告比較，在新出現或明顯升溫的話題上標「NEW」或「↑」。
   - `<head>` 必須有 `<title>旅遊話題洞察 TODAY</title>` 和 `<meta name="description" content="一句話總結今天最重要的 2–3 個題目">`，首頁列表會用到這兩個欄位。
   - 「方法與限制」要如實列出：各來源實際查詢數量、查不到或回傳 0 筆的項目、地區覆蓋缺口、來源衝突。
   - 圖片外連，加上 `loading="lazy" referrerpolicy="no-referrer"`，並設 onerror 讓失效的圖片變成色塊佔位。
   - 完成後用 curl 檢查圖片網址，失效的就換掉或移除。

## 收尾

1. `python3 scripts/build_index.py`
2. 確認 `git status` 只有 `reports/travel_topics_TODAY.html` 和 `index.html` 有變更，而且沒有任何憑證或 `tmp/` 檔案。
3. `git add reports/travel_topics_TODAY.html index.html`，commit 訊息寫 `report: TODAY`，push 到 `main`。
4. 最後回覆五行內的摘要：今天的前三名題目、各區塊的話題數、缺漏的資料來源。
