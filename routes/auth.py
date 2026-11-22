"""Giriş, çıkış ve her istekte güncel kullanıcı yükleme."""
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from services.auth_service import active_user, authenticate, revoke_sessions
from services import account_security as limits
from database import get_db
from security import csrf_token, login_required

bp = Blueprint('auth', __name__)


@bp.before_app_request
def load_user():
    g.user = None
    if request.endpoint == 'static':
        return
    user_id = session.get('user_id')
    if isinstance(user_id, int):
        g.user = active_user(user_id)
        if g.user is None or type(session.get('session_version')) is not int or session['session_version']!=g.user.session_version:
            g.user = None
            session.clear()


@bp.route('/giris', methods=['GET', 'POST'])
def login():
    if g.user is not None:
        return redirect(url_for('dashboard.panel'))
    error = None
    username = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        attempt = limits.reserve_login(username[:80], request.remote_addr)
        if attempt is None:
            response = render_template('login.html', error='Çok fazla deneme yapıldı. 15 dakika sonra tekrar deneyin.', username=username[:80])
            return response, 429, {'Retry-After': '900'}
        user = authenticate(username, password) if 0 < len(username) <= 80 and 0 < len(password) <= 256 else None
        limits.complete_login(attempt, user)
        if user:
            session.clear()
            session['user_id'] = user.id
            session['session_version'] = user.session_version
            session.permanent = True
            csrf_token()
            return redirect(url_for('dashboard.panel'))
        error = 'Kullanıcı adı veya parola hatalı ya da hesap kullanıma kapalı.'
    return render_template('login.html', error=error, username=username[:80]), 401 if error else 200


@bp.post('/cikis')
@login_required
def logout():
    revoke_sessions(g.user)
    with get_db() as db:
        limits.log_activity(db, g.user.id, 'logout', 'Başarılı')
    session.clear()
    flash('Oturumunuz güvenle kapatıldı.', 'success')
    return redirect(url_for('auth.login'))


@bp.route('/parola-sifirla', methods=['GET', 'POST'])
def reset():
    error = None
    if request.method == 'POST':
        try:
            limits.consume_reset(request.form.get('token', ''), request.form.get('password', ''),
                                 request.form.get('confirmation', ''))
        except ValueError as issue:
            error = str(issue)
        else:
            session.clear()
            flash('Parolanız sıfırlandı. Yeni parolayla giriş yapın.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('password_reset.html', error=error), 422 if error else 200
