"""Nesne adaptörü: Google Books, BookDataProvider sözleşmesine uyarlanır."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from urllib.parse import urlunsplit, parse_qsl, urlencode
from models.urls import http_url_parts
from models.isbn import normalize_isbn, valid_isbn
from services.google_books_api import GoogleBooksAPI, BookProviderError


@dataclass(frozen=True)
class BookImportData:
    source_id: str
    title: str
    author: str
    isbn: str
    thumbnail: str | None
    warnings: tuple[str, ...]
    description: str = ''
    publisher: str = ''
    publication_year: int | None = None
    language: str = ''
    publication_date: str = ''

    def to_form(self):
        return {'title':self.title, 'author':self.author, 'isbn':self.isbn,
                'book_type':'physical','total_copies':1,'category_id':'',
                'shelf_location':'','file_url':'', 'cover_url':self.thumbnail,
                'description':self.description, 'publisher':self.publisher,
                'publication_year':self.publication_year, 'language':self.language}


PAGE_SIZE = 12


@dataclass(frozen=True)
class BookSearchPage:
    books: tuple[BookImportData, ...]
    has_next: bool = False


class BookDataProvider(ABC):
    @abstractmethod
    def search_page(self, *, title='', author='', isbn='', page=1) -> BookSearchPage:
        """Sayfalı arama sonuçları."""

    @abstractmethod
    def search_books(self, *, title='', author='', isbn='') -> list[BookImportData]:
        """İç uygulama biçiminde arama sonuçları."""

    @abstractmethod
    def get_book(self, source_id) -> BookImportData:
        """Seçilen kaydın düzenlenebilir iç biçimi."""


def safe_thumbnail(value):
    parts=http_url_parts(value)
    if parts is None or parts.hostname not in ('books.google.com','books.googleusercontent.com','covers.openlibrary.org') or parts.port is not None:
        return None
    if parts.hostname == 'covers.openlibrary.org' and not re.fullmatch(r'/b/id/[1-9][0-9]{0,11}-[SML]\.jpg', parts.path):
        return None
    query = urlencode([(k,v) for k,v in parse_qsl(parts.query) if k.lower() != 'key'])
    return urlunsplit(('https',parts.netloc,parts.path,query,''))


def search_fields(title, author, isbn):
    title, author, isbn = (' '.join(str(value).split()) for value in (title, author, isbn))
    if not any((title, author, isbn)) or any(len(value) > 200 for value in (title, author, isbn)):
        raise ValueError('En az bir arama alanı doldurun; her alan en fazla 200 karakter olmalıdır.')
    if isbn:
        isbn = normalize_isbn(isbn)
        if not valid_isbn(isbn):
            raise ValueError('Arama için geçerli bir ISBN-10 veya ISBN-13 girin.')
    return title, author, isbn


def clean_text(value, limit):
    return value.strip()[:limit] if isinstance(value, str) else ''


def publication_year(value):
    match = re.match(r'^([0-9]{4})(?:$|-)', str(value))
    return int(match[1]) or None if match else None


def import_warnings(title, author, isbn):
    warnings = [message for value, message in (
        (title, 'Başlık eksik; kaydetmeden önce doldurun.'),
        (author, 'Yazar eksik; kaydetmeden önce doldurun.'),
        (isbn, 'Geçerli ISBN bulunamadı; isterseniz elle ekleyin.'),
    ) if not value]
    if len(title) > 200 or len(author) > 160:
        warnings.append('Başlık veya yazar alanı çok uzun; kaydetmeden önce kısaltın.')
    return tuple(warnings)


class GoogleBooksAdapter(BookDataProvider):
    def __init__(self, api: GoogleBooksAPI):
        self.api = api

    def search_books(self, *, title='', author='', isbn=''):
        return list(self.search_page(title=title, author=author, isbn=isbn).books)

    def search_page(self, *, title='', author='', isbn='', page=1):
        title, author, isbn = search_fields(title, author, isbn)
        terms = []
        for prefix,value in (('intitle',title),('inauthor',author)):
            if value:
                # Kullanıcı girdisi ek Google sorgu işleçleri oluşturamaz.
                clean = value.replace('"',' ').replace(':',' ')
                terms.append(f'{prefix}:"{clean}"')
        if isbn:
            terms.append('isbn:'+isbn)
        query = ' '.join(terms)
        offset = (page - 1) * PAGE_SIZE
        payload = self.api.search_volumes(query, start_index=offset) if offset else self.api.search_volumes(query)
        items = payload.get('items', [])
        total = payload.get('totalItems')
        if not isinstance(items,list):
            raise BookProviderError('Google Books sonuç listesi geçersiz.', 'invalid_response')
        if not items and not (type(total) is int and 0 <= total <= offset):
            raise BookProviderError('Google Books sonuç listesi eksik.', 'invalid_response')
        results = []
        seen = set()
        for item in items[:PAGE_SIZE]:
            if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',item['id']):
                continue
            if item['id'] not in seen:
                results.append(self.adapt(item))
                seen.add(item['id'])
        if items and not results:
            raise BookProviderError('Google Books kullanılabilir bir kitap kaydı döndürmedi.', 'invalid_response')
        has_next = bool(items) and (total > offset + PAGE_SIZE if type(total) is int else len(items) >= PAGE_SIZE)
        return BookSearchPage(tuple(results), has_next)

    def get_book(self, source_id):
        payload = self.api.get_volume(source_id)
        if payload.get('id') != source_id:
            raise BookProviderError('Google Books kayıt kimliği doğrulanamadı.', 'invalid_response')
        return self.adapt(payload)

    def adapt(self, item):
        info = item.get('volumeInfo')
        if not isinstance(info,dict):
            info = {}
        title = info.get('title')
        title = title.strip() if isinstance(title,str) else ''
        authors = info.get('authors')
        author = ', '.join(name.strip() for name in authors if isinstance(name,str) and name.strip()) if isinstance(authors,list) else ''
        identifiers = info.get('industryIdentifiers')
        isbns = {}
        for identifier in identifiers if isinstance(identifiers,list) else []:
            if not isinstance(identifier,dict) or not isinstance(identifier.get('identifier'),str):
                continue
            value = normalize_isbn(identifier['identifier'])
            kind = identifier.get('type')
            if kind in ('ISBN_13','ISBN_10') and valid_isbn(value) and len(value)==(13 if kind=='ISBN_13' else 10):
                isbns[kind] = value
        isbn = isbns.get('ISBN_13',isbns.get('ISBN_10',''))
        links = info.get('imageLinks')
        thumbnail = safe_thumbnail(links.get('thumbnail') or links.get('smallThumbnail')) if isinstance(links,dict) else None
        date = clean_text(info.get('publishedDate'), 32)
        year = publication_year(date)
        return BookImportData(
            item['id'], title, author, isbn, thumbnail, import_warnings(title, author, isbn),
            clean_text(info.get('description'), 10000), clean_text(info.get('publisher'), 200),
            year, clean_text(info.get('language'), 50), date if year else '')
