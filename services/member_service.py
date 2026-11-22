"""Yönetici üye dizini, doğrulama ve değişiklik işlemleri."""
import re
import sqlite3
from werkzeug.security import generate_password_hash
from database import get_db
from services.validation import escaped_like
from services.notification_service import NotificationService


class MemberValidationError(ValueError):
    pass


def get_member(member_id):
    return get_db().execute('SELECT * FROM members WHERE id=?',(member_id,)).fetchone()


def search_members(query='',status='all',page=1):
    db=get_db()
    pattern=escaped_like(query)
    where="(tr_fold(full_name) LIKE tr_fold(?) ESCAPE '\\' OR tr_fold(email) LIKE tr_fold(?) ESCAPE '\\')"
    params=[pattern,pattern]
    if status!='all':
        where+=' AND is_active=?'
        params.append(1 if status=='active' else 0)
    count=db.execute(f'SELECT COUNT(*) FROM members WHERE {where}',params).fetchone()[0]
    pages=max(1,(count+19)//20)
    page=min(max(page,1),pages)
    rows=db.execute(f'SELECT * FROM members WHERE {where} ORDER BY id DESC LIMIT 20 OFFSET ?',(*params,(page-1)*20)).fetchall()
    return rows,count,page,pages


def save_member(data,user_id,member_id=None):
    name=data.get('full_name','').strip()
    email=data.get('email','').strip()
    kind=data.get('member_type','')
    account_name=data.get('account_username','').strip()
    account_password=data.get('account_password','')
    if not 1<=len(name)<=160:
        raise MemberValidationError('Ad soyad 1–160 karakter olmalıdır.')
    if len(email)>254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):
        raise MemberValidationError('Geçerli bir e-posta adresi girin.')
    if kind not in ('student','teacher','standard'):
        raise MemberValidationError('Geçerli bir üyelik türü seçin.')
    if account_name or account_password:
        if not re.fullmatch(r'[A-Za-z0-9_.-]{3,80}',account_name):
            raise MemberValidationError('Kullanıcı adı 3–80 harf, rakam, nokta, alt çizgi veya tire içermelidir.')
        if not 8<=len(account_password)<=256:
            raise MemberValidationError('Yeni hesap parolası 8–256 karakter olmalıdır.')
    db=get_db()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            linked_user_id=None
            if member_id is not None:
                existing=get_member(member_id)
                if existing is None:
                    raise LookupError('Üye bulunamadı.')
                linked_user_id=existing['user_id']
                if linked_user_id is not None and (account_name or account_password):
                    raise MemberValidationError('Bağlı giriş hesabı bu formdan değiştirilemez.')
                db.execute('UPDATE members SET full_name=?,email=?,member_type=? WHERE id=?',(name,email,kind,member_id))
            else:
                member_id=db.execute('INSERT INTO members(full_name,email,member_type) VALUES(?,?,?)',(name,email,kind)).lastrowid
            if account_name:
                linked_user_id=db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,'member')",(account_name,generate_password_hash(account_password))).lastrowid
                db.execute('UPDATE members SET user_id=? WHERE id=?',(linked_user_id,member_id))
            db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)',(user_id,'member_saved',f'Üye #{member_id}: {name}'))
            log_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            NotificationService(db).publish('membership', log_id, 'Üyelik bilgileriniz kaydedildi.', [member_id])
    except sqlite3.IntegrityError as error:
        message='Bu kullanıcı adı zaten kayıtlı.' if 'users.username' in str(error) else 'Bu e-posta adresi zaten kayıtlı veya üye bilgileri geçersiz.'
        raise MemberValidationError(message) from error
    return member_id


def set_active(member_id,active,user_id):
    db=get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        member=get_member(member_id)
        if member is None:
            raise LookupError('Üye bulunamadı.')
        db.execute('UPDATE members SET is_active=? WHERE id=?',(int(active),member_id))
        if not active and member['is_active'] and member['user_id'] is not None:
            db.execute('UPDATE users SET session_version=session_version+1 WHERE id=?',(member['user_id'],))
        db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)',(user_id,'member_status',f'Üye #{member_id}: {"aktif" if active else "pasif"}'))
        log_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        NotificationService(db).publish('membership', log_id, 'Üyelik durumunuz güncellendi.', [member_id])
