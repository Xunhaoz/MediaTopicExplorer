"""PR TIMES（prtimes.jp）新聞稿關鍵字搜尋。

使用網站「もっと見る」按鈕呼叫的 /api/search_release.php（非官方、免金鑰）。

  prtimes.py search 紅葉 イルミネーション --since 2026-10-04
  prtimes.py search ちいかわ --max-pages 3 --text
"""
import html
import re
import time

from skillkit import (Http, Item, JST, SkillError, add_command, add_max_pages, add_since_until, in_range,
                      new_parser, run, since_utc, to_utc)

API = "https://prtimes.jp/api/search_release.php"
BASE = "https://prtimes.jp"
PAGE_SIZE = 50  # 超過約 60 筆時，伺服器每頁要 20 秒以上；50 筆通常較快，但仍常有慢頁
http = Http(delay=1, concurrency=4, timeout=60)  # 不同關鍵字平行查，同一關鍵字依序翻頁


class Release(Item):
    company: str
    keywords: list[str]


def plain_text(raw):
    text = re.sub(r"<(br|/p|/div|/li|/h\d)[^>]*>", "\n", raw or "")
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def fetch_page(keyword, page):
    params = {"type": "search", "v": keyword, "page": page, "limit": PAGE_SIZE,
              "sub": "", "lv2": "", "locate": "", "random": int(time.time() * 1000)}
    data = http.get(API, params=params).json()
    if "articles" not in data:
        raise SkillError(f"API 回應沒有 articles 欄位；格式可能改了（{keyword}）")
    return data["articles"] or []


def search_keyword(keyword, args):
    """由新到舊翻頁；遇到比 --since 舊的就停止。回傳 [(id, 新聞稿)]。"""
    lo, out = since_utc(args), []
    for page in range(1, args.max_pages + 1):
        articles = fetch_page(keyword, page)
        for a in articles:
            published = to_utc(a["updated_at"]["origin"], assume=JST)
            if not in_range(published, args):
                continue
            r = {"id": a["url"].rsplit("/", 1)[-1].removesuffix(".html"), "url": BASE + a["url"],
                 "title": a["title"], "company": a["provider"]["name"], "published_at": published}
            if args.text:
                r["text"] = plain_text(a.get("text"))
            out.append(r)
        if len(articles) < PAGE_SIZE or (lo and to_utc(articles[-1]["updated_at"]["origin"], assume=JST) < lo):
            break
    return out


def cmd_search(args):
    keywords = list(dict.fromkeys(args.keywords))
    merged = {}
    for kw, rows in zip(keywords, http.map(lambda kw: search_keyword(kw, args), keywords)):
        for r in rows:
            merged.setdefault(r["id"], {**r, "keywords": []})["keywords"].append(kw)
    return sorted((Release(**r) for r in merged.values()), key=lambda r: r.published_at, reverse=True)


def main():
    ap, sub = new_parser(__doc__)
    p = add_command(sub, "search", "關鍵字搜尋新聞稿（比對標題和內文）", cmd_search)
    p.add_argument("keywords", nargs="+", help="日文關鍵字，可多個")
    add_since_until(p)
    add_max_pages(p, 10, f"每個關鍵字的頁數上限，每頁 {PAGE_SIZE} 則")
    p.add_argument("--text", action="store_true", help="附上新聞稿全文（純文字）")
    run("prtimes", ap)


if __name__ == "__main__":
    main()
