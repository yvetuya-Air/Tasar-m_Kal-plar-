"""Dijital koleksiyon, erişim denetimli okuyucu ve ilerleme rotaları."""
import io

from flask import Blueprint, abort, g, jsonify, render_template, request, send_file

from database import get_db
from security import login_required
from services import digital_service as media
from services.book_service import get_book

bp = Blueprint('digital', __name__, url_prefix='/dijital-kutuphane')


@bp.get('')
@login_required
def index():
    rows = get_db().execute(
        "SELECT id,title,author,cover_url,book_type,managed_media,file_url FROM books WHERE book_type IN ('ebook','audio') ORDER BY title",
    ).fetchall()
    return render_template('digital_library.html', books=[(book, media.can_read(book['id'], g.user)) for book in rows])


def authorized_media(book_id):
    info = media.media_info(book_id)
    if info is None:
        abort(404)
    if not media.can_read(book_id, g.user):
        abort(403)
    return info


@bp.get('/<int:book_id>/oku')
@login_required
def reader(book_id):
    info = authorized_media(book_id)
    position, bookmarks = media.reading_state(g.user.id, book_id)
    text_mode = bool(info['page_count']) and request.args.get('mode') == 'text'
    text = query = ''
    matches = []
    truncated = False
    if text_mode:
        query = request.args.get('q', '').strip()
        position = request.args.get('page', int(position or 1), type=int)
        if len(query) > 100 or not 1 <= position <= info['page_count']:
            abort(400)
        try:
            text, matches, truncated = media.pdf_readable_text(media.media_bytes(book_id), position, query)
        except (ValueError, RuntimeError, media.pdfium.PdfiumError):
            abort(422)
    view = {'enabled': text_mode, 'text': text, 'query': query, 'matches': matches, 'truncated': truncated}
    return render_template('digital_reader.html', book=get_book(book_id), info=info,
                           position=position or (1 if info['page_count'] else 0), bookmarks=bookmarks, text_view=view)


@bp.get('/<int:book_id>/sayfa/<int:page>')
@login_required
def page_image(book_id, page):
    info = authorized_media(book_id)
    if not info['page_count'] or page > info['page_count']:
        abort(404)
    zoom = request.args.get('zoom', 1.4, type=float)
    if not 0.5 <= zoom <= 3:
        abort(400)
    try:
        image = media.pdf_page(media.media_bytes(book_id), page, zoom)
    except (ValueError, RuntimeError, media.pdfium.PdfiumError):
        abort(422)
    response = send_file(image, mimetype='image/jpeg')
    response.cache_control.no_store = True
    return response


@bp.get('/<int:book_id>/ses')
@login_required
def audio(book_id):
    info = authorized_media(book_id)
    if not info['duration']:
        abort(404)
    name = 'kitap.mp3' if info['mime'] == 'audio/mpeg' else 'kitap.wav'
    response = send_file(io.BytesIO(media.media_bytes(book_id)), mimetype=info['mime'],
                         download_name=name, conditional=True)
    response.cache_control.no_store = True
    return response


@bp.post('/<int:book_id>/ilerleme')
@login_required
def progress(book_id):
    info = authorized_media(book_id)
    try:
        media.save_position(g.user.id, book_id, info, request.form.get('position', ''))
    except ValueError as issue:
        return jsonify(error=str(issue)), 422
    return '', 204


@bp.post('/<int:book_id>/ayrac')
@login_required
def bookmark(book_id):
    info = authorized_media(book_id)
    try:
        number = int(request.form.get('page', ''))
        media.set_bookmark(g.user.id, book_id, info, number, request.form.get('marked') == 'yes')
    except ValueError:
        return jsonify(error='Geçersiz ayraç sayfası.'), 422
    return '', 204
