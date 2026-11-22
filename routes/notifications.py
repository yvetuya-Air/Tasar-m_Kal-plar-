"""Yalnızca oturum sahibinin bildirimleri ve okunma işlemleri."""
from flask import Blueprint, abort, g, redirect, render_template, request, url_for
from security import login_required
from services import notification_service
from services.circulation_policy import EVENTS
from services.validation import requested_page

bp = Blueprint('notifications',__name__,url_prefix='/bildirimler')


@bp.get('')
@login_required
def index():
    page = requested_page(request.args.get('page',1))
    kind = request.args.get('kind', '')
    if kind and kind not in EVENTS:
        abort(400)
    rows,count,page,pages = notification_service.list_notifications(g.user.id,page,kind)
    return render_template('notifications.html',rows=rows,count=count,page=page,pages=pages,events=EVENTS,
                           kind=kind,disabled=notification_service.notification_options(g.user.id))


@bp.post('/<int:notification_id>/oku')
@login_required
def read(notification_id):
    try:
        notification_service.mark_read(notification_id,g.user.id)
    except LookupError:
        abort(404)
    return redirect(url_for('notifications.index'))


@bp.post('/tumunu-oku')
@login_required
def read_all():
    notification_service.mark_all(g.user.id)
    return redirect(url_for('notifications.index'))


@bp.post('/tercihler')
@login_required
def preferences():
    notification_service.update_options(g.user.id, set(request.form.getlist('enabled')))
    return redirect(url_for('notifications.index'))
