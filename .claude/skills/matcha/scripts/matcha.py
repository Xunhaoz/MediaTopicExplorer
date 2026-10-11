"""MATCHA 繁中版（matcha-jp.com/tw）公開資料。

  matcha.py news --max-pages 3
  matcha.py feed
  matcha.py home
  matcha.py sitemap 2026-09 2026-10 | --since 2026-01-01
  matcha.py article 27745 https://matcha-jp.com/tw/27744 | --from FILE
"""
import json
import re
import xml.etree.ElementTree as ET

import feedparser
import httpx

from skillkit import (Http, Item, SkillError, add_command, add_from, add_max_pages, add_since_until, ensure_parsed,
                      new_parser, parse_html, refs, run, to_date, to_utc)

BASE = "https://matcha-jp.com/tw"
ARTICLE_ID_RE = re.compile(r"matcha-jp\.com/tw/(\d+)")
SM = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
IMG = "{http://www.google.com/schemas/sitemap-image/1.1}"
HOME_SECTIONS = ["熱門文章", "MATCHA編輯部推薦", "本月在地第一手情報"]
http = Http(delay=1, concurrency=3)


class Card(Item):
    places: list[str]


class HomeCard(Card):
    section: str
    rank: int


class SitemapEntry(Item):
    sitemap_month: str
    geo: str | None


class Article(Item):
    final_url: str
    locally: bool
    keywords: list[str]
    lead: str | None


def article_id(url):
    m = ARTICLE_ID_RE.search(url or "")
    return m.group(1) if m else None


def text(node):
    return re.sub(r"\s+", " ", node.text()).strip() if node else None


# ---------- 列表卡片（news、home 共用） ----------

def parse_card(li, cls=Card, **extra):
    link = li.css_first("a.article__title-link")
    url = link.attributes.get("href") if link else None
    return cls(
        id=article_id(url) or url,
        url=url,
        title=text(li.css_first("h3.article__title")),
        author=text(li.css_first(".article__author-name")),
        places=[text(p) for p in li.css(".meta-place")],
        published_date=to_date(text(li.css_first("p.article__meta"))),
        **extra,
    )


def cmd_news(args):
    out = []
    for page in range(1, args.max_pages + 1):
        html = http.get(f"{BASE}/news", params={"page": page}).text
        cards = [parse_card(li) for li in parse_html(html).css("li.c-article-item")]
        if page == 1:
            ensure_parsed(cards, html, "新聞卡片")
        if not cards:
            break
        out += cards
    return out


# ---------- feed ----------

def cmd_feed(args):
    feed = feedparser.parse(http.get(f"{BASE}/feed").content)
    if feed.bozo and not feed.entries:
        raise SkillError(f"RSS 解析失敗：{feed.bozo_exception}")
    return [Item(
        id=article_id(e.link) or e.link,
        url=e.link,
        title=e.title,
        published_at=to_utc(e.get("published")),
        categories=[t.term for t in e.get("tags", [])],
        description=e.get("summary"),
    ) for e in feed.entries]


# ---------- home ----------

def cmd_home(args):
    html = http.get(BASE).text
    out = []
    for h2 in parse_html(html).css("h2.c-content-section__title"):
        heading = text(h2)
        # 各區塊外層 class 不一定相同；h2 → 區塊標頭 → 區塊本體，卡片都在區塊本體裡
        body = h2.parent.parent if h2.parent else None
        if heading in HOME_SECTIONS and body:
            out += [parse_card(li, HomeCard, section=heading, rank=i + 1)
                    for i, li in enumerate(body.css("li.c-article-item"))]
    missing = [h for h in HOME_SECTIONS if not any(c.section == h for c in out)]
    if missing:
        raise SkillError(f"首頁找不到區塊或區塊沒有文章：{'、'.join(missing)}；網站結構可能改了")
    return out


# ---------- sitemap ----------

def available_months():
    root = ET.fromstring(http.get(f"{BASE}/sitemap.xml").content.lstrip())
    return sorted({m for loc in root.iter(f"{SM}loc") for m in re.findall(r"/tw/articles/(\d{4}-\d{2})\.xml", loc.text)})


def sitemap_month(month):
    try:
        root = ET.fromstring(http.get(f"{BASE}/articles/{month}.xml").content.lstrip())
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return []
        raise
    out = []
    for u in root.findall(f"{SM}url"):
        url = u.findtext(f"{SM}loc").strip()
        out.append(SitemapEntry(
            id=article_id(url) or url,
            url=url,
            title=(u.findtext(f"{IMG}image/{IMG}caption") or "").strip() or None,
            modified_date=to_date((u.findtext(f"{SM}lastmod") or "")[:10]),
            sitemap_month=month,
            geo=(u.findtext(f"{IMG}image/{IMG}geo_location") or "").strip() or None,
        ))
    return out


def cmd_sitemap(args):
    months = set(args.months)
    if args.since or args.until:
        lo = args.since.strftime("%Y-%m") if args.since else "0000-00"
        hi = args.until.strftime("%Y-%m") if args.until else "9999-99"
        months |= {m for m in available_months() if lo <= m <= hi}
    if not months:
        raise SkillError("請給月份（YYYY-MM），或用 --since／--until")
    return [e for m in sorted(months) for e in sitemap_month(m)]


# ---------- article ----------

def lead(tree):
    """內文第一段。Locally 文章用 ejs-paragraph；編輯部文章是 .article_content 裡的第一個 <p>。"""
    return text(tree.css_first("p.ejs-paragraph") or tree.css_first(".article_content p")) or None


def json_ld_dates(tree):
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(node.text())
        except json.JSONDecodeError:
            continue
        for d in data if isinstance(data, list) else [data]:
            if isinstance(d, dict) and d.get("datePublished"):
                return d.get("datePublished"), d.get("dateModified")
    return None, None


def article(ref):
    aid = ref if ref.isdigit() else article_id(ref)
    if not aid:
        return {"input": ref, "error": "看不懂的文章：請用文章 ID 或 matcha-jp.com/tw/<ID> 網址"}
    url = f"{BASE}/{aid}"
    try:
        resp = http.get(url)
    except httpx.HTTPStatusError as e:
        return {"input": ref, "error": f"HTTP {e.response.status_code}"}
    except httpx.TransportError as e:
        return {"input": ref, "error": f"連線錯誤 {type(e).__name__}"}
    tree = parse_html(resp.text)
    title = text(tree.css_first("h1"))
    if not title:
        return {"input": ref, "error": "找不到標題；網站結構可能改了"}
    def meta(name):
        node = tree.css_first(f'meta[name="{name}"]')
        return (node.attributes.get("content") or "") if node else ""

    published, modified = json_ld_dates(tree)
    final_url = str(resp.url)
    return Article(
        id=aid,
        url=url,
        final_url=final_url,
        locally="locally.matcha-jp.com" in final_url,
        title=title,
        published_at=to_utc(published),
        modified_at=to_utc(modified),
        keywords=[k.strip() for k in meta("keywords").split(",") if k.strip()],
        description=meta("description") or None,
        lead=lead(tree),
    )


def cmd_article(args):
    ids = refs(args, args.refs, "id")
    if not ids:
        raise SkillError("請給文章 ID 或網址，或用 --from 指定檔案")
    results = http.map(article, ids)
    return [r for r in results if isinstance(r, Item)], [r for r in results if isinstance(r, dict)]


def main():
    ap, sub = new_parser(__doc__)
    p = add_command(sub, "news", "「本月在地第一手情報」列表（/tw/news），由新到舊", cmd_news)
    add_max_pages(p, 1, "頁數上限，每頁 12 篇")

    add_command(sub, "feed", "一般文章 RSS（/tw/feed，最新 30 篇）", cmd_feed)
    add_command(sub, "home", "首頁「熱門文章」「MATCHA編輯部推薦」「本月在地第一手情報」三個區塊", cmd_home)

    p = add_command(sub, "sitemap", "每月文章 sitemap（/tw/articles/YYYY-MM.xml）", cmd_sitemap)
    p.add_argument("months", nargs="*", help="YYYY-MM，可多個")
    add_since_until(p, field="sitemap 月份")

    p = add_command(sub, "article", "文章內頁資訊", cmd_article)
    p.add_argument("refs", nargs="*", help="文章 ID 或 matcha-jp.com/tw/<ID> 網址")
    add_from(p, "id")
    run("matcha", ap)


if __name__ == "__main__":
    main()
