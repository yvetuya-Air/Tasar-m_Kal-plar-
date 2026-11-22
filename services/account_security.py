"""Oturum açma sınırı, denetim günlüğü ve tek kullanımlık parola sıfırlama."""
import hashlib
import hmac
import re
import secrets

from flask import current_app
from werkzeug.security import generate_password_hash

from database import get_db


def log_activity(db, user_id, action, details):
    db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)',
               (user_id, action, details))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def bucket(namespace, value):
    key = current_app.secret_key
    if isinstance(key, str):
        key = key.encode('utf-8')
    return hmac.new(key, f'{namespace}:{value}'.encode('utf-8'), hashlib.sha256).hexdigest()


def reserve_login(username, address):
    account = bucket('account', username.casefold())
    network = bucket('address', address or '')
    db = get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("DELETE FROM login_attempts WHERE created_at<=datetime('now','-15 minutes')")
        by_account = db.execute('SELECT count(*) FROM login_attempts WHERE account_bucket=?', (account,)).fetchone()[0]
        by_ip = db.execute('SELECT count(*) FROM login_attempts WHERE address_bucket=?', (network,)).fetchone()[0]
        if by_account >= 8 or by_ip >= 40:
            return None
        return db.execute('INSERT INTO login_attempts(account_bucket,address_bucket) VALUES(?,?)', (account, network)).lastrowid


def complete_login(attempt, user):
    db = get_db()
    with db:
        row = db.execute('SELECT account_bucket FROM login_attempts WHERE id=?', (attempt,)).fetchone()
        if user is not None:
            if row:
                db.execute('DELETE FROM login_attempts WHERE account_bucket=?', (row['account_bucket'],))
            log_activity(db, user.id, 'login', 'Başarılı')
        else:
            log_activity(db, None, 'login_failed', 'Başarısız')


def issue_reset(username):
    db = get_db()
    token = secrets.token_urlsafe(32)
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT id FROM users WHERE username=? AND is_active=1', (username,)).fetchone()
        if not row:
            raise LookupError('Etkin hesap bulunamadı.')
        db.execute("""INSERT INTO password_resets VALUES(?,?,datetime('now','+30 minutes'))
                   ON CONFLICT(user_id) DO UPDATE SET token_hash=excluded.token_hash,expires_at=excluded.expires_at""",
                   (row['id'], digest(token)))
        log_activity(db, row['id'], 'reset_issued', 'Sıfırlama isteği oluşturuldu')
    return token


def consume_reset(token, password, confirmation):
    if not 8 <= len(password) <= 256 or password != confirmation:
        raise ValueError('Yeni parola 8–256 karakter olmalı ve doğrulamayla eşleşmelidir.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise ValueError('Geçersiz veya süresi dolmuş kod.')
    db = get_db()
    token_hash = digest(token)
    row = db.execute('SELECT user_id FROM password_resets WHERE token_hash=? AND expires_at>CURRENT_TIMESTAMP',
                     (token_hash,)).fetchone()
    if not row:
        raise ValueError('Geçersiz veya süresi dolmuş kod.')
    hashed = generate_password_hash(password)
    with db:
        db.execute('BEGIN IMMEDIATE')
        deleted = db.execute('DELETE FROM password_resets WHERE token_hash=? AND expires_at>CURRENT_TIMESTAMP',
                             (token_hash,))
        if deleted.rowcount != 1:
            raise ValueError('Geçersiz veya süresi dolmuş kod.')
        user_id = row['user_id']
        updated = db.execute('UPDATE users SET password_hash=?,session_version=session_version+1 WHERE id=? AND is_active=1',
                             (hashed, user_id))
        if updated.rowcount != 1:
            raise ValueError('Geçersiz veya süresi dolmuş kod.')
        username = db.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()['username']
        db.execute('DELETE FROM login_attempts WHERE account_bucket=?', (bucket('account', username.casefold()),))
        log_activity(db, user_id, 'password_reset', 'Parola sıfırlandı')
