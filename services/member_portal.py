"""Üye rafı, öneriler, profil ve parola işlemleri."""
import re
import sqlite3
from werkzeug.security import generate_password_hash

from database import get_db
from services.auth_service import authenticate


LISTS = {'favorilerim': ('favorite', 'Favorilerim'), 'okuma-listem': ('reading', 'Okuma Listem')}


def profile(user_id):
    return get_db().execute('SELECT * FROM members WHERE user_id=? AND is_active=1', (user_id,)).fetchone()


def change_profile(user_id, name, email):
    name, email = name.strip(), email.strip()
    if not 1 <= len(name) <= 160 or len(email) > 254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        raise ValueError('Geçerli ad soyad ve e-posta girin.')
    db = get_db()
    try:
        with db:
            db.execute('UPDATE members SET full_name=?,email=? WHERE user_id=?', (name, email, user_id))
            db.execute("INSERT INTO activity_logs(user_id,action,details) VALUES(?,'profile_updated','Üye profili güncellendi')", (user_id,))
    except sqlite3.IntegrityError:
        raise ValueError('Bu e-posta adresi zaten kayıtlı.') from None


def change_password(user, old, new, confirmation):
    if not 8 <= len(new) <= 256 or new != confirmation:
        raise ValueError('Yeni parola 8–256 karakter olmalı ve doğrulamayla eşleşmelidir.')
    if not 1 <= len(old) <= 256 or authenticate(user.username, old) is None:
        raise ValueError('Mevcut parola hatalı.')
    password_hash = generate_password_hash(new)
    db = get_db()
    with db:
        result = db.execute(
            'UPDATE users SET password_hash=?,session_version=session_version+1 WHERE id=? AND session_version=?',
            (password_hash, user.id, user.session_version),
        )
        if result.rowcount != 1:
            raise ValueError('Oturum değişti. Tekrar giriş yapın.')
        db.execute('DELETE FROM password_resets WHERE user_id=?', (user.id,))
        db.execute("INSERT INTO activity_logs(user_id,action,details) VALUES(?,'password_changed','Parola değiştirildi')", (user.id,))


def save_list_entry(user_id, book_id, kind, add):
    db = get_db()
    with db:
        if not db.execute('SELECT 1 FROM books WHERE id=?', (book_id,)).fetchone():
            raise LookupError
        if add:
            db.execute('INSERT OR IGNORE INTO member_books(user_id,book_id,list_type) VALUES(?,?,?)',
                       (user_id, book_id, kind))
        else:
            db.execute('DELETE FROM member_books WHERE user_id=? AND book_id=? AND list_type=?',
                       (user_id, book_id, kind))


def shelf(user_id, kind):
    return get_db().execute(
        '''SELECT b.id,b.title,b.author,b.cover_url FROM member_books f
           JOIN books b ON b.id=f.book_id WHERE f.user_id=? AND f.list_type=?
           ORDER BY f.created_at DESC,b.id DESC''', (user_id, kind),
    ).fetchall()


def reading_history(user_id):
    return get_db().execute(
        '''SELECT b.id,b.title,b.author,b.cover_url,r.updated_at,
                  ROUND(r.position*100 / COALESCE(m.page_count,m.duration)) AS percent
           FROM reading_progress r JOIN books b ON b.id=r.book_id JOIN book_media m ON m.book_id=b.id
           WHERE r.user_id=? ORDER BY r.updated_at DESC,b.id DESC''', (user_id,),
    ).fetchall()


def borrowed_books(user_id):
    return get_db().execute(
        '''SELECT b.id,b.title,b.author,b.cover_url,b.managed_media,l.due_on,d.page_count,p.position FROM loans l
           JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
           LEFT JOIN book_media d ON d.book_id=b.id
           LEFT JOIN reading_progress p ON p.book_id=b.id AND p.user_id=m.user_id
           WHERE m.user_id=? AND l.returned_on IS NULL ORDER BY l.due_on,b.id''', (user_id,),
    ).fetchall()


def recommendations(user_id):
    return get_db().execute(
        '''SELECT b.id,b.title,b.author,b.cover_url FROM books b JOIN (
             SELECT saved.category_id,COUNT(*) AS weight FROM member_books f JOIN books saved ON saved.id=f.book_id
             WHERE f.user_id=? GROUP BY saved.category_id
           ) preferences ON preferences.category_id=b.category_id
           WHERE NOT EXISTS(SELECT 1 FROM member_books x WHERE x.book_id=b.id AND x.user_id=?)
           ORDER BY preferences.weight DESC,b.id DESC LIMIT 8''', (user_id, user_id),
    ).fetchall()


def penalties(user):
    return get_db().execute(
        '''SELECT b.title,l.returned_on,l.penalty_cents,m.full_name FROM loans l
           JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
           WHERE l.penalty_cents>0 AND (?='admin' OR m.user_id=?)
           ORDER BY l.returned_on DESC,l.id DESC''', (user.role, user.id),
    ).fetchall()
