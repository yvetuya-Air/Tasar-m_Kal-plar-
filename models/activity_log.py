"""ActivityLog veri modeli; SQLite kaydının tipli temsili."""
from dataclasses import dataclass
from models.base import RowModel


@dataclass(frozen=True)
class ActivityLog(RowModel):
    id: int
    user_id: int | None
    action: str
    details: str
    created_at: str
