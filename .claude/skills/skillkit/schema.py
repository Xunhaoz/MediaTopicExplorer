"""輸出規範。每個指令輸出一個 envelope：

  {"source", "command", "fetched_at", "params", "items": [...], "errors": [{"input", "error"}]}

items 裡每一筆都是 Item 的子類別。Item 定義了跨來源共用的欄位名稱，子類別只能「加」來源特有的欄位；
extra="forbid" 讓拼錯或私自取名的欄位直接報錯。

命名規則（子類別也要遵守）：
- id 一律是字串；指向其他東西的 ID 用 <東西>_id，例如 channel_id、video_id
- 完整時間用 *_at（UTC，輸出成 ...Z）；只有日期用 *_date（YYYY-MM-DD）
- categories、tags 放名稱或 slug；放 ID 時用 category_ids、tag_ids
- description 是來源提供的摘要；text 是全文
"""
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, PlainSerializer

from .timeutil import to_utc, utc_z


def _require_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("時間必須帶時區；請先用 skillkit.timeutil.to_utc 轉換")
    return to_utc(dt)


UtcDatetime = Annotated[datetime, AfterValidator(_require_utc), PlainSerializer(utc_z, return_type=str)]
Date = Annotated[date, PlainSerializer(lambda d: d.isoformat(), return_type=str)]


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    url: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: UtcDatetime | None = None
    published_date: Date | None = None
    modified_at: UtcDatetime | None = None
    modified_date: Date | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    description: str | None = None
    text: str | None = None

    def dump(self) -> dict:
        # 只輸出建構時有給的欄位；明確給 None 的會保留成 null（例如「被隱藏」）
        return self.model_dump(mode="json", exclude_unset=True)


class ItemError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str
    error: str
