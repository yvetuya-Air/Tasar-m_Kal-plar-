"""Kullanıcı sorgulama ve Werkzeug parola doğrulaması."""
import secrets
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db
from models import User

_DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))


def authenticate(username, password):
    row = get_db().execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    try:
        valid = check_password_hash(row['password_hash'] if row else _DUMMY_HASH, password)
    except (ValueError,TypeError):
        # Bozuk/eskimiş hash kimlik doğrulamayı geçirmez ve HTTP 500 üretmez.
        check_password_hash(_DUMMY_HASH,password)
        valid = False
    return active_user(row['id']) if row and valid else None


def active_user(user_id):
    row = get_db().execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    if row is None or not row['is_active']:
        return None
    member = get_db().execute('SELECT is_active FROM members WHERE user_id=?', (user_id,)).fetchone()
    return None if member and not member['is_active'] else User.from_row(row)


def revoke_sessions(user):
    db=get_db()
    with db:
        db.execute('UPDATE users SET session_version=session_version+1 WHERE id=? AND session_version=?',(user.id,user.session_version))
