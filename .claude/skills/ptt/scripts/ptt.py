"""PTT（www.ptt.cc 網頁版）看板文章列表與站內搜尋。只讀列表頁，不抓內文。

  ptt.py list Japan_Travel --since 2026-09-27
  ptt.py search Japan_Travel esim --max-pages 3
"""
import re
from urllib.parse import urlencode

import httpx

from skillkit import (Http, Item, SkillError, add_command, add_max_pages, add_since_until, in_range, new_parser,
                      parse_html, run, since_utc, to_utc)

BASE = "https://www.ptt.cc"
http = Http(delay=0.8, cookies={"over18": "1"}, timeout=20)

FILE_RE = re.compile(r"/M\.(\d+)\.A\.[0-9A-F]+\.html$")
TAG_RE = re.compile(r"^(Re:\s*|Fw:\s*)?\[([^\]]+)\]")


class Post(Item):
    board: str
    tag: str | None
    is_reply: bool
    nrec: int


def parse_nrec(text):
    """推減噓的淨值：爆＝100 以上記為 100；X1–X9＝噓多 10–90 記為 -10～-90；XX 記為 -100；空白記為 0。"""
    text = text.strip()
    if text == "爆":
        return 100
    if text.startswith("X"):
        return -100 if text == "XX" else -int(text[1:] or 1) * 10
    return int(text) if text.isdigit() else 0


def fetch(path, board):
    try:
        return http.get(BASE + path).text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404 and "/search" not in path:
            raise SkillError(f"看板 {board} 不存在，或大小寫不對") from None
        raise


def parse_page(page, board):
    """回傳 (文章清單, 上一頁路徑)。置底公告（r-list-sep 之後）和已刪除文章不列入。"""
    tree = parse_html(page)
    container = tree.css_first("div.r-list-container")
    if container is None:
        raise SkillError("找不到文章列表區塊；網站結構可能改了")
    posts = []
    for node in container.iter():
        classes = (node.attributes.get("class") or "").split()
        if "r-list-sep" in classes:
            break
        if "r-ent" not in classes:
            continue
        link = node.css_first("div.title a")
        m = FILE_RE.search(link.attributes.get("href", "")) if link else None
        if not m:
            continue
        title = link.text(strip=True)
        tag = TAG_RE.match(title)
        posts.append(Post(
            id=link.attributes["href"].rsplit("/", 1)[-1].removesuffix(".html"),
            url=BASE + link.attributes["href"],
            title=title,
            author=node.css_first("div.author").text(strip=True),
            published_at=to_utc(int(m.group(1))),
            board=board,
            tag=tag.group(2) if tag else None,
            is_reply=bool(tag and tag.group(1)),
            nrec=parse_nrec(node.css_first("div.nrec").text()),
        ))
    prev = next((a.attributes.get("href") for a in tree.css("div.btn-group-paging a")
                 if "上頁" in a.text() and a.attributes.get("href")), None)
    return posts, prev


def cmd_list(args):
    path, out, seen, pages = f"/bbs/{args.board}/index.html", [], set(), 0
    lo = since_utc(args)
    while path and pages < args.max_pages:
        posts, path = parse_page(fetch(path, args.board), args.board)
        pages += 1
        for p in posts:
            if in_range(p.published_at, args) and p.id not in seen:
                seen.add(p.id)
                out.append(p)
        if lo and posts and all(p.published_at < lo for p in posts):  # 整頁都比 since 舊就停
            break
    return sorted(out, key=lambda p: p.published_at, reverse=True)


def cmd_search(args):
    out = []
    for page in range(1, args.max_pages + 1):
        try:
            posts, prev = parse_page(fetch(f"/bbs/{args.board}/search?{urlencode({'page': page, 'q': args.query})}",
                                           args.board), args.board)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                if page == 1:
                    raise SkillError(f"看板 {args.board} 不存在，或大小寫不對") from None
                break  # 超過最後一頁
            raise
        out += posts
        if not posts or not prev:
            break
    return sorted(out, key=lambda p: p.published_at, reverse=True)


def main():
    ap, sub = new_parser(__doc__)
    p = add_command(sub, "list", "看板最新文章列表，由新往舊翻頁", cmd_list)
    p.add_argument("board", help="看板英文名稱，大小寫要正確，例如 Japan_Travel")
    add_since_until(p)
    add_max_pages(p, 20, "頁數上限，每頁約 20 篇")

    p = add_command(sub, "search", "看板站內搜尋", cmd_search)
    p.add_argument("board", help="看板英文名稱")
    p.add_argument("query", help="關鍵字（比對標題），或 PTT 搜尋語法：author:ID、recommend:N、thread:標題")
    add_max_pages(p, 1, "頁數上限，每頁約 20 篇")
    run("ptt", ap)


if __name__ == "__main__":
    main()
