"""Reservation veri modeli; SQLite kaydının tipli temsili."""
from dataclasses import dataclass
from models.base import RowModel


@dataclass(frozen=True)
class Reservation(RowModel):
    id: int
    book_id: int
    member_id: int
    status: str
    created_at: str
