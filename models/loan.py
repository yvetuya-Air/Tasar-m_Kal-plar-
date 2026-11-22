"""Loan veri modeli; SQLite kaydının tipli temsili."""
from dataclasses import dataclass
from models.base import RowModel


@dataclass(frozen=True)
class Loan(RowModel):
    id: int
    book_id: int
    member_id: int
    borrowed_on: str
    due_on: str
    returned_on: str | None
    penalty_cents: int
