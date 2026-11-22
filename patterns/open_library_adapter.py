"""Open Library eserlerini ve baskılarını ortak kitap biçimine dönüştürür."""
from dataclasses import replace

from models.isbn import isbn_variants, normalize_isbn, valid_isbn
from patterns.adapter import (
    PAGE_SIZE, BookDataProvider, BookImportData, BookProviderError, BookSearchPage,
    clean_text, import_warnings, publication_year, search_fields,
)
from services.open_library_api import OpenLibraryAPI, WORK_ID


def records(value):
    return value if isinstance(value, list) else []


def first_text(values, limit):
    return next((value for item in records(values) if (value := clean_text(item, limit))), '')


def cover_url(cover_id):
    if type(cover_id) is int and 0 < cover_id < 10**12:
        return f'https://covers.openlibrary.org/b/id/{cover_id}-M.jpg?default=false'


def work_id_from(doc):
    key = doc.get('key')
    if isinstance(key, str):
        work_id = key.removeprefix('/works/')
        if WORK_ID.fullmatch(work_id):
            return work_id


def phrase(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


class OpenLibraryAdapter(BookDataProvider):
    def __init__(self, api: OpenLibraryAPI):
        self.api = api

    def search_books(self, *, title='', author='', isbn=''):
        return list(self.search_page(title=title, author=author, isbn=isbn).books)

    def search_page(self, *, title='', author='', isbn='', page=1):
        title, author, isbn = search_fields(title, author, isbn)
        terms = [f'{field}:{phrase(value)}' for field, value in
                 (('title', title), ('author', author), ('isbn', isbn)) if value]
        return self._search(' AND '.join(terms), page, isbn)

    def _search(self, query, page, isbn):
        payload = self.api.search_works(query, page=page, limit=PAGE_SIZE)
        docs = payload.get('docs')
        total = payload.get('numFound', payload.get('num_found'))
        if not isinstance(docs, list) or (not docs and type(total) is int and total > (page - 1) * PAGE_SIZE):
            raise BookProviderError('Open Library sonuç listesi eksik.', 'invalid_response')
        books = {}
        for doc in docs[:PAGE_SIZE]:
            work_id = work_id_from(doc) if isinstance(doc, dict) else None
            if work_id and work_id not in books:
                books[work_id] = self.adapt(work_id, doc, isbn)
        if docs and not books:
            raise BookProviderError('Open Library kullanılabilir bir kitap kaydı döndürmedi.', 'invalid_response')
        has_next = bool(docs) and (total > page * PAGE_SIZE if type(total) is int else len(docs) >= PAGE_SIZE)
        return BookSearchPage(tuple(books.values()), has_next)

    def adapt(self, work_id, doc, requested_isbn=''):
        editions = doc.get('editions')
        candidates = records(editions.get('docs')) if isinstance(editions, dict) else []
        edition = next((item for item in candidates if isinstance(item, dict)), {})
        edition_isbns = [normalize_isbn(value) for value in records(edition.get('isbn')) if isinstance(value, str)]
        if requested_isbn and not set(isbn_variants(requested_isbn)).intersection(edition_isbns):
            # Arama eseri bulsa bile başka bir baskının alanlarını ISBN ile birleştirme.
            edition, edition_isbns = {}, []
        isbn = requested_isbn or next(iter(sorted(filter(valid_isbn, edition_isbns), key=len, reverse=True)), '')
        title = clean_text(edition.get('title'), 1000) or clean_text(doc.get('title'), 1000)
        author = ', '.join(name for value in records(doc.get('author_name'))
                           if (name := clean_text(value, 160)))
        thumbnail = cover_url(edition.get('cover_i')) or cover_url(doc.get('cover_i'))
        years = records(edition.get('publish_year'))
        year = publication_year(years[0] if years else doc.get('first_publish_year'))
        source_id = f'{work_id}:{requested_isbn}' if requested_isbn else work_id
        return BookImportData(source_id, title, author, isbn, thumbnail,
                              import_warnings(title, author, isbn),
                              publisher=first_text(edition.get('publisher'), 200),
                              publication_year=year, language=first_text(edition.get('language'), 50))

    def get_book(self, source_id):
        work_id, separator, isbn = source_id.partition(':')
        if not WORK_ID.fullmatch(work_id) or (separator and not valid_isbn(isbn)):
            raise BookProviderError('Geçersiz Open Library kayıt kimliği.', 'invalid_id')
        query = f'key:{phrase(f"/works/{work_id}")}' + (f' AND isbn:{phrase(isbn)}' if isbn else '')
        page = self._search(query, 1, isbn)
        draft = next((book for book in page.books if book.source_id == source_id), None)
        if draft is None:
            raise BookProviderError('Seçilen Open Library kaydı bulunamadı.', 'not_found')
        work = self.api.get_work(work_id)
        if work_id_from(work) != work_id:
            raise BookProviderError('Open Library kayıt kimliği doğrulanamadı.', 'invalid_response')
        description = work.get('description')
        if isinstance(description, dict):
            description = description.get('value')
        covers = records(work.get('covers'))
        thumbnail = draft.thumbnail or next((url for cover in covers if (url := cover_url(cover))), None)
        return replace(draft, description=clean_text(description, 10000), thumbnail=thumbnail)
