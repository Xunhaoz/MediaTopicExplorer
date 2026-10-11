"""參數與執行規範。

共用參數（各 skill 只能透過這裡加，不要自己取名）：
  --max N         筆數上限
  --max-pages N   頁數上限
  --since/--until YYYY-MM-DD，台灣時間，兩端都包含當天
  --from FILE     讀前一個指令的輸出（items[].id 或 items[].url），或每行一筆的文字檔；- 為 stdin

指令函式回傳 items，或 (items, errors)；run() 負責包成 envelope、印到 stdout、處理錯誤與退出碼。
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .schema import Item, ItemError
from .timeutil import parse_tw_date, tw_day_end, tw_day_start, utc_z


class SkillError(Exception):
    """給使用者看的錯誤訊息；run() 會印到 stderr 並以 1 結束。"""


def new_parser(doc):
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    return ap, ap.add_subparsers(dest="command", required=True)


def add_command(sub, name, help, func):
    p = sub.add_parser(name, help=help, description=help)
    p.set_defaults(func=func)
    return p


def add_max(p, default, help="筆數上限"):
    p.add_argument("--max", type=int, default=default, help=f"{help}（預設 {default}）")


def add_max_pages(p, default, help="頁數上限"):
    p.add_argument("--max-pages", type=int, default=default, help=f"{help}（預設 {default}）")


def add_since_until(p, field="發布時間"):
    p.add_argument("--since", type=parse_tw_date, help=f"YYYY-MM-DD（台灣時間），{field}在這天（含）之後")
    p.add_argument("--until", type=parse_tw_date, help=f"YYYY-MM-DD（台灣時間），{field}在這天（含）之前")


def add_from(p, key):
    p.add_argument("--from", dest="from_file", metavar="FILE",
                   help=f"讀前一個指令輸出的 items[].{key}，或每行一筆的文字檔；- 為 stdin")


def since_utc(args):
    return tw_day_start(args.since) if getattr(args, "since", None) else None


def until_utc(args):
    """--until 當天結束（不含）的 UTC 時間。"""
    return tw_day_end(args.until) if getattr(args, "until", None) else None


def in_range(dt, args) -> bool:
    lo, hi = since_utc(args), until_utc(args)
    return dt is not None and (lo is None or dt >= lo) and (hi is None or dt < hi)


def refs(args, positional, key):
    """位置參數加上 --from 讀到的值，去重並保留順序。"""
    values = list(positional or [])
    if getattr(args, "from_file", None):
        path = args.from_file
        text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            values += [line.strip() for line in text.splitlines() if line.strip()]
        else:
            rows = data.get("items", []) if isinstance(data, dict) else data
            values += [str(r[key]) for r in rows if isinstance(r, dict) and r.get(key)]
    return list(dict.fromkeys(values))


def ensure_parsed(items, page, what):
    """頁面有內容卻一筆都解析不到，代表網站結構可能改了，直接報錯，不要默默回傳空清單。"""
    if not items and page and page.strip():
        raise SkillError(f"頁面有內容，但解析不到任何{what}；網站結構可能改了")


def _params(args):
    skip = {"func", "command"}
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v)
            for k, v in vars(args).items() if k not in skip and v not in (None, [], False)}


def run(source, ap):
    args = ap.parse_args()
    try:
        result = args.func(args)
    except SkillError as e:
        sys.exit(f"{source}：{e}")
    except httpx.HTTPStatusError as e:
        sys.exit(f"{source}：HTTP {e.response.status_code}（{e.request.url}）")
    except httpx.TransportError as e:
        sys.exit(f"{source}：連線錯誤 {type(e).__name__}：{e}")
    items, errors = result if isinstance(result, tuple) else (result, [])
    for it in items:
        assert isinstance(it, Item), f"items 只能放 Item 子類別：{type(it)}"
    out = {
        "source": source,
        "command": args.command,
        "fetched_at": utc_z(datetime.now(timezone.utc)),
        "params": _params(args),
        "items": [it.dump() for it in items],
        "errors": [ItemError(input=str(e["input"]), error=str(e["error"])).model_dump() for e in errors],
    }
    print(f"{source} {args.command}：{len(items)} 筆" + (f"，{len(errors)} 筆失敗" if errors else ""),
          file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=1))
