"""Member veri modeli; SQLite kaydının tipli temsili."""
from dataclasses import dataclass
from models.base import RowModel


@dataclass(frozen=True)
class Member(RowModel):
    id: int
    user_id: int | None
    full_name: str
    email: str
    member_type: str
    is_active: bool
    created_at: str
