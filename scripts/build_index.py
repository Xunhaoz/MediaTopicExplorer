"""掃描 reports/travel_topics_YYYY-MM-DD.html，重新產生根目錄的 index.html。

  python3 scripts/build_index.py

只用標準庫。報告的標題取自 <title>，摘要取自 <meta name="description">（沒有就留空）。
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
NAME = re.compile(r"travel_topics_(\d{4}-\d{2}-\d{2})\.html$")
WEEKDAYS = "一二三四五六日"


def meta(path):
    head = path.read_text(encoding="utf-8", errors="ignore")[:20000]
    title = re.search(r"<title>(.*?)</title>", head, re.S)
    desc = re.search(r'<meta\s+name="description"\s+content="(.*?)"', head, re.S)
    return (html.unescape(title.group(1).strip()) if title else "旅遊話題洞察",
            html.unescape(desc.group(1).strip()) if desc else "")


def main():
    from datetime import date
    rows = []
    for p in REPORTS.glob("travel_topics_*.html"):
        m = NAME.search(p.name)
        if m:
            rows.append((date.fromisoformat(m.group(1)), p.name, *meta(p)))
    rows.sort(reverse=True)

    def card(d, name, title, desc, latest=False):
        label = f"{d:%Y/%m/%d}（{WEEKDAYS[d.weekday()]}）"
        tag = '<span class="new">最新</span>' if latest else ""
        sub = f'<p class="desc">{html.escape(desc)}</p>' if desc else ""
        return (f'<a class="card{" latest" if latest else ""}" href="reports/{name}">'
                f'<div class="date">{label}{tag}</div><div class="title">{html.escape(title)}</div>{sub}</a>')

    items = "\n".join(card(*r, latest=(i == 0)) for i, r in enumerate(rows)) or '<p class="empty">還沒有報告。</p>'
    updated = f"{rows[0][0]:%Y/%m/%d}" if rows else "—"
    (ROOT / "index.html").write_text(TEMPLATE.replace("{{ITEMS}}", items)
                                     .replace("{{UPDATED}}", updated)
                                     .replace("{{COUNT}}", str(len(rows))), encoding="utf-8")
    print(f"index.html：{len(rows)} 份報告")


TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>旅遊話題洞察</title>
<meta name="description" content="每日更新的旅遊話題洞察報告：熱門、趨勢、週期與候選熱門話題。">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&family=Noto+Serif+TC:wght@700;900&display=swap" rel="stylesheet">
<style>
:root{--bg:#f5f1ea;--paper:#fffdf9;--ink:#1e1b17;--muted:#6b645a;--line:#e3dccf;--accent:#b4441c;--accent-soft:#f6e3d8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#171513;--paper:#211e1b;--ink:#efe9df;--muted:#a59d91;--line:#36312b;--accent:#e9875c;--accent-soft:#3a2a22}}
:root[data-theme="dark"]{--bg:#171513;--paper:#211e1b;--ink:#efe9df;--muted:#a59d91;--line:#36312b;--accent:#e9875c;--accent-soft:#3a2a22}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans TC",system-ui,sans-serif;line-height:1.6}
main{max-width:760px;margin:0 auto;padding:48px 16px 64px}
h1{font-family:"Noto Serif TC",serif;font-weight:900;font-size:clamp(28px,6vw,40px);margin:0 0 6px;letter-spacing:.02em}
.lede{color:var(--muted);margin:0 0 28px}
.list{display:grid;gap:12px}
.card{display:block;background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:16px 18px;color:inherit;text-decoration:none;transition:border-color .15s}
.card:hover{border-color:var(--accent)}
.card.latest{border-left:4px solid var(--accent)}
.date{font-size:14px;color:var(--muted);font-weight:700;display:flex;gap:8px;align-items:center}
.new{background:var(--accent-soft);color:var(--accent);font-size:12px;padding:1px 8px;border-radius:99px}
.title{font-family:"Noto Serif TC",serif;font-weight:700;font-size:20px;margin-top:2px}
.desc{margin:6px 0 0;color:var(--muted);font-size:15px}
.empty{color:var(--muted)}
footer{margin-top:40px;color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:16px}
</style>
</head>
<body>
<main>
<h1>旅遊話題洞察</h1>
<p class="lede">每日更新・共 {{COUNT}} 份・最新 {{UPDATED}}</p>
<div class="list">
{{ITEMS}}
</div>
<footer>資料來源：PTT、YouTube、步步日本、MATCHA、Funliday、PR TIMES 與網路新聞。報告由 Claude 自動彙整，數據與日期以各報告內的原始來源為準。</footer>
</main>
</body>
</html>
"""

if __name__ == "__main__":
    main()
