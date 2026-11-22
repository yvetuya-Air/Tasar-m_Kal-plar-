"""Gerçek CSRF ve geçici SQLite ile kimlik doğrulama bütünleştirme testleri."""
from datetime import timedelta
import re
import pytest
from werkzeug.security import check_password_hash
from app import create_app
from database import get_db, init_db
from seed import seed_demo
from services.demo_accounts import prepare_demo_accounts, DEMO_ADMIN_PASSWORD, DEMO_MEMBER_PASSWORD


@pytest.fixture
def app(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'auth-test-only',
                      'DATABASE': str(tmp_path / 'auth.sqlite3')})
    with app.app_context():
        init_db()
        seed_demo(get_db())
        prepare_demo_accounts(get_db())
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def token(client, path='/giris'):
    response = client.get(path)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match, response.status_code
    return match.group(1).decode()


def login(client, username='demo_yonetici', password=DEMO_ADMIN_PASSWORD):
    return client.post('/giris', data={'username': username, 'password': password, 'csrf_token': token(client)})


@pytest.mark.parametrize('username,password,allowed,denied', [
    ('demo_yonetici',DEMO_ADMIN_PASSWORD,'/yonetim','/hesabim'),
    ('demo_uye',DEMO_MEMBER_PASSWORD,'/hesabim','/yonetim')])
def test_login_roles(client, username, password, allowed, denied):
    assert login(client, username, password).status_code == 302
    assert client.get('/panel').status_code == 200
    assert client.get(allowed).status_code == 200
    assert client.get(denied).status_code == 403


@pytest.mark.parametrize('username,password', [('demo_yonetici','wrong'),('missing','wrong'),('', ''),("' OR 1=1 --",'wrong'),('demo_uye',DEMO_ADMIN_PASSWORD)])
def test_invalid_login(client, username, password):
    response = login(client, username, password)
    assert response.status_code == 401
    assert 'Kullanıcı adı veya parola'.encode() in response.data
    with client.session_transaction() as session:
        assert 'user_id' not in session


@pytest.mark.parametrize('path', ['/panel','/yonetim','/hesabim'])
def test_anonymous_private_routes(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.location.endswith('/giris')


@pytest.mark.parametrize('supplied', [None, 'wrong'])
def test_login_csrf(client, supplied):
    token(client)
    data = {'username': 'demo_yonetici','password': DEMO_ADMIN_PASSWORD}
    if supplied is not None:
        data['csrf_token'] = supplied
    assert client.post('/giris', data=data).status_code == 400


def test_csrf_bound_to_browser(app, client):
    foreign_token = token(app.test_client())
    token(client)
    assert client.post('/giris', data={'csrf_token': foreign_token}).status_code == 400


def test_logout(client):
    login(client)
    csrf = token(client, '/panel')
    assert client.get('/cikis').status_code == 405
    assert client.post('/cikis').status_code == 400
    assert client.get('/panel').status_code == 200
    response = client.post('/cikis', data={'csrf_token': csrf}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Oturumunuz güvenle kapatıldı.'.encode() in response.data
    assert client.get('/panel').status_code == 302


def test_login_clears_session_and_rotates_csrf(client):
    old_token = token(client)
    with client.session_transaction() as session:
        session['untrusted_old_data'] = 'x'
    client.post('/giris', data={'csrf_token': old_token, 'username': 'demo_yonetici', 'password': DEMO_ADMIN_PASSWORD})
    with client.session_transaction() as session:
        assert 'untrusted_old_data' not in session
        assert session['_csrf_token'] != old_token
        assert 'password' not in session and 'role' not in session
    assert client.post('/cikis', data={'csrf_token': old_token}).status_code == 400


@pytest.mark.parametrize('table', ['users','members'])
def test_disabled_accounts(app, client, table):
    with app.app_context():
        with get_db() as db:
            db.execute(f'UPDATE {table} SET is_active=0 WHERE id=?', (2 if table=='users' else 1,))
    assert login(client, 'demo_uye', DEMO_MEMBER_PASSWORD).status_code == 401


def test_disable_during_session(app, client):
    login(client)
    with app.app_context():
        with get_db() as db:
            db.execute("UPDATE users SET is_active=0 WHERE username='demo_yonetici'")
    assert client.get('/panel').status_code == 302


def test_role_change_is_immediate(app, client):
    login(client)
    with app.app_context():
        with get_db() as db:
            db.execute("UPDATE users SET role='member' WHERE username='demo_yonetici'")
    assert client.get('/yonetim').status_code == 403


def test_member_sees_only_own_profile(client):
    login(client, 'demo_uye', DEMO_MEMBER_PASSWORD)
    response = client.get('/hesabim?member_id=2')
    assert 'Demo Öğrenci'.encode() in response.data
    assert 'ogretmen@example.invalid'.encode() not in response.data


def test_demo_hashes_and_repeat_safety(app):
    with app.app_context():
        db = get_db()
        hashes = dict(db.execute('SELECT username,password_hash FROM users').fetchall())
        assert check_password_hash(hashes['demo_yonetici'], DEMO_ADMIN_PASSWORD)
        assert check_password_hash(hashes['demo_uye'], DEMO_MEMBER_PASSWORD)
        assert hashes['demo_uye'] != DEMO_MEMBER_PASSWORD
        assert not prepare_demo_accounts(db)
        assert hashes == dict(db.execute('SELECT username,password_hash FROM users').fetchall())


def test_demo_refuses_unmarked_database(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path/'empty.sqlite3')})
    with app.app_context():
        init_db()
        with pytest.raises(ValueError):
            prepare_demo_accounts(get_db())
        assert get_db().execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0


def test_demo_cli(app):
    result = app.test_cli_runner().invoke(args=['demo-accounts'])
    assert result.exit_code == 0


def test_security_headers_and_cookie(client):
    response = client.get('/giris')
    cookie = response.headers['Set-Cookie']
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert "form-action 'self'" in response.headers['Content-Security-Policy']


def test_secure_cookie_setting(app):
    app.config['SESSION_COOKIE_SECURE'] = True
    response = app.test_client().get('/giris')
    assert 'Secure;' in response.headers['Set-Cookie']


def test_expired_session(app, client):
    login(client)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=-1)
    assert client.get('/panel').status_code == 302


def test_forged_session(client):
    client.set_cookie('session', 'forged.invalid.signature')
    assert client.get('/yonetim').status_code == 302


def test_safe_redirect_and_escaping(client):
    response = client.post('/giris?next=https://example.invalid', data={
        'csrf_token':token(client), 'username':'demo_yonetici', 'password':DEMO_ADMIN_PASSWORD})
    assert response.location == '/panel'
    assert client.get('/giris').location == '/panel'


def test_error_escapes_username(client):
    response = login(client, '<script>alert(1)</script>', 'wrong')
    assert b'<script>' not in response.data
    assert b'&lt;script&gt;' in response.data
