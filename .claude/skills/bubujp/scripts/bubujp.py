"""步步日本（www.bubu-jp.com）文章、瀏覽數排行與分類標籤。

網站是 WordPress，文章與分類取自公開 REST API（/wp-json/wp/v2/），
瀏覽數取自 WordPress Popular Posts 外掛的公開 API（/wp-json/wordpress-popular-posts/v1/）。

  bubujp.py posts --since 2026-10-01 --search 紅葉 --max 100
  bubujp.py popular --range last7days --max 500
  bubujp.py terms categories
"""
import html
import re
from datetime import timezone

from skillkit import Http, Item, add_command, add_max, add_since_until, new_parser, run, since_utc, to_utc, until_utc

BASE = "https://www.bubu-jp.com/wp-json"
http = Http(delay=0.5, timeout=60)


class Post(Item):
    category_ids: list[str]
    tag_ids: list[str]


class PopularPost(Item):
    category_ids: list[str]
    tag_ids: list[str]
    pageviews: int


class Term(Item):
    name: str
    parent_id: str | None
    count: int


def plain(rendered):
    return html.unescape(re.sub(r"<[^>]+>", "", rendered or "")).strip()


def gmt(s):
    return to_utc(s, assume=timezone.utc)  # WordPress 的 *_gmt 沒有時區標記，但就是 UTC


def ids(xs):
    return [str(x) for x in xs or []]


def paged(path, max_items, **params):
    """WordPress 標準分頁：per_page 最多 100，總頁數在 X-WP-TotalPages。"""
    rows, page, total = [], 1, 1
    while page <= total and len(rows) < max_items:
        resp = http.get(f"{BASE}{path}", params={"per_page": min(100, max_items - len(rows)), "page": page, **params})
        rows += resp.json()
        total = int(resp.headers.get("X-WP-TotalPages", 1))
        page += 1
    return rows[:max_items]


def wp_time(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def cmd_posts(args):
    rows = paged("/wp/v2/posts", args.max, search=args.search, after=wp_time(since_utc(args)),
                 before=wp_time(until_utc(args)), categories=args.category, tags=args.tag,
                 _fields="id,date_gmt,modified_gmt,link,title,excerpt,categories,tags")
    return [Post(id=str(p["id"]), url=p["link"], title=plain(p["title"]["rendered"]),
                 published_at=gmt(p["date_gmt"]), modified_at=gmt(p["modified_gmt"]),
                 category_ids=ids(p["categories"]), tag_ids=ids(p["tags"]),
                 description=plain(p["excerpt"]["rendered"])) for p in rows]


def cmd_popular(args):
    rng, extra = args.range, {}
    if args.days:
        rng, extra = "custom", {"time_unit": "day", "time_quantity": args.days}
    data = http.get(f"{BASE}/wordpress-popular-posts/v1/popular-posts", params={
        "range": rng, "limit": args.max, "freshness": 1 if args.fresh else None,
        "taxonomy": "category" if args.category else None, "term_id": args.category,
        "_fields": "id,date_gmt,link,title,categories,tags,pageviews", **extra}).json()
    return [PopularPost(id=str(p["id"]), url=p["link"], title=plain(p["title"]["rendered"]),
                        published_at=gmt(p.get("date_gmt")), category_ids=ids(p.get("categories")),
                        tag_ids=ids(p.get("tags")), pageviews=int(p["pageviews"])) for p in data]


def cmd_terms(args):
    rows = paged(f"/wp/v2/{args.kind}", 10_000, _fields="id,name,parent,count")
    return [Term(id=str(r["id"]), name=html.unescape(r["name"]),
                 parent_id=str(r["parent"]) if r.get("parent") else None, count=r["count"]) for r in rows]


def main():
    ap, sub = new_parser(__doc__)
    p = add_command(sub, "posts", "文章清單（/wp/v2/posts），由新到舊", cmd_posts)
    add_max(p, 100, "篇數上限，每 100 篇一頁")
    p.add_argument("--search", help="站內搜尋關鍵字（比對標題和內文）")
    add_since_until(p)
    p.add_argument("--category", help="分類 ID，多個用逗號分隔")
    p.add_argument("--tag", help="標籤 ID，多個用逗號分隔")

    p = add_command(sub, "popular", "瀏覽數排行（WordPress Popular Posts），依 pageviews 由高到低", cmd_popular)
    p.add_argument("--range", choices=["last24hours", "last7days", "last30days", "all"], default="last7days")
    p.add_argument("--days", type=int, help="改用自訂區間：最近 N 天（會覆蓋 --range）")
    add_max(p, 100, "篇數上限")
    p.add_argument("--fresh", action="store_true", help="只列在統計區間內發布的文章")
    p.add_argument("--category", help="分類 ID，多個用逗號分隔；前面加 - 代表排除")

    p = add_command(sub, "terms", "分類或標籤清單", cmd_terms)
    p.add_argument("kind", choices=["categories", "tags"])
    run("bubujp", ap)


if __name__ == "__main__":
    main()
