"""Aşama 13 katalog kaynakları, önbellek ve veri geçişi."""
import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from app import create_app
from database import get_db, init_db
from models.book import Book
from patterns.open_library_adapter import OpenLibraryAdapter
from services.catalog_cache import CatalogCache
from services.google_books_api import BookProviderError
from services.open_library_api import OpenLibraryAPI
from test_adapter import app, csrf, fake_http, login, response, volume


ISBN = '9780140328721'
WORK_ID = 'OL123W'


def open_response():
    return {'numFound': 1, 'docs': [{
        'key': f'/works/{WORK_ID}', 'title': 'Örnek eser',
        'author_name': ['Örnek yazar'], 'cover_i': 115,
        'editions': {'docs': [{
            'title': 'Örnek baskı', 'isbn': [ISBN], 'publisher': ['Örnek yayınevi'],
            'publish_year': [1988], 'language': ['eng'],
        }]},
    }]}


@pytest.mark.parametrize(('values', 'query'), [
    ({'title': 'Kitap'}, 'title:"Kitap"'),
    ({'author': 'Yazar'}, 'author:"Yazar"'),
    ({'isbn': '978-0140328721'}, f'isbn:"{ISBN}"'),
])
def test_open_library_queries(values, query):
    http = Mock()
    http.get.return_value = response(dict(open_response(), numFound=40))
    page = OpenLibraryAdapter(OpenLibraryAPI(http)).search_page(**values, page=2)
    url, = http.get.call_args.args
    options = http.get.call_args.kwargs
    assert url == 'https://openlibrary.org/search.json'
    assert options['params']['q'] == query
    assert options['params']['page'] == 2
    assert options['params']['limit'] == 12
    assert options['allow_redirects'] is False
    assert page.has_next and page.books[0].title == 'Örnek baskı'


@pytest.mark.parametrize('payload', [{}, {'docs': [None]}, {'docs': [], 'numFound': 5}])
def test_open_library_malformed_results(payload):
    http = Mock()
    http.get.return_value = response(payload)
    with pytest.raises(BookProviderError, match='Open Library') as problem:
        OpenLibraryAdapter(OpenLibraryAPI(http)).search_books(title='Kitap')
    assert problem.value.kind == 'invalid_response'


def test_invalid_open_library_key_never_calls_network():
    http = Mock()
    with pytest.raises(BookProviderError) as problem:
        OpenLibraryAdapter(OpenLibraryAPI(http)).get_book('../private')
    assert problem.value.kind == 'invalid_id'
    http.get.assert_not_called()


def test_google_pagination_and_normalized_cache(app, fake_http):
    fake_http.get.return_value = response({'items': [volume()], 'totalItems': 30})
    fake_http.get.side_effect = None
    client = login(app)
    data = {'csrf_token': csrf(client, '/kitaplar/google'), 'title': 'Kitap'}
    first = client.post('/kitaplar/google', data=data)
    assert b'name="page" value="2"' in first.data
    second = client.post('/kitaplar/google', data={**data, 'page': '2'})
    assert b'Sayfa 2' in second.data
    assert [call.kwargs['params']['startIndex'] for call in fake_http.get.call_args_list] == [0, 12]
    again = client.post('/kitaplar/google', data={**data, 'title': '  Kitap  ', 'page': '2'})
    assert again.status_code == 200 and fake_http.get.call_count == 2


def test_open_library_timeout_falls_back_to_google(app, fake_http, monkeypatch):
    http = Mock(side_effect=requests.Timeout('özel bağlantı bilgisi'))
    monkeypatch.setattr(requests, 'get', http)
    client = login(app)
    data = {'csrf_token': csrf(client, '/kitap-kesfet'), 'title': 'Kitap',
            'source': 'open_library', 'page': '2'}
    result = client.post('/kitap-kesfet', data=data)
    assert result.status_code == 200
    assert 'Google Books sonuçları gösteriliyor'.encode() in result.data
    assert 'Kaynak · Google Books'.encode() in result.data
    assert 'özel bağlantı bilgisi'.encode() not in result.data
    assert fake_http.get.call_args.kwargs['params']['startIndex'] == 0


@pytest.mark.parametrize('role', ['admin', 'member'])
def test_discovery_details_and_import_role(app, fake_http, role):
    item = volume()
    item['volumeInfo'].update(publishedDate='1988-10-15', description='Ayrıntılı açıklama')
    fake_http.get.side_effect = lambda url, **kwargs: response(
        {'items': [item], 'totalItems': 1} if url.endswith('/volumes') else item
    )
    client = login(app, role)
    assert b'/kitap-kesfet' in client.get('/kitaplar').data
    token = csrf(client, '/kitap-kesfet')
    search = client.post('/kitap-kesfet', data={'csrf_token': token, 'title': 'Kitap'})
    assert b'1988-10-15' in search.data
    assert b'/kitap-kesfet/ayrinti' in search.data
    data = {'csrf_token': token, 'source_id': item['id']}
    detail = client.post('/kitap-kesfet/ayrinti', data=data)
    assert detail.status_code == 200 and 'Ayrıntılı açıklama'.encode() in detail.data
    assert (b'/kitaplar/google/aktar' in detail.data) == (role == 'admin')
    assert client.post('/kitaplar/google/aktar', data=data).status_code == (200 if role == 'admin' else 403)
    assert fake_http.get.call_count == 2


def test_quota_fallback_import_persists_metadata(app, fake_http, monkeypatch):
    fake_http.get.return_value = response({}, 429)
    fake_http.get.side_effect = None
    http = Mock()
    http.get.side_effect = lambda url, **kwargs: response(
        open_response() if url.endswith('/search.json') else
        {'key': f'/works/{WORK_ID}', 'description': {'value': '<script>Örnek açıklama</script>'}}
    )
    monkeypatch.setattr(requests, 'get', http.get)
    client = login(app)
    token = csrf(client, '/kitaplar/google')
    data = {'csrf_token': token, 'isbn': ISBN, 'page': '2'}
    search = client.post('/kitaplar/google', data=data)
    assert search.status_code == 200
    assert 'Open Library sonuçları'.encode() in search.data
    assert http.get.call_args.kwargs['params']['page'] == 1
    assert b'name="source" value="open_library"' in search.data
    assert f'{WORK_ID}:{ISBN}'.encode() in search.data
    client.post('/kitaplar/google', data={**data, 'isbn': '', 'title': 'Başka kitap'})
    assert fake_http.get.call_count == 1

    preview_data = {'csrf_token': token, 'source': 'open_library', 'source_id': f'{WORK_ID}:{ISBN}'}
    preview = client.post('/kitaplar/google/aktar', data=preview_data)
    assert preview.status_code == 200
    assert b'&lt;script&gt;' in preview.data
    assert 'Örnek yayınevi'.encode() in preview.data
    assert 'covers.openlibrary.org' in preview.headers['Content-Security-Policy']
    client.post('/kitaplar/google/aktar', data=preview_data)
    assert http.get.call_count == 4

    from test_integration import parsed
    form = next(form for form in parsed(preview).forms if form['action'] == '/kitaplar/ekle')
    saved = client.post(form['action'], data={
        **form['inputs'], 'csrf_token': token, 'book_type': 'physical',
        'shelf_location': 'A1', 'category_id': '', 'description': '<script>Örnek açıklama</script>',
    })
    assert saved.status_code == 302
    with app.app_context():
        book = Book.from_row(get_db().execute('SELECT * FROM books WHERE isbn=?', (ISBN,)).fetchone())
        assert book.cover_url == 'https://covers.openlibrary.org/b/id/115-M.jpg?default=false'
        assert book.description == '<script>Örnek açıklama</script>'
        assert (book.publisher, book.publication_year, book.language) == ('Örnek yayınevi', 1988, 'eng')
    assert b'&lt;script&gt;' in client.get('/kitaplar').data


def test_cache_expiry_eviction_and_retry_delay():
    now = Mock(return_value=10)
    fetch = Mock(return_value='sonuç')
    cache = CatalogCache(ttl=30, capacity=1, clock=now)
    assert cache.load('a', fetch) == cache.load('a', fetch)
    assert fetch.call_count == 1
    cache.load('b', fetch)
    cache.load('a', fetch)
    assert fetch.call_count == 3
    now.return_value = 41
    fetch.side_effect = BookProviderError('Kota', 'quota', 75)
    for _ in range(2):
        with pytest.raises(BookProviderError):
            cache.load('a', fetch)
    assert fetch.call_count == 4
    now.return_value = 116
    fetch.side_effect = None
    assert cache.load('a', fetch) == 'sonuç'


def test_v1_migration_preserves_book_inventory_and_history(tmp_path):
    path = tmp_path / 'v1.sqlite3'
    schema = Path(__file__).resolve().parents[1].joinpath('schema.sql').read_text(encoding='utf-8')
    old_schema = schema.replace(
        ' cover_url TEXT, description TEXT, publisher TEXT, publication_year INTEGER, language TEXT,\n', ''
    )
    with sqlite3.connect(path) as connection:
        connection.executescript(old_schema)
        connection.execute("INSERT INTO books(id,title,author,book_type,shelf_location) VALUES(7,'Eski','Yazar','physical','A1')")
        connection.execute("INSERT INTO members(id,full_name,email,member_type) VALUES(3,'Üye','uye@example.test','student')")
        connection.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(7,3,'2026-11-01','2026-11-10')")
    application = create_app({'TESTING': True, 'DATABASE': str(path)})
    with application.app_context():
        assert 'cover_url' not in [column['name'] for column in get_db().execute('PRAGMA table_info(books)')]
        init_db()
        init_db()
        db = get_db()
        row = db.execute('SELECT * FROM book_inventory WHERE id=7').fetchone()
        book = Book.from_row(row)
        assert book.title == 'Eski' and book.cover_url is None and row['available_copies'] == 0
        assert db.execute('SELECT book_id, member_id FROM loans').fetchone()[:] == (7, 3)
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
