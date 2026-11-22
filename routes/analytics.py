"""Yönetici analitik ekranı."""
from flask import Blueprint, render_template, request

from security import role_required
from services import analytics

bp = Blueprint('analytics', __name__)


@bp.get('/analitik')
@role_required('admin')
def index():
    try:
        period = analytics.selected_period(request.args)
    except ValueError as error:
        return render_template('analytics.html', error=str(error)), 422
    cards, charts = analytics.dashboard(period)
    return render_template('analytics.html', period=period, cards=cards, charts=charts)
