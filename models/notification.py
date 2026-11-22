"""Notification veri modeli; SQLite kaydının tipli temsili."""
from dataclasses import dataclass
from models.base import RowModel


@dataclass(frozen=True)
class Notification(RowModel):
    id: int
    member_id: int
    reservation_id: int | None
    message: str
    is_read: bool
    created_at: str
