"""Factory Method: istemci, soyut oluşturucu üzerinden kitap üretir."""
from abc import ABC, abstractmethod
from models.book import AudioBook, Book, PhysicalBook, EBook


class BookCreator(ABC):
    @abstractmethod
    def create_book(self, **data) -> Book:
        """Somut oluşturucunun sağladığı ürün oluşturma noktası."""

    def prepare_book(self, **data) -> Book:
        book = self.create_book(**data)
        book.validate_details()
        return book


class PhysicalBookCreator(BookCreator):
    def create_book(self, **data) -> Book:
        return PhysicalBook(**{**data, 'book_type': 'physical'})


class EBookCreator(BookCreator):
    def create_book(self, **data) -> Book:
        return EBook(**{**data, 'book_type': 'ebook'})


class AudioBookCreator(BookCreator):
    def create_book(self, **data) -> Book:
        return AudioBook(**{**data, 'book_type': 'audio'})


CREATORS = {'physical': PhysicalBookCreator, 'ebook': EBookCreator, 'audio': AudioBookCreator}
