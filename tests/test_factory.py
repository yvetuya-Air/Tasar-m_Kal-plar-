"""Factory Method soyutlama ve ürün davranışı birim testleri."""
from dataclasses import FrozenInstanceError
import pytest
from models.book import Book, PhysicalBook, EBook
from patterns.factory_method import BookCreator, PhysicalBookCreator, EBookCreator


def book_data(**overrides):
    return dict(id=None, title='Test Kitabı', author='Test Yazarı', isbn=None,
                category_id=None, total_copies=1, shelf_location='A-01', file_url=None,
                created_at='', **overrides)


def test_abstract_classes_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Book(**book_data(), book_type='physical')
    with pytest.raises(TypeError):
        BookCreator()


def test_physical_creator_product():
    book = PhysicalBookCreator().prepare_book(**book_data())
    assert isinstance(book, Book) and isinstance(book, PhysicalBook)
    assert book.book_type == 'physical' and book.type_label == 'Fiziksel Kitap'
    with pytest.raises(FrozenInstanceError):
        book.title = 'Yeni'


def test_ebook_creator_product():
    data = book_data()
    data.update(shelf_location=None, file_url='https://example.invalid/book.pdf')
    book = EBookCreator().prepare_book(**data)
    assert isinstance(book, EBook)
    assert book.book_type == 'ebook' and book.type_label == 'Elektronik Kitap'


@pytest.mark.parametrize('shelf,url', [(None,None),('   ',None),('A','https://example.invalid'),('a'*81,None)])
def test_physical_details(shelf, url):
    data = book_data()
    data.update(shelf_location=shelf, file_url=url)
    with pytest.raises(ValueError):
        PhysicalBookCreator().prepare_book(**data)


@pytest.mark.parametrize('url', ['', 'javascript:alert(1)', 'file:///etc/passwd', 'https://', 'https://user:secret@example.invalid/book', 'https://[broken', 'https://example.invalid:99999', 'https://example.invalid/a b'])
def test_ebook_url_validation(url):
    data = book_data()
    data.update(shelf_location=None, file_url=url)
    with pytest.raises(ValueError):
        EBookCreator().prepare_book(**data)


def test_creator_template_calls_overridden_factory_method():
    class RecordingCreator(PhysicalBookCreator):
        called = False

        def create_book(self, **data):
            self.called = True
            return super().create_book(**data)

    creator = RecordingCreator()
    assert isinstance(creator.prepare_book(**book_data()), PhysicalBook)
    assert creator.called
