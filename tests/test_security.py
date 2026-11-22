"""Aşama 10: parola, oturum, SQL, XSS ve hatalı girdi regresyonları."""
import re
from pathlib import Path
import sqlite3
from unittest.mock import Mock
import pytest
import requests
from werkzeug.security import generate_password_hash,check_password_hash
from app import create_app
from database import get_db,init_db
from seed import seed_demo
from services.demo_accounts import prepare_demo_accounts,DEMO_ADMIN_PASSWORD,DEMO_MEMBER_PASSWORD
from models.book import EBook,PhysicalBook
from patterns.adapter import safe_thumbnail
from services import member_service


@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'security-only','DATABASE':str(tmp_path/'security.sqlite3')})
    with app.app_context():
        init_db()
        seed_demo(get_db())
        prepare_demo_accounts(get_db())
    return app


def csrf(client,path='/giris'):
    return re.search(rb'name="csrf_token" value="([^"]+)"',client.get(path).data).group(1).decode()


def login(client,member=False):
    result=client.post('/giris',data={'csrf_token':csrf(client),'username':'demo_uye' if member else 'demo_yonetici',
                                    'password':DEMO_MEMBER_PASSWORD if member else DEMO_ADMIN_PASSWORD})
    assert result.status_code==302
    return client


@pytest.fixture
def admin(app):
    return login(app.test_client())


def test_salted_password_hashes():
    """Aynı parolanın farklı tuzlarla hashlenmesi ve doğru/yanlış doğrulama."""
    first=generate_password_hash('TestPassword!2026')
    second=generate_password_hash('TestPassword!2026')
    assert first!=second and first!='TestPassword!2026'
    assert check_password_hash(first,'TestPassword!2026')
    assert not check_password_hash(first,'wrong')


@pytest.mark.parametrize('bad_hash',['unknown$salt$hash','pbkdf2:sha256:bad$salt$hash','scrypt:bad$salt$hash','plaintext'])
def test_corrupt_password_hash_fails_closed(app,bad_hash):
    """Bozuk hash bulunan hesapla giriş 500 yerine genel 401 döndürmelidir."""
    with app.app_context():
        with get_db() as db:
            db.execute('UPDATE users SET password_hash=? WHERE id=1',(bad_hash,))
    client=app.test_client()
    result=client.post('/giris',data={'csrf_token':csrf(client),'username':'demo_yonetici','password':'test'})
    assert result.status_code==401
    assert bad_hash.encode() not in result.data
    assert client.get('/panel').status_code==302


def test_logout_revokes_copied_signed_cookie(app,admin):
    """Çıkış öncesi kopyalanmış geçerli çerez sonradan tekrar kullanılamamalıdır."""
    stolen=admin.get_cookie('session').value
    other=app.test_client()
    other.set_cookie('session',stolen)
    assert other.get('/panel').status_code==200
    assert admin.post('/cikis',data={'csrf_token':csrf(admin,'/panel')}).status_code==302
    other.set_cookie('session',stolen)
    assert other.get('/panel').status_code==302
    assert login(app.test_client()).get('/panel').status_code==200


def test_deactivate_reactivate_does_not_revive_old_cookie(app,admin):
    """Üyelik pasifleştirilip açılınca eski kopya oturum yeniden canlanmamalıdır."""
    member=login(app.test_client(),member=True)
    old_cookie=member.get_cookie('session').value
    with app.app_context():
        member_service.set_active(1,False,1)
        member_service.set_active(1,True,1)
    attacker=app.test_client()
    attacker.set_cookie('session',old_cookie)
    assert attacker.get('/panel').status_code==302
    assert login(app.test_client(),member=True).get('/panel').status_code==200


def test_pre_migration_cookie_is_rejected(app,admin):
    """Oturum sürümü bulunmayan eski çerez güvenli biçimde girişe yönlenmelidir."""
    with admin.session_transaction() as session:
        session.pop('session_version')
    assert admin.get('/panel').status_code==302


@pytest.mark.parametrize('field,value',[('user_id',999),('session_version',999),('role','admin')])
def test_session_fields_cannot_elevate_member(app,field,value):
    """Testte imzalı içerik değiştirilse bile kullanıcı/rol/sürüm SQL ile denetlenir."""
    member=login(app.test_client(),member=True)
    with member.session_transaction() as session:
        session[field]=value
    expected=403 if field=='role' else 302
    assert member.get('/yonetim').status_code==expected


@pytest.mark.parametrize('path',['/kitaplar','/uyeler','/rezervasyonlar'])
@pytest.mark.parametrize('payload',["' OR 1=1 --", "'; DROP TABLE books; --", '%_\\'])
def test_sql_injection_search_is_literal(app,admin,path,payload):
    """SQL saldırı metni arama olarak işlenmeli; tablolar ve satırlar değişmemelidir."""
    result=admin.get(path,query_string={'q':payload})
    assert result.status_code==200
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM books').fetchone()[0]==2
        assert get_db().execute('SELECT COUNT(*) FROM members').fetchone()[0]==3
    if path in ('/kitaplar','/uyeler'):
        assert 'Demo Fiziksel Kitap'.encode() not in result.data
        assert 'Demo Öğretmen'.encode() not in result.data


def test_sql_injection_write_stores_text_without_executing(app,admin):
    """Kitap alanındaki SQL metni veri olarak saklanmalı, sorgu olarak çalışmamalıdır."""
    payload="'; DROP TABLE members; --"
    result=admin.post('/kitaplar/ekle',data={'csrf_token':csrf(admin,'/panel'),'title':payload,'author':'Test',
                                          'book_type':'physical','total_copies':'1','shelf_location':'A-10'})
    assert result.status_code==302
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM members').fetchone()[0]==3
        assert get_db().execute('SELECT title FROM books ORDER BY id DESC').fetchone()[0]==payload


@pytest.mark.parametrize('payload',['<script>window.__xss=1</script>','<img src=x onerror="window.__xss=1">','"><svg onload=alert(1)>'])
def test_stored_xss_escaped_in_catalog_edit_and_dashboard(admin,payload):
    """Kaydedilmiş zararlı HTML katalog, form ve günlükte düz metin kalmalıdır."""
    assert admin.post('/kitaplar/ekle',data={'csrf_token':csrf(admin,'/panel'),'title':payload,'author':payload,
                                           'book_type':'physical','total_copies':'1','shelf_location':'A-10'}).status_code==302
    for path in ('/kitaplar','/panel'):
        page=admin.get(path)
        assert page.status_code==200
        assert payload.encode() not in page.data
        assert b'&lt;' in page.data


@pytest.mark.parametrize('path',['/kitaplar','/uyeler'])
def test_reflected_xss_in_search_is_escaped(admin,path):
    """Arama girdisi HTML özniteliğini kapatarak script oluşturamamalıdır."""
    payload='"><img src=x onerror=alert(1)>'
    result=admin.get(path,query_string={'q':payload})
    assert result.status_code==200 and payload.encode() not in result.data
    assert b'&lt;img' in result.data


@pytest.mark.parametrize('character',['\x00','\x01','\x1f','\x7f','\\'])
def test_control_characters_rejected_in_ebook_and_cover(character):
    """URL ayrıştırıcısının kabul ettiği kontrol karakterleri ürün/kapakta reddedilir."""
    url='https://books.google.com/book'+character+'path'
    book=EBook(id=None,title='T',author='A',isbn=None,category_id=None,book_type='ebook',total_copies=1,shelf_location=None,file_url=url,created_at='')
    with pytest.raises(ValueError): book.validate_details()
    assert safe_thumbnail(url) is None


def test_empty_url_userinfo_rejected():
    """Boş kullanıcı bilgisi taşıyan URL de dosya ve kapak adresi olamaz."""
    url='https://@books.google.com/book'
    assert safe_thumbnail(url) is None
    book=EBook(id=None,title='T',author='A',isbn=None,category_id=None,book_type='ebook',total_copies=1,shelf_location=None,file_url=url,created_at='')
    with pytest.raises(ValueError): book.validate_details()


def test_wrong_typed_physical_details_have_validation_error():
    """Rafın yanlış Python türü ürün doğrulamasında anlaşılır hata vermelidir."""
    book=PhysicalBook(id=None,title='T',author='A',isbn=None,category_id=None,book_type='physical',total_copies=1,shelf_location=42,file_url=None,created_at='')
    with pytest.raises(ValueError): book.validate_details()


def test_csrf_header_and_cross_session(app,admin):
    """Geçerli başlık jetonu kabul edilir; başka oturumun jetonu reddedilir."""
    other=login(app.test_client(),member=True)
    foreign=csrf(other,'/panel')
    assert admin.post('/cikis',headers={'X-CSRF-Token':foreign}).status_code==400
    assert admin.get('/panel').status_code==200
    assert admin.post('/cikis',headers={'X-CSRF-Token':csrf(admin,'/panel')}).status_code==302


def test_real_http_is_blocked_in_automated_tests():
    """Test yalıtımı, taklit edilmeyen gerçek dış isteği durdurmalıdır."""
    with pytest.raises(AssertionError,match='HTTP'):
        requests.get('https://www.googleapis.com/books/v1/volumes',timeout=1)


def test_existing_database_session_migration_preserves_records(tmp_path):
    """Eski users tablosuna sürüm sütunu eklenir; hesap ve hash aynen korunur."""
    path=tmp_path/'legacy.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        db.execute("INSERT INTO users(username,password_hash,role) VALUES('legacy','old-hash','member')")
    app=create_app({'TESTING':True,'DATABASE':str(path)})
    with app.app_context():
        init_db()
        row=get_db().execute('SELECT * FROM users').fetchone()
        assert row['username']=='legacy' and row['password_hash']=='old-hash' and row['session_version']==0
        init_db()
        assert get_db().execute('SELECT COUNT(*) FROM users').fetchone()[0]==1
