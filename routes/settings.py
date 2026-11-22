"""Tarayıcıya özgü görünüm tercihleri ve oturum bilgisi."""
from flask import Blueprint,current_app,g,render_template,request,redirect,flash,url_for
from database import get_db
from security import login_required, role_required
from services import circulation_policy as policy

bp=Blueprint('settings',__name__)


@bp.get('/ayarlar')
@login_required
def index():
    return render_template('settings.html',session_minutes=int(current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()/60),
                           api_configured=bool(current_app.config['GOOGLE_BOOKS_API_KEY']) if g.user.role=='admin' else None)


@bp.route('/ayarlar/odunc-politikasi', methods=['GET', 'POST'])
@role_required('admin')
def circulation():
    error = None
    if request.method == 'POST':
        try:
            policy.update_policies(request.form, g.user.id)
        except ValueError as issue:
            error = str(issue)
        else:
            flash('Ödünç politikaları kaydedildi.', 'success')
            return redirect(url_for('settings.circulation'))
    values = {kind: policy.display_policy(kind) for kind in policy.MEMBER_TYPES}
    return render_template('circulation_settings.html', values=values, types=policy.MEMBER_TYPES,
                           fields=policy.FIELDS, hours=policy.hold_hours(get_db()), error=error), 422 if error else 200
