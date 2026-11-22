"""Soyut kitap ve fiziksel/elektronik kitap ürünleri."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from models.urls import http_url_parts
from models.base import RowModel


@dataclass(frozen=True)
class Book(RowModel, ABC):
    id: int | None
    title: str
    author: str
    isbn: str | None
    category_id: int | None
    book_type: str
    total_copies: int
    shelf_location: str | None
    file_url: str | None
    created_at: str
    cover_url: str | None = None
    description: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    managed_media: bool = False

    @property
    @abstractmethod
    def type_label(self):
        """Ürünün kullanıcıya gösterilen türü."""

    @abstractmethod
    def validate_details(self):
        """Ürüne özgü alan kuralları."""

    @classmethod
    def from_row(cls, row):
        if cls is Book:
            products = {'physical': PhysicalBook, 'ebook': EBook, 'audio': AudioBook}
            try:
                product = products[row['book_type']]
            except KeyError as error:
                raise ValueError('Geçersiz kitap türü.') from error
            return product.from_row(row)
        return super().from_row(row)


@dataclass(frozen=True)
class PhysicalBook(Book):
    @property
    def type_label(self):
        return 'Fiziksel Kitap'

    def validate_details(self):
        if self.book_type != 'physical' or not isinstance(self.shelf_location,str) or not self.shelf_location.strip() or len(self.shelf_location) > 80 or self.file_url:
            raise ValueError('Fiziksel kitap için en fazla 80 karakterlik raf konumu gerekir; dosya adresi boş olmalıdır.')


@dataclass(frozen=True)
class EBook(Book):
    @property
    def type_label(self):
        return 'Elektronik Kitap'

    def validate_details(self):
        has_file = not self.file_url if self.managed_media else http_url_parts(self.file_url) is not None
        if self.book_type != 'ebook' or not has_file or self.shelf_location:
            raise ValueError('Elektronik kitap için geçerli bir HTTP/HTTPS dosya adresi gerekir; raf konumu boş olmalıdır.')


@dataclass(frozen=True)
class AudioBook(Book):
    @property
    def type_label(self):
        return 'Sesli Kitap'

    def validate_details(self):
        if self.book_type != 'audio' or not self.managed_media or self.file_url or self.shelf_location:
            raise ValueError('Sesli kitap için bir ses dosyası yükleyin.')
