"""Dijital yükleme, okuyucu, izinler ve ilerleme regresyonları."""
import io
import wave

import pypdfium2 as pdfium
import pytest

from database import get_db
from models.book import AudioBook, Book
from test_adapter import app, csrf, login


def pdf_bytes():
    output = io.BytesIO()
    with pdfium.PdfDocument.new() as document:
        for _ in range(2):
            document.new_page(200, 300).close()
        document.save(output)
    return output.getvalue()


def wav_bytes():
    output = io.BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
        stream.writeframes(b'\x00\x00' * 16000)
    return output.getvalue()


def upload(client, filename, content, kind, rights='yes'):
    return client.post('/kitaplar/ekle', data={
        'csrf_token': csrf(client, '/kitaplar/ekle'), 'title': 'Dijital deneme',
        'author': 'Yazar', 'book_type': kind, 'total_copies': '1',
        'rights': rights, 'media': (io.BytesIO(content), filename),
    })


def test_pdf_access_progress_bookmarks_and_resume(app):
    administrator = login(app)
    member = login(app, 'member')
    assert upload(administrator, 'kitap.pdf', pdf_bytes(), 'ebook').status_code == 302
    with app.app_context():
        db = get_db()
        book = db.execute("SELECT id FROM books WHERE title='Dijital deneme'").fetchone()['id']
        member_id = db.execute('SELECT id FROM members WHERE user_id IS NOT NULL').fetchone()['id']
    base = f'/dijital-kutuphane/{book}'
    assert member.get(f'{base}/sayfa/1').status_code == 403
    assert administrator.get(f'{base}/sayfa/1').data.startswith(b'\xff\xd8')
    with app.app_context(), get_db() as db:
        db.execute('INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(?,?,?,?)',
                   (book, member_id, '2026-11-01', '2026-11-30'))
    token = csrf(member, '/dijital-kutuphane')
    assert member.post(f'{base}/ilerleme', data={'csrf_token': token, 'position': '2'}).status_code == 204
    assert member.post(f'{base}/ilerleme', data={'csrf_token': token, 'position': 'nan'}).status_code == 422
    assert member.post(f'{base}/ayrac', data={'csrf_token': token, 'page': '2', 'marked': 'yes'}).status_code == 204
    assert b'data-position="2.0"' in member.get(f'{base}/oku').data
    assert b'<option value="2">2</option>' in member.get(f'{base}/oku').data
    assert b'<option value="2">2</option>' not in administrator.get(f'{base}/oku').data


def test_audio_factory_and_byte_ranges(app):
    client = login(app)
    assert upload(client, 'ses.wav', wav_bytes(), 'audio').status_code == 302
    with app.app_context():
        book = Book.from_row(get_db().execute("SELECT * FROM books WHERE book_type='audio'").fetchone())
    assert isinstance(book, AudioBook) and book.managed_media
    base = f'/dijital-kutuphane/{book.id}'
    stream = client.get(f'{base}/ses', headers={'Range': 'bytes=0-11'})
    assert stream.status_code == 206 and stream.data.startswith(b'RIFF')
    assert 'no-store' in stream.headers['Cache-Control']
    assert b'<audio' in client.get(f'{base}/oku').data
    assert client.post(f'{base}/ilerleme', data={
        'csrf_token': csrf(client, '/dijital-kutuphane'), 'position': '1.5',
    }).status_code == 204
    assert b'data-position="1.5"' in client.get(f'{base}/oku').data


@pytest.mark.parametrize(('filename', 'kind', 'content', 'rights'), [
    ('kitap.pdf', 'ebook', lambda: b'%PDF-invalid', 'yes'),
    ('kitap.pdf', 'ebook', pdf_bytes, ''),
    ('ses.mp3', 'audio', wav_bytes, 'yes'),
    ('ses.wav', 'physical', wav_bytes, 'yes'),
])
def test_invalid_upload_does_not_create_book(app, filename, kind, content, rights):
    assert upload(login(app), filename, content(), kind, rights).status_code == 422
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM books WHERE title='Dijital deneme'").fetchone()[0] == 0


def test_seed_repairs_legacy_demo_link_without_replacing_book(app):
    from seed import seed_demo

    with app.app_context(), get_db() as db:
        db.execute('DELETE FROM book_media WHERE book_id=2')
        db.execute("UPDATE books SET managed_media=0,file_url='https://example.invalid/demo.pdf' WHERE id=2")
    with app.app_context():
        assert seed_demo(get_db()) is False
        assert seed_demo(get_db()) is False
    client = login(app)
    assert b'example.invalid/demo.pdf' not in client.get('/dijital-kutuphane').data
    assert client.get('/dijital-kutuphane/2/sayfa/1').data.startswith(b'\xff\xd8')
    assert client.get('/dijital-kutuphane/2/sayfa/2').data.startswith(b'\xff\xd8')


def test_demo_member_can_resume_search_and_loses_access_after_return(app):
    runner = app.test_cli_runner()
    first = runner.invoke(args=['demo-reading'])
    second = runner.invoke(args=['demo-reading'])
    assert first.exit_code == second.exit_code == 0 and first.output == second.output
    member = login(app, 'member')
    admin = login(app)
    reader = '/dijital-kutuphane/2/oku'
    token = csrf(member, reader)
    assert member.post('/dijital-kutuphane/2/ilerleme', data={'csrf_token': token, 'position': '2'}).status_code == 204
    assert member.post('/dijital-kutuphane/2/ayrac', data={'csrf_token': token, 'page': '2', 'marked': 'yes'}).status_code == 204
    assert 'Kaldığın yerden devam et'.encode() in member.get('/kitaplarim').data
    assert b'data-position="2.0"' in member.get(reader).data
    result = member.get(reader, query_string={'mode': 'text', 'q': 'belgesi - sayfa 2'})
    assert result.status_code == 200 and b'Deneme PDF belgesi - Sayfa 2' in result.data
    assert b'page=2' in result.data and b'page=1' in result.data
    loan = int(first.output.strip().rsplit('#', 1)[1])
    return_url = f'/odunc/{loan}/iade'
    assert admin.post(return_url, data={'csrf_token': csrf(admin, return_url)}).status_code == 302
    assert member.get(reader + '?mode=text&q=Deneme').status_code == 403
    assert member.get('/dijital-kutuphane/2/sayfa/2').status_code == 403
    assert member.post('/dijital-kutuphane/2/ilerleme', data={'csrf_token': token, 'position': '2'}).status_code == 403
