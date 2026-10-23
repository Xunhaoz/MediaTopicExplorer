"""Brave Search API 唯讀查詢。

授權：
  1. 環境變數 BRAVE_API_KEY
  2. 沒有：不帶憑證送出，交給雲端環境的 network secret 在 proxy 補上 X-Subscription-Token

  brave.py web "京都 紅葉 2026" --max 40 --country JP --lang jp --since 2026-10-01
  brave.py news "京都 紅葉" --max 50 --freshness pw
"""
import os
from datetime import date, timedelta, timezone

from skillkit import Http, Item, SkillError, add_command, add_max, add_since_until, in_range, new_parser, run, to_utc

BASE = "https://api.search.brave.com/res/v1/"
MAX_OFFSET = 9  # offset 是頁碼（0 起算），API 上限 9
http = Http(delay=1.0, concurrency=1)  # 免費方案每秒 1 次


# ---------- 輸出欄位 ----------

class Result(Item):
    site: str | None
    site_name: str | None
    snippets: list[str] | None = None


class NewsResult(Result):
    breaking: bool
    thumbnail_url: str | None


# ---------- API ----------

def api(endpoint, **params):
    key = os.environ.get("BRAVE_API_KEY")
    headers = {"Accept": "application/json", **({"X-Subscription-Token": key} if key else {})}
    resp = http.get(BASE + endpoint, params=params, headers=headers, check=False)
    if resp.is_error:
        try:
            err = resp.json().get("error", {})
        except ValueError:
            err = {}
        message = f"{resp.status_code} {err.get('code', '')}：{err.get('detail', resp.text[:200])}"
        if resp.status_code in (401, 403, 422) and not key:
            message += "（沒有設定 BRAVE_API_KEY，network secret 也沒有生效：請設定 BRAVE_API_KEY，"\
                       "或在雲端環境替 api.search.brave.com 加上 X-Subscription-Token 的 network secret）"
        raise SkillError(f"Brave API 錯誤 {message}")
    return resp.json()


def freshness(args):
    """--since／--until（台灣時間）轉成 Brave 的日期範圍；前後各放寬一天，精確範圍由 in_range 再篩。"""
    if args.freshness:
        if args.since or args.until:
            raise SkillError("--freshness 不能和 --since／--until 一起用")
        return args.freshness
    if not (args.since or args.until):
        return None
    lo = args.since - timedelta(days=1) if args.since else date(2000, 1, 1)
    hi = args.until + timedelta(days=1) if args.until else date.today() + timedelta(days=1)
    return f"{lo.isoformat()}to{hi.isoformat()}"


def search(endpoint, key, page_size, args):
    """翻頁直到 --max、沒有更多結果，或 offset 到上限；以網址去重。"""
    params = dict(q=args.query, country=args.country, search_lang=args.lang, safesearch=args.safesearch,
                  freshness=freshness(args), extra_snippets="true" if args.snippets else None)
    results, seen = [], set()
    count = min(page_size, args.max)  # offset 是頁碼，每頁筆數要固定
    for offset in range(MAX_OFFSET + 1):
        body = api(endpoint, count=count, offset=offset, **params)
        page = (body.get(key) or {}).get("results", []) if key else body.get("results", [])
        for r in page:
            if r.get("url") and r["url"] not in seen:
                seen.add(r["url"])
                results.append(r)
        more = body.get("query", {}).get("more_results_available")
        if len(results) >= args.max or not page or more is False:
            break
    return results


def common(r, args):
    # page_age 沒有時區（例如 2026-01-15T14:30:00），視為 UTC
    published = to_utc(r.get("page_age"), assume=timezone.utc)
    fields = dict(id=r["url"], url=r["url"], title=r.get("title", ""), description=r.get("description", ""),
                  published_at=published, site=(r.get("meta_url") or {}).get("hostname"),
                  site_name=(r.get("profile") or {}).get("name"))
    if args.snippets:
        fields["snippets"] = r.get("extra_snippets", [])
    return fields


def keep(item, args):
    """沒有發布時間的結果無法判斷，保留；有的才用 --since／--until 精確篩選。"""
    return item.published_at is None or not (args.since or args.until) or in_range(item.published_at, args)


# ---------- web ----------

def cmd_web(args):
    items = [Result(**common(r, args)) for r in search("web/search", "web", 20, args)]
    return [it for it in items if keep(it, args)][:args.max]


# ---------- news ----------

def cmd_news(args):
    items = [NewsResult(**common(r, args), breaking=bool(r.get("breaking")),
                        thumbnail_url=(r.get("thumbnail") or {}).get("src"))
             for r in search("news/search", None, 50, args)]
    return [it for it in items if keep(it, args)][:args.max]


# ---------- main ----------

def add_search_args(p, max_default, page_size):
    p.add_argument("query", help="關鍵字；可用 site:、-排除、\"完整詞組\" 等搜尋運算子")
    add_max(p, max_default, f"筆數上限，每 {page_size} 筆一頁、最多 10 頁")
    p.add_argument("--country", help="2 碼國家代碼，例如 TW、JP；不給就由 API 決定")
    p.add_argument("--lang", help="search_lang，內容語言，例如 zh-hant、jp、en；不給就不限")
    p.add_argument("--freshness", choices=["pd", "pw", "pm", "py"], help="過去 1 天／7 天／31 天／1 年")
    add_since_until(p)
    p.add_argument("--safesearch", choices=["off", "moderate", "strict"], help="不給就用 API 預設")
    p.add_argument("--snippets", action="store_true", help="每筆多回傳最多 5 段摘錄（snippets 欄位）")


def main():
    ap, sub = new_parser(__doc__)
    p = add_command(sub, "web", "網頁搜尋（web/search，每 20 筆 1 次請求）", cmd_web)
    add_search_args(p, 20, 20)
    p = add_command(sub, "news", "新聞搜尋（news/search，每 50 筆 1 次請求）", cmd_news)
    add_search_args(p, 50, 50)
    run("brave", ap)


if __name__ == "__main__":
    main()
