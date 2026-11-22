"""Üyeye ait raf, profil ve hesap rotaları."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from security import login_required, role_required
from services import member_portal as portal

bp = Blueprint('member_portal', __name__)


@bp.get('/kitaplarim')
@role_required('member')
def my_books():
    return render_template('member_shelf.html', title='Kitaplarım',
                           items=portal.borrowed_books(g.user.id),
                           suggested=portal.recommendations(g.user.id))


@bp.get('/favorilerim', defaults={'name': 'favorilerim'})
@bp.get('/okuma-listem', defaults={'name': 'okuma-listem'})
@role_required('member')
def shelf(name):
    kind, title = portal.LISTS[name]
    return render_template('member_shelf.html', title=title, items=portal.shelf(g.user.id, kind), list_kind=kind)


@bp.get('/okuma-gecmisim')
@role_required('member')
def history():
    return render_template('member_shelf.html', title='Okuma Geçmişim', items=portal.reading_history(g.user.id))


@bp.post('/kitaplarim/<int:book_id>/liste')
@role_required('member')
def list_action(book_id):
    kind = request.form.get('kind')
    operation = request.form.get('operation')
    if kind not in ('favorite', 'reading') or operation not in ('add', 'remove'):
        abort(400)
    try:
        portal.save_list_entry(g.user.id, book_id, kind, operation == 'add')
    except LookupError:
        abort(404)
    flash('Kişisel kitap listeniz güncellendi.', 'success')
    if operation == 'remove':
        return redirect(url_for('member_portal.shelf', name='favorilerim' if kind == 'favorite' else 'okuma-listem'))
    return redirect(url_for('books.index'))


@bp.route('/profilim', methods=['GET', 'POST'])
@role_required('member')
def profile():
    member = portal.profile(g.user.id)
    if member is None or request.method == 'GET':
        return render_template('member_profile.html', member=member)
    try:
        portal.change_profile(g.user.id, request.form.get('full_name', ''), request.form.get('email', ''))
    except ValueError as error:
        return render_template('member_profile.html', member=request.form, error=str(error)), 422
    flash('Profiliniz güncellendi.', 'success')
    return redirect(url_for('member_portal.profile'))


@bp.route('/ayarlar/parola', methods=['GET', 'POST'])
@login_required
def password():
    if request.method == 'POST':
        try:
            portal.change_password(g.user, request.form.get('current_password', ''), request.form.get('password', ''),
                                   request.form.get('confirmation', ''))
        except ValueError as error:
            return render_template('password.html', error=str(error)), 422
        session.clear()
        flash('Parolanız güncellendi. Yeni parolayla giriş yapın.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('password.html')


@bp.get('/cezalar')
@login_required
def penalties():
    return render_template('penalties.html', items=portal.penalties(g.user))
