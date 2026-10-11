"""HTML 解析統一用 selectolax 的 lexbor 後端（CSS selector）。"""
from selectolax.lexbor import LexborHTMLParser


def parse_html(page: str) -> LexborHTMLParser:
    return LexborHTMLParser(page)
