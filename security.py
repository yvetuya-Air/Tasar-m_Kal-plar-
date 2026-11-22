"""CSRF ve sunucu tarafı erişim denetimi."""
from functools import wraps
import secrets
from flask import abort, g, redirect, request, session, url_for
from werkzeug.routing import IntegerConverter, ValidationError as RoutingValidationError
from services.validation import MAX_RECORD_ID, record_id


class RecordIDConverter(IntegerConverter):
    """URL kimlikleri de SQLite INTEGER aralığında ve pozitif olmalıdır."""
    def __init__(self, map):
        super().__init__(map, min=1, max=MAX_RECORD_ID)

    def to_python(self, value):
        try:
            return record_id(value)
        except ValueError:
            raise RoutingValidationError from None


def csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return session['_csrf_token']


def protect_csrf():
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        expected = session.get('_csrf_token')
        supplied = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if (not isinstance(expected,str) or not isinstance(supplied,str)
                or not expected.isascii() or not supplied.isascii() or len(supplied)>128
                or not secrets.compare_digest(expected,supplied)):
            abort(400)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorate(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user.role != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorate
