"""Category veri modeli; SQLite kaydının tipli temsili."""
from dataclasses import dataclass
from models.base import RowModel


@dataclass(frozen=True)
class Category(RowModel):
    id: int
    name: str
