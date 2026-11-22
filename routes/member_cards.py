"""Kişisel kart ve yetkili hızlı üye tanıma."""
from flask import Blueprint, abort, g, render_template, request, send_file

from database import get_db
from security import role_required
from services import member_card as cards

bp = Blueprint('member_cards', __name__)


def private_file(file, mimetype, filename=None):
    response = send_file(file, mimetype=mimetype, download_name=filename, as_attachment=bool(filename))
    response.cache_control.no_store = True
    return response


@bp.get('/uye-kartim')
@role_required('member')
def card():
    return render_template('member_card.html', card=cards.card_for_user(g.user.id), types=cards.TYPES)


@bp.get('/uye-kartim/qr')
@role_required('member')
def qr():
    card = cards.card_for_user(g.user.id)
    if card is None:
        abort(404)
    return private_file(cards.image_file(cards.qr_image(card), 'PNG'), 'image/png')


@bp.get('/uye-kartim/indir/<file_format>')
@role_required('member')
def download(file_format):
    card = cards.card_for_user(g.user.id)
    formats = {'png': 'image/png', 'pdf': 'application/pdf'}
    if card is None or file_format not in formats:
        abort(404)
    return private_file(cards.image_file(cards.card_image(card), file_format.upper()),
                        formats[file_format], f'uye-karti.{file_format}')


@bp.route('/uye-tani', methods=['GET', 'POST'])
@role_required('admin')
def scan():
    result = None
    active_loans = []
    error = None
    if request.method == 'POST':
        result = cards.find_card(request.form.get('identifier', ''))
        if result:
            active_loans = get_db().execute(
                '''SELECT l.id,b.title FROM loans l JOIN books b ON b.id=l.book_id
                   WHERE l.member_id=? AND l.returned_on IS NULL ORDER BY l.id''', (result['id'],),
            ).fetchall()
        else:
            error = 'Üye bulunamadı. QR kodu veya üye numarasını kontrol edin.'
    return render_template('member_scan.html', member=result, loans=active_loans, error=error), 404 if error else 200
