"""Satır eşleme ortak davranışı; SQL işlemleri modellerden ayrıdır."""
from dataclasses import fields


class RowModel:
    @classmethod
    def from_row(cls, row):
        values = {f.name: row[f.name] for f in fields(cls)}
        for key in ('is_active', 'is_read'):
            if key in values:
                values[key] = bool(values[key])
        return cls(**values)
