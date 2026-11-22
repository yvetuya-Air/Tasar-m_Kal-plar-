"""Dijital dosya doğrulama, erişim ve kişisel okuma durumu."""
import io
import math
from dataclasses import dataclass
from contextlib import closing
from pathlib import Path
from threading import Lock
import wave

import pypdfium2 as pdfium
from mutagen import MutagenError
from mutagen.mp3 import MP3

from database import get_db, turkish_fold

MEDIA_LIMIT = 32 * 1024 * 1024
PDF_LOCK = Lock()


@dataclass(frozen=True)
class DigitalFile:
    mime: str
    content: bytes
    page_count: int | None = None
    duration: float | None = None


def validate_upload(file, book_type, rights_confirmed):
    if not rights_confirmed:
        raise ValueError('Dosyanın dağıtım hakkına sahip olduğunuzu onaylayın.')
    content = file.stream.read(MEDIA_LIMIT + 1)
    if not content or len(content) > MEDIA_LIMIT:
        raise ValueError('Dosya boş olamaz ve 32 MB sınırını aşamaz.')
    extension = Path(file.filename).suffix.lower()
    try:
        if book_type == 'ebook' and extension == '.pdf' and content.startswith(b'%PDF-'):
            with PDF_LOCK, pdfium.PdfDocument(content) as document:
                pages = len(document)
                if 0 < pages <= 3000:
                    return DigitalFile('application/pdf', content, page_count=pages)
        if book_type == 'audio' and extension == '.mp3':
            duration = MP3(io.BytesIO(content)).info.length
            if math.isfinite(duration) and duration > 0:
                return DigitalFile('audio/mpeg', content, duration=duration)
        if book_type == 'audio' and extension == '.wav':
            with wave.open(io.BytesIO(content)) as sound:
                frames = sound.getnframes()
                expected = frames * sound.getnchannels() * sound.getsampwidth()
                if frames and expected <= len(content) and len(sound.readframes(frames)) == expected:
                    return DigitalFile('audio/wav', content, duration=frames / sound.getframerate())
    except (ValueError, RuntimeError, pdfium.PdfiumError, MutagenError, wave.Error, EOFError):
        pass
    raise ValueError('Geçerli bir PDF, MP3 veya PCM WAV dosyası yükleyin.')


def can_read(book_id, user):
    if user.role == 'admin':
        return True
    return get_db().execute(
        '''SELECT 1 FROM loans l JOIN members m ON m.id=l.member_id
           WHERE l.book_id=? AND m.user_id=? AND m.is_active=1 AND l.returned_on IS NULL''',
        (book_id, user.id),
    ).fetchone() is not None


def media_info(book_id):
    return get_db().execute(
        'SELECT mime,page_count,duration FROM book_media WHERE book_id=?', (book_id,),
    ).fetchone()


def media_bytes(book_id):
    row = get_db().execute('SELECT content FROM book_media WHERE book_id=?', (book_id,)).fetchone()
    return row['content']


def pdf_page(content, number, zoom):
    with PDF_LOCK, pdfium.PdfDocument(content) as document, closing(document[number - 1]) as page:
        width, height = page.get_size()
        if width <= 0 or height <= 0:
            raise ValueError('Geçersiz PDF sayfası.')
        scale = min(zoom, 2200 / max(width, height))
        with closing(page.render(scale=scale)) as bitmap:
            output = io.BytesIO()
            bitmap.to_pil().convert('RGB').save(output, format='JPEG', quality=88)
    output.seek(0)
    return output


def pdf_readable_text(content, number, query=''):
    def extract(document, index):
        with closing(document[index]) as page, closing(page.get_textpage()) as text_page:
            return text_page.get_text_bounded().replace('\r\n', '\n').strip()

    with PDF_LOCK, pdfium.PdfDocument(content) as document:
        current = extract(document, number - 1)
        matches = []
        if query:
            needle = turkish_fold(' '.join(query.split()))
            for index in range(len(document)):
                page_text = current if index == number - 1 else extract(document, index)
                if needle in turkish_fold(' '.join(page_text.split())):
                    matches.append(index + 1)
                    if len(matches) >= 31:
                        break
    return current, matches[:30], len(matches) > 30


def reading_state(user_id, book_id):
    db = get_db()
    row = db.execute('SELECT position FROM reading_progress WHERE user_id=? AND book_id=?',
                     (user_id, book_id)).fetchone()
    pages = db.execute('SELECT page FROM reading_bookmarks WHERE user_id=? AND book_id=? ORDER BY page',
                       (user_id, book_id))
    return row['position'] if row else None, [item['page'] for item in pages]


def save_position(user_id, book_id, info, value):
    position = float(value)
    pages = info['page_count']
    if not math.isfinite(position) or (pages and (not position.is_integer() or not 1 <= position <= pages)):
        raise ValueError('Geçersiz okuma konumu.')
    if not pages and not 0 <= position <= info['duration'] + 1:
        raise ValueError('Geçersiz dinleme konumu.')
    position = min(position, info['duration']) if not pages else position
    with get_db() as db:
        db.execute(
            '''INSERT INTO reading_progress(user_id,book_id,position) VALUES(?,?,?)
               ON CONFLICT(user_id,book_id) DO UPDATE SET
               position=excluded.position,updated_at=CURRENT_TIMESTAMP''',
            (user_id, book_id, position),
        )


def set_bookmark(user_id, book_id, info, page, marked):
    if not info['page_count'] or not 1 <= page <= info['page_count']:
        raise ValueError('Geçersiz ayraç sayfası.')
    with get_db() as db:
        if marked:
            db.execute('INSERT OR IGNORE INTO reading_bookmarks(user_id,book_id,page) VALUES(?,?,?)',
                       (user_id, book_id, page))
        else:
            db.execute('DELETE FROM reading_bookmarks WHERE user_id=? AND book_id=? AND page=?',
                       (user_id, book_id, page))
