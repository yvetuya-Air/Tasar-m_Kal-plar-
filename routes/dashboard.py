"""Ortak panel, yönetici alanı ve üyeye özel hesap görünümü."""
from flask import Blueprint, g, render_template
from database import get_db
from security import login_required, role_required
from services.dashboard_service import dashboard_data

bp = Blueprint('dashboard', __name__)


@bp.get('/panel')
@login_required
def panel():
    return render_template('overview.html',**dashboard_data(g.user))


@bp.get('/yonetim')
@role_required('admin')
def admin():
    return render_template('panel.html', section='admin')


@bp.get('/hesabim')
@role_required('member')
def account():
    member = get_db().execute('SELECT full_name, email, member_type FROM members WHERE user_id=?', (g.user.id,)).fetchone()
    return render_template('panel.html', section='account', member=member)
