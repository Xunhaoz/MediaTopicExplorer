"""HTTP 規範：每個來源一個 Http，統一逾時、重試、請求間隔與同時請求數上限。

- delay：相鄰兩次請求「開始」的最短間隔（秒），跨執行緒共用。
- concurrency：Http.map 同時進行的請求數上限。
- 遇到連線錯誤、逾時、429、5xx 會重試（最多 3 次，指數退避）；其他 4xx 不重試。
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

UA = "Mozilla/5.0 (personal research)"
RETRY_STATUS = {429, 500, 502, 503, 504}


def _retryable(e: BaseException) -> bool:
    if isinstance(e, httpx.TransportError):
        return True
    return isinstance(e, httpx.HTTPStatusError) and e.response.status_code in RETRY_STATUS


class Http:
    def __init__(self, delay=0.0, concurrency=1, timeout=30.0, headers=None, cookies=None):
        self.delay = delay
        self.concurrency = concurrency
        self.client = httpx.Client(headers={"User-Agent": UA, **(headers or {})}, cookies=cookies,
                                   timeout=timeout, follow_redirects=True)
        self._lock = threading.Lock()
        self._next_start = 0.0

    def _throttle(self):
        with self._lock:
            now = time.monotonic()
            wait = self._next_start - now
            self._next_start = max(now, self._next_start) + self.delay
        if wait > 0:
            time.sleep(wait)

    @retry(retry=retry_if_exception(_retryable), stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, max=8), reraise=True)
    def get(self, url, params=None, headers=None, check=True) -> httpx.Response:
        """check=True 時 4xx/5xx 丟 httpx.HTTPStatusError；check=False 只對可重試的狀態碼重試，其餘照樣回傳。"""
        self._throttle()
        params = {k: v for k, v in (params or {}).items() if v is not None}
        # 空的 params 不能傳給 httpx，否則會清掉 url 上原本的查詢字串
        resp = self.client.get(url, params=params or None, headers=headers)
        if resp.status_code in RETRY_STATUS or (check and resp.is_error):
            resp.raise_for_status()
        return resp

    def map(self, fn, items):
        """以 concurrency 個執行緒平行執行 fn，結果順序與輸入相同。"""
        items = list(items)
        if self.concurrency <= 1 or len(items) <= 1:
            return [fn(x) for x in items]
        with ThreadPoolExecutor(self.concurrency) as ex:
            return list(ex.map(fn, items))
