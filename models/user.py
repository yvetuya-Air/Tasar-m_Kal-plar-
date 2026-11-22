"""User veri modeli; SQLite kaydının tipli temsili."""
from dataclasses import dataclass, field
from models.base import RowModel


@dataclass(frozen=True)
class User(RowModel):
    id: int
    username: str
    password_hash: str = field(repr=False)
    role: str
    is_active: bool
    created_at: str
    session_version: int = 0
