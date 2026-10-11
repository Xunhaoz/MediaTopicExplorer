"""YouTube Data API v3 唯讀查詢。

授權（依序找第一個有的）：
  1. 環境變數 YOUTUBE_API_KEY
  2. 環境變數 YOUTUBE_CREDENTIALS（服務帳戶 JSON 路徑）
  3. 專案根目錄的 youtube-service-account.json
  4. 都沒有：不帶憑證送出，交給雲端環境的 network secret 在 proxy 補上 X-Goog-Api-Key

  yt.py search "京都 紅葉" --max 50 --order viewCount --since 2026-09-11
  yt.py stats VIDEO_ID [VIDEO_ID ...] | --from FILE
  yt.py channels @handle [UC... ...]
  yt.py uploads @handle [UC... ...] --max 50 --since 2026-09-11
  yt.py comments VIDEO_ID [VIDEO_ID ...] | --from FILE --max 100
"""
import os
import re
import threading
from pathlib import Path

from skillkit import (Http, Item, SkillError, add_command, add_from, add_max, add_since_until, in_range, new_parser,
                      refs, run, since_utc, to_utc, until_utc)
from skillkit.timeutil import utc_z

BASE = "https://www.googleapis.com/youtube/v3/"
DEFAULT_CREDENTIALS = Path(__file__).resolve().parents[4] / "youtube-service-account.json"
SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"  # readonly 範圍下 commentThreads.list 會回 403
http = Http(concurrency=4)


# ---------- 輸出欄位 ----------

class Video(Item):
    channel_id: str
    channel_title: str


class VideoStats(Video):
    duration_seconds: int | None
    live: str
    views: int | None
    likes: int | None
    comments: int | None
    category_id: str | None
    topic_categories: list[str]


class Channel(Item):
    handle: str | None
    subscribers: int | None
    video_count: int
    view_count: int
    uploads_playlist_id: str


class Comment(Item):
    video_id: str
    likes: int
    replies: int


# ---------- API ----------

class YouTubeError(Exception):
    def __init__(self, status, reason, message):
        super().__init__(f"{status} {reason}：{message}")
        self.reason = reason


class Auth:
    def __init__(self):
        self.api_key = os.environ.get("YOUTUBE_API_KEY")
        self.creds = None
        self.lock = threading.Lock()
        if self.api_key:
            return
        path = os.environ.get("YOUTUBE_CREDENTIALS")
        if path and not Path(path).is_file():
            raise SkillError(f"YOUTUBE_CREDENTIALS 指向的檔案不存在：{path}")
        path = path or (DEFAULT_CREDENTIALS if DEFAULT_CREDENTIALS.is_file() else None)
        if path:
            from google.oauth2 import service_account
            self.creds = service_account.Credentials.from_service_account_file(path, scopes=[SCOPE])

    def apply(self):
        if self.api_key:
            return {"key": self.api_key}, {}
        if not self.creds:
            return {}, {}
        with self.lock:
            if not self.creds.valid:
                from google.auth.transport.requests import Request
                self.creds.refresh(Request())
            return {}, {"Authorization": f"Bearer {self.creds.token}"}


_auth = None


def api(endpoint, **params):
    global _auth
    _auth = _auth or Auth()
    auth_params, headers = _auth.apply()
    resp = http.get(BASE + endpoint, params={**params, **auth_params}, headers=headers, check=False)
    body = resp.json() if resp.content else {}
    if resp.is_error:
        err = body.get("error", {})
        reason = (err.get("errors") or [{}])[0].get("reason", "unknown")
        message = err.get("message", "")
        if resp.status_code == 403 and not (_auth.api_key or _auth.creds):
            message += "（沒有找到本機憑證，network secret 也沒有生效：請設定 YOUTUBE_API_KEY、YOUTUBE_CREDENTIALS，"\
                       "或在雲端環境替 www.googleapis.com 加上 X-Goog-Api-Key 的 network secret）"
        raise YouTubeError(resp.status_code, reason, message)
    return body


def paginate(endpoint, max_items, page_size, **params):
    items, token = [], None
    while len(items) < max_items:
        body = api(endpoint, maxResults=min(page_size, max_items - len(items)), pageToken=token, **params)
        items += body.get("items", [])
        token = body.get("nextPageToken")
        if not token:
            break
    return items[:max_items]


def guard(fn):
    """整個指令層級的 API 錯誤轉成 SkillError（配額用完、憑證錯誤等）。"""
    def wrapped(args):
        try:
            return fn(args)
        except YouTubeError as e:
            raise SkillError(f"YouTube API 錯誤 {e}") from None
    return wrapped


VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/live/)([\w-]{11})")
CHANNEL_ID_RE = re.compile(r"(UC[\w-]{22})")
HANDLE_RE = re.compile(r"(?:youtube\.com/)?(@[\w.\-]+)")
DURATION_RE = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def to_video_id(ref):
    m = VIDEO_ID_RE.search(ref)
    return m.group(1) if m else ref.strip()


def video_url(vid):
    return f"https://www.youtube.com/watch?v={vid}"


def parse_duration(iso):
    m = DURATION_RE.fullmatch(iso or "")
    if not m:
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


# ---------- search ----------

@guard
def cmd_search(args):
    lo, hi = since_utc(args), until_utc(args)
    items = paginate("search", args.max, 50, part="snippet", q=args.query, type="video", order=args.order,
                     regionCode=args.region, relevanceLanguage=args.lang, videoDuration=args.duration,
                     channelId=args.channel, publishedAfter=utc_z(lo) if lo else None,
                     publishedBefore=utc_z(hi) if hi else None)
    return [Video(id=it["id"]["videoId"], url=video_url(it["id"]["videoId"]), title=it["snippet"]["title"],
                  published_at=to_utc(it["snippet"]["publishedAt"]), description=it["snippet"].get("description", ""),
                  channel_id=it["snippet"]["channelId"], channel_title=it["snippet"]["channelTitle"])
            for it in items if it.get("id", {}).get("videoId")]


# ---------- stats ----------

def to_stats(item):
    sn, st, cd = item["snippet"], item.get("statistics", {}), item.get("contentDetails", {})
    as_int = lambda k: int(st[k]) if k in st else None  # 欄位不存在＝創作者隱藏，保留 null
    return VideoStats(
        id=item["id"], url=video_url(item["id"]), title=sn["title"], published_at=to_utc(sn["publishedAt"]),
        tags=sn.get("tags", []), description=sn.get("description", ""),
        channel_id=sn["channelId"], channel_title=sn["channelTitle"],
        duration_seconds=parse_duration(cd.get("duration")), live=sn.get("liveBroadcastContent", "none"),
        views=as_int("viewCount"), likes=as_int("likeCount"), comments=as_int("commentCount"),
        category_id=sn.get("categoryId"), topic_categories=item.get("topicDetails", {}).get("topicCategories", []),
    )


@guard
def cmd_stats(args):
    ids = list(dict.fromkeys(to_video_id(r) for r in refs(args, args.ids, "id")))
    if not ids:
        raise SkillError("請給影片 ID 或網址，或用 --from 指定檔案")
    batches = [ids[i:i + 50] for i in range(0, len(ids), 50)]
    bodies = http.map(lambda b: api("videos", part="snippet,statistics,contentDetails,topicDetails",
                                    id=",".join(b), maxResults=50), batches)
    videos = [to_stats(it) for body in bodies for it in body.get("items", [])]
    found = {v.id for v in videos}
    return videos, [{"input": i, "error": "查不到（私人、已刪除、會員限定或 ID 錯誤）"} for i in ids if i not in found]


# ---------- channels / uploads ----------

def resolve_channel(ref):
    if m := CHANNEL_ID_RE.search(ref):
        params = {"id": m.group(1)}
    elif m := HANDLE_RE.search(ref):
        params = {"forHandle": m.group(1)}
    else:
        return {"input": ref, "error": "看不懂的頻道：請用 @handle、頻道網址或 UC 開頭的頻道 ID"}
    items = api("channels", part="snippet,contentDetails,statistics", **params).get("items", [])
    if not items:
        return {"input": ref, "error": "找不到頻道"}
    ch, stats = items[0], items[0].get("statistics", {})
    return Channel(
        id=ch["id"], url=f"https://www.youtube.com/channel/{ch['id']}", title=ch["snippet"]["title"],
        published_at=to_utc(ch["snippet"].get("publishedAt")), description=ch["snippet"].get("description", ""),
        handle=ch["snippet"].get("customUrl"),
        subscribers=None if stats.get("hiddenSubscriberCount") else int(stats.get("subscriberCount", 0)),
        video_count=int(stats.get("videoCount", 0)), view_count=int(stats.get("viewCount", 0)),
        uploads_playlist_id=ch["contentDetails"]["relatedPlaylists"]["uploads"],
    )


def split(results):
    return [r for r in results if isinstance(r, Item)], [r for r in results if isinstance(r, dict)]


@guard
def cmd_channels(args):
    return split(http.map(resolve_channel, args.channels))


def list_uploads(ch, args):
    """上傳清單由新到舊；遇到比 --since 舊的就停止翻頁。"""
    lo, videos, token = since_utc(args), [], None
    while len(videos) < args.max:
        body = api("playlistItems", part="snippet,contentDetails", playlistId=ch.uploads_playlist_id,
                   maxResults=min(50, args.max - len(videos)), pageToken=token)
        stop = False
        for it in body.get("items", []):
            published = to_utc(it["contentDetails"].get("videoPublishedAt") or it["snippet"]["publishedAt"])
            if lo and published < lo:
                stop = True
            if not in_range(published, args):
                continue
            vid = it["contentDetails"]["videoId"]
            videos.append(Video(id=vid, url=video_url(vid), title=it["snippet"]["title"], published_at=published,
                                channel_id=ch.id, channel_title=ch.title))
        token = body.get("nextPageToken")
        if stop or not token:
            break
    return videos[:args.max]


@guard
def cmd_uploads(args):
    channels, errors = split(http.map(resolve_channel, args.channels))
    videos = [v for vs in http.map(lambda ch: list_uploads(ch, args), channels) for v in vs]
    return videos, errors


# ---------- comments ----------

def fetch_comments(vid, args):
    try:
        items = paginate("commentThreads", args.max, 100, part="snippet", videoId=vid, order=args.order,
                         textFormat="plainText")
    except YouTubeError as e:
        if e.reason in ("commentsDisabled", "videoNotFound"):
            return {"input": vid, "error": e.reason}
        raise
    out = []
    for it in items:
        top = it["snippet"]["topLevelComment"]["snippet"]
        out.append(Comment(id=it["id"], url=f"{video_url(vid)}&lc={it['id']}",
                           text=top.get("textOriginal") or top.get("textDisplay", ""),
                           published_at=to_utc(top.get("publishedAt")), video_id=vid,
                           likes=top.get("likeCount", 0), replies=it["snippet"].get("totalReplyCount", 0)))
    return out


@guard
def cmd_comments(args):
    ids = list(dict.fromkeys(to_video_id(r) for r in refs(args, args.video_ids, "id")))
    if not ids:
        raise SkillError("請給影片 ID 或網址，或用 --from 指定檔案")
    results = http.map(lambda v: fetch_comments(v, args), ids)
    return [c for r in results if isinstance(r, list) for c in r], [r for r in results if isinstance(r, dict)]


# ---------- main ----------

def main():
    ap, sub = new_parser(__doc__)
    p = add_command(sub, "search", "關鍵字搜尋影片（search.list，每 50 筆用 1 次搜尋額度）", cmd_search)
    p.add_argument("query")
    add_max(p, 50, "筆數上限，每 50 筆一頁")
    p.add_argument("--order", choices=["relevance", "date", "viewCount", "rating"], default="relevance")
    add_since_until(p)
    p.add_argument("--region", help="regionCode，例如 TW；不給就不限")
    p.add_argument("--lang", help="relevanceLanguage，例如 zh-Hant；不給就不限")
    p.add_argument("--duration", choices=["any", "short", "medium", "long"], default="any",
                   help="short <4 分、medium 4–20 分、long >20 分")
    p.add_argument("--channel", help="只搜這個頻道 ID")

    p = add_command(sub, "stats", "影片統計（videos.list，每 50 支 1 unit）", cmd_stats)
    p.add_argument("ids", nargs="*", help="影片 ID 或網址")
    add_from(p, "id")

    p = add_command(sub, "channels", "頻道資訊（channels.list，每個頻道 1 unit）", cmd_channels)
    p.add_argument("channels", nargs="+", help="@handle、頻道網址或 UC 開頭的頻道 ID")

    p = add_command(sub, "uploads", "頻道上傳清單（channels.list＋playlistItems.list），由新到舊", cmd_uploads)
    p.add_argument("channels", nargs="+", help="@handle、頻道網址或 UC 開頭的頻道 ID")
    add_max(p, 50, "每個頻道的影片數上限")
    add_since_until(p)

    p = add_command(sub, "comments", "頂層留言（commentThreads.list，每 100 則 1 unit）", cmd_comments)
    p.add_argument("video_ids", nargs="*", help="影片 ID 或網址")
    add_from(p, "id")
    add_max(p, 100, "每支影片的留言數上限")
    p.add_argument("--order", choices=["relevance", "time"], default="relevance")
    run("youtube", ap)


if __name__ == "__main__":
    main()
