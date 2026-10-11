"""Funliday 部落格（www.funliday.com/posts/）文章清單與文章資訊。

部落格是 WordPress，但 REST API 要登入、RSS 關閉、列表頁由 JS 載入，所以清單取自 SEO 外掛的 sitemap，
文章資訊取自文章頁的 meta 標籤。

  funliday.py sitemap --since 2026-10-01
  funliday.py meta URL [URL ...] | --from FILE
"""
import re
import xml.etree.ElementTree as ET

import httpx

from skillkit import (Http, Item, SkillError, add_command, add_from, add_since_until, in_range,
                      new_parser, parse_html, refs, run, to_utc)

BASE = "https://www.funliday.com/posts"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
http = Http(delay=0.5, concurrency=4)


class Entry(Item):
    pass


def slug(url):
    return url.rstrip("/").rsplit("/", 1)[-1]


def get_xml(url):
    try:
        return ET.fromstring(http.get(url).content.lstrip())  # 網站在 XML 宣告前多輸出了空行
    except ET.ParseError as e:
        raise SkillError(f"sitemap 不是合法的 XML（{url}）：{e}") from None


def cmd_sitemap(args):
    index = get_xml(f"{BASE}/sitemap.xml")
    maps = [e.text.strip() for e in index.findall("sm:sitemap/sm:loc", NS) if re.search(r"/post-sitemap\d*\.xml", e.text)]
    if not maps:
        raise SkillError("sitemap 索引裡找不到 post-sitemap；網站結構可能改了")
    out = []
    for sm in maps:
        for u in get_xml(sm).findall("sm:url", NS):
            url = u.findtext("sm:loc", namespaces=NS).strip()
            modified = to_utc(u.findtext("sm:lastmod", namespaces=NS))
            if (args.since or args.until) and not in_range(modified, args):
                continue
            out.append(Entry(id=slug(url), url=url, modified_at=modified))
    return sorted(out, key=lambda e: e.modified_at.timestamp() if e.modified_at else 0, reverse=True)


def parse_meta(url, page):
    tree = parse_html(page)

    def prop(name):
        node = tree.css_first(f'meta[property="{name}"]')
        return node.attributes.get("content") if node else None

    if not prop("og:title"):
        raise SkillError("找不到 og:title；網站結構可能改了")
    # 只看文章本身 <article class="hentry ... category-xxx">；相關文章卡片和選單裡的分類不算
    art = tree.css_first("article.hentry")
    classes = (art.attributes.get("class") or "").split() if art else []
    return Entry(
        id=slug(url),
        url=url,
        title=re.sub(r"\s*\|\s*Funliday$", "", prop("og:title")),
        published_at=to_utc(prop("article:published_time")),
        modified_at=to_utc(prop("article:modified_time")),
        categories=[c.removeprefix("category-") for c in classes if c.startswith("category-")],
        description=prop("og:description"),
    )


def cmd_meta(args):
    urls = refs(args, args.urls, "url")
    if not urls:
        raise SkillError("請給文章網址，或用 --from 指定檔案")

    def one(url):
        try:
            return parse_meta(url, http.get(url).text)
        except httpx.HTTPStatusError as e:
            return {"input": url, "error": f"HTTP {e.response.status_code}"}
        except httpx.TransportError as e:
            return {"input": url, "error": f"連線錯誤 {type(e).__name__}"}

    results = http.map(one, urls)
    return [r for r in results if isinstance(r, Item)], [r for r in results if isinstance(r, dict)]


def main():
    ap, sub = new_parser(__doc__)
    p = add_command(sub, "sitemap", "列出 sitemap 裡的文章網址與最後修改時間，由新到舊", cmd_sitemap)
    add_since_until(p, field="最後修改時間")

    p = add_command(sub, "meta", "抓文章頁的標題、發布／修改時間、分類、摘要", cmd_meta)
    p.add_argument("urls", nargs="*", help="文章網址")
    add_from(p, "url")
    run("funliday", ap)


if __name__ == "__main__":
    main()
