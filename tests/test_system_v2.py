"""Giriş sınırı, tek kullanımlık sıfırlama ve gerçek SQLite geri yükleme."""
from pathlib import Path

from database import get_db
from services.backups import restore_backup, write_backup
from test_adapter import app, csrf, login
from test_digital import upload, wav_bytes


def test_rate_limits_and_redacts_credentials(app):
    client = app.test_client()
    token = csrf(client)
    for _ in range(8):
        assert client.post('/giris', data={'csrf_token': token, 'username': 'demo_uye', 'password': 'yanlis-parola'}).status_code == 401
    assert client.post('/giris', data={'csrf_token': token, 'username': 'demo_uye', 'password': 'yanlis-parola'}).status_code == 429
    admin = login(app)
    assert b'yanlis-parola' not in admin.get('/islem-gecmisi').data


def test_reset_consumed_once_and_revokes_sessions(app):
    member = login(app, 'member')
    isolated = app.test_client()
    result = app.test_cli_runner().invoke(args=['issue-password-reset', 'demo_uye'])
    assert result.exit_code == 0
    reset_token = result.output.strip()
    token = csrf(isolated, '/parola-sifirla')
    data = {'token': reset_token, 'password': 'Yeni-Parola44', 'confirmation': 'Yeni-Parola44'}
    assert isolated.post('/parola-sifirla', data={**data, 'csrf_token': token}).status_code == 302
    assert member.get('/panel').status_code == 302
    assert isolated.post('/parola-sifirla', data={**data, 'csrf_token': csrf(isolated, '/parola-sifirla')}).status_code == 422


def test_backup_roundtrip_and_access(app):
    expected = Path(app.config['DATABASE'])
    stored = expected.with_name('verified.sqlite3')
    admin = login(app)
    sample = wav_bytes()
    assert upload(admin, 'yedek.wav', sample, 'audio').status_code == 302
    downloaded = admin.get('/ayarlar/yedek')
    assert downloaded.data.startswith(b'SQLite format 3')
    downloaded.close()
    assert login(app, 'member').get('/ayarlar/yedek').status_code == 403
    write_backup(expected, stored)
    with app.app_context(), get_db() as db:
        db.execute("UPDATE books SET title='Değişiklik' WHERE id=1")
    previous = restore_backup(expected, stored)
    assert previous.is_file()
    assert admin.get('/panel').status_code == 302
    with app.app_context():
        assert get_db().execute('SELECT title FROM books WHERE id=1').fetchone()[0] != 'Değişiklik'
        assert get_db().execute("SELECT content FROM book_media WHERE mime='audio/wav'").fetchone()[0] == sample
