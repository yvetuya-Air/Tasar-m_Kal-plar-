"""Kitap CRUD, izinler, CSRF ve Factory Method/SQLite bütünleştirmesi."""
import re
import pytest
from app import create_app
from database import get_db, init_db
from models.book import Book, PhysicalBook, EBook
from seed import seed_demo
from services.demo_accounts import prepare_demo_accounts, DEMO_ADMIN_PASSWORD, DEMO_MEMBER_PASSWORD
from services import book_service
from patterns.factory_method import CREATORS, PhysicalBookCreator


@pytest.fixture
def app(tmp_path):
    app = create_app({'TESTING':True, 'SECRET_KEY':'books-test-only', 'DATABASE':str(tmp_path/'books.sqlite3')})
    with app.app_context():
        init_db()
        seed_demo(get_db())
        prepare_demo_accounts(get_db())
    return app


def csrf(client, path='/giris'):
    result = client.get(path)
    return re.search(rb'name="csrf_token" value="([^"]+)"',result.data).group(1).decode()


def signed_in(app, role='admin'):
    client = app.test_client()
    client.post('/giris', data={'csrf_token':csrf(client), 'username':'demo_yonetici' if role=='admin' else 'demo_uye',
                              'password':DEMO_ADMIN_PASSWORD if role=='admin' else DEMO_MEMBER_PASSWORD})
    return client


@pytest.fixture
def admin(app):
    return signed_in(app)


def form(**overrides):
    return {**{'title':'Yeni Kitap', 'author':'Deneme Yazarı', 'isbn':'978-0-306-40615-7',
               'category_id':'1', 'book_type':'physical', 'total_copies':'2',
               'shelf_location':'B-12','file_url':''}, **overrides}


def post(client, path, data):
    return client.post(path, data={**data, 'csrf_token':csrf(client, '/kitaplar')})


def test_create_edit_search_delete_lifecycle(app, admin):
    result = post(admin, '/kitaplar/ekle', form())
    assert result.status_code == 302
    with app.app_context():
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE isbn='9780306406157'").fetchone()
        book_id = row['id']
        assert isinstance(Book.from_row(row), PhysicalBook)
        assert db.execute("SELECT COUNT(*) FROM activity_logs WHERE action='book_created'").fetchone()[0] == 1
    assert 'Yeni Kitap'.encode() in admin.get('/kitaplar?q=Yeni').data
    assert 'Yeni Kitap'.encode() not in admin.get('/kitaplar?q=bulunamayan').data
    assert post(admin, f'/kitaplar/{book_id}/duzenle', form(title='Değişen Kitap')).status_code == 302
    assert 'Değişen Kitap'.encode() in admin.get('/kitaplar?q=Değişen').data
    assert admin.get(f'/kitaplar/{book_id}/sil').status_code == 200
    with app.app_context():
        assert book_service.get_book(book_id) is not None
    assert post(admin,f'/kitaplar/{book_id}/sil',{}).status_code == 302
    with app.app_context():
        assert book_service.get_book(book_id) is None
        assert get_db().execute("SELECT COUNT(*) FROM activity_logs WHERE action IN ('book_created','book_updated','book_deleted')").fetchone()[0] == 3


def test_ebook_creation_and_safe_type_change(app, admin):
    assert post(admin,'/kitaplar/ekle',form(book_type='ebook',shelf_location='',file_url='https://example.invalid/test.pdf')).status_code == 302
    with app.app_context():
        book_id = get_db().execute('SELECT MAX(id) FROM books').fetchone()[0]
        assert isinstance(book_service.get_book(book_id), EBook)
    assert post(admin,f'/kitaplar/{book_id}/duzenle',form()).status_code == 302
    with app.app_context():
        assert isinstance(book_service.get_book(book_id), PhysicalBook)


def test_service_really_calls_factory_method(app, monkeypatch):
    created = []
    class TrackingCreator(PhysicalBookCreator):
        def create_book(self, **data):
            created.append(data['title'])
            return super().create_book(**data)
    monkeypatch.setitem(CREATORS,'physical',TrackingCreator)
    with app.app_context():
        book = book_service.save_book(form(),1)
        assert created == ['Yeni Kitap']
        assert isinstance(book, PhysicalBook)


@pytest.mark.parametrize('changes', [
    {'title':''},{'title':' '*10},{'title':'x'*201},{'author':''},{'author':'x'*161},
    {'total_copies':'0'},{'total_copies':'-1'},{'total_copies':'1.5'},{'total_copies':'10001'},
    {'category_id':'999'},{'category_id':'oops'},{'isbn':'9780306406158'},{'isbn':'junk'},
    {'book_type':'unknown'},{'shelf_location':''},{'file_url':'https://example.invalid'},
    {'book_type':'ebook','shelf_location':'','file_url':'javascript:alert(1)'},
    {'book_type':'ebook','shelf_location':'','file_url':''}])
def test_server_validation_rolls_back(app, admin, changes):
    response = post(admin,'/kitaplar/ekle',form(**changes))
    assert response.status_code == 422
    assert b'role="alert"' in response.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM books').fetchone()[0] == 2
        assert get_db().execute("SELECT COUNT(*) FROM activity_logs WHERE action='book_created'").fetchone()[0] == 0


def test_duplicate_isbn(app, admin):
    assert post(admin,'/kitaplar/ekle',form()).status_code == 302
    response = post(admin,'/kitaplar/ekle',form(title='Başka'))
    assert response.status_code == 422
    assert 'Bu ISBN zaten kayıtlı.'.encode() in response.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM books').fetchone()[0] == 3


@pytest.mark.parametrize('book_id',[1,2])
def test_history_prevents_delete_and_type_change(app, admin, book_id):
    assert post(admin,f'/kitaplar/{book_id}/sil',{}).status_code == 409
    changes = form(book_type='ebook',shelf_location='',file_url='https://example.invalid/test.pdf') if book_id==1 else form()
    assert post(admin,f'/kitaplar/{book_id}/duzenle',changes).status_code == 422
    with app.app_context():
        assert book_service.get_book(book_id) is not None


def test_stock_reduction_rejected(app, admin):
    with app.app_context():
        with get_db() as db:
            for member_id in (1,2):
                db.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(2,?,'2026-11-01','2026-11-20')",(member_id,))
    result = post(admin,'/kitaplar/2/duzenle',form(book_type='ebook',total_copies='1',shelf_location='',file_url='https://example.invalid/test.pdf'))
    assert result.status_code == 422
    with app.app_context():
        assert book_service.get_book(2).total_copies == 2


@pytest.mark.parametrize('path', ['/kitaplar/ekle','/kitaplar/1/duzenle','/kitaplar/1/sil'])
def test_member_cannot_mutate(app, path):
    member = signed_in(app,'member')
    assert member.get('/kitaplar').status_code == 200
    assert member.get(path).status_code == 403
    assert post(member,path,form()).status_code == 403
    assert b'Kitap ekle' not in member.get('/kitaplar').data


@pytest.mark.parametrize('path', ['/kitaplar','/kitaplar/ekle','/kitaplar/1/duzenle','/kitaplar/1/sil'])
def test_anonymous_cannot_access(app, path):
    assert app.test_client().get(path).status_code == 302


@pytest.mark.parametrize('path',['/kitaplar/ekle','/kitaplar/1/duzenle','/kitaplar/1/sil'])
def test_csrf_required(admin, path):
    assert admin.post(path,data=form()).status_code == 400


@pytest.mark.parametrize('path',['/kitaplar/999/duzenle','/kitaplar/999/sil'])
def test_missing_book(admin, path):
    assert admin.get(path).status_code == 404
    assert post(admin,path,form()).status_code == 404


def test_turkish_search_and_literal_wildcards(app, admin):
    post(admin,'/kitaplar/ekle',form(title='IŞIK ve İLETİŞİM %_',isbn=''))
    assert 'IŞIK ve İLETİŞİM'.encode() in admin.get('/kitaplar',query_string={'q':'ışık'}).data
    assert 'IŞIK ve İLETİŞİM'.encode() in admin.get('/kitaplar',query_string={'q':'iletişim'}).data
    assert 'IŞIK ve İLETİŞİM'.encode() in admin.get('/kitaplar',query_string={'q':'%_'}).data
    assert 'Demo Fiziksel'.encode() not in admin.get('/kitaplar',query_string={'q':'%_'}).data
    assert admin.get('/kitaplar',query_string={'q':'x'*201}).status_code == 400


def test_pagination(app, admin):
    with app.app_context():
        for index in range(21):
            book_service.save_book(form(title=f'Sayfa Kitabı {index}',isbn=''),1)
    assert b'1 / 2' in admin.get('/kitaplar').data
    assert b'2 / 2' in admin.get('/kitaplar?page=2').data
    assert admin.get('/kitaplar?page=oops').status_code == 200


def test_isbn10_and_xss_escaping(admin):
    assert post(admin,'/kitaplar/ekle',form(title='<script>alert(1)</script>',isbn='0-8044-2957-X')).status_code == 302
    response = admin.get('/kitaplar')
    assert b'<script>alert(1)</script>' not in response.data
    assert b'&lt;script&gt;' in response.data
