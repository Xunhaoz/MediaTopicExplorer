"""時間規範：日期參數一律是台灣時間；輸出的時間一律是 UTC。"""
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
JST = ZoneInfo("Asia/Tokyo")


def parse_tw_date(s: str) -> date:
    """參數用的 YYYY-MM-DD。"""
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise ValueError(f"日期格式要是 YYYY-MM-DD：{s!r}") from None


def tw_day_start(d: date) -> datetime:
    """台灣時間當天 00:00，換成 UTC。"""
    return datetime.combine(d, time(), TPE).astimezone(timezone.utc)


def tw_day_end(d: date) -> datetime:
    """台灣時間隔天 00:00（不含），換成 UTC。--until 包含當天，所以用隔天開頭當上界。"""
    return tw_day_start(d + timedelta(days=1))


def to_utc(value, assume=None) -> datetime | None:
    """把來源的各種時間格式轉成帶時區的 UTC datetime。

    接受 datetime、unix 秒數、ISO 8601（含 Z、+09:00、+0900）、RFC 2822（RSS）。
    來源沒有時區時，必須用 assume 指定來源時區，否則丟 ValueError，避免默默猜錯。
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            dt = parsedate_to_datetime(s)  # RFC 2822
    if dt.tzinfo is None:
        if assume is None:
            raise ValueError(f"時間沒有時區，請指定來源時區：{value!r}")
        dt = dt.replace(tzinfo=assume)
    return dt.astimezone(timezone.utc)


def to_date(value) -> date | None:
    """只有日期的來源值（2026-10-09、2026.10.09、2026/10/09）。"""
    if not value:
        return None
    return date.fromisoformat(str(value).strip().replace(".", "-").replace("/", "-"))


def utc_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
