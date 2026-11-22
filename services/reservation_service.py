"""Kronolojik rezervasyon kuyruğu ve atomik kayıt/iptal işlemleri."""
import sqlite3
from database import get_db
from services.notification_service import NotificationService
from services.validation import record_id


class ReservationValidationError(ValueError):
    pass


def eligible_queue(db, book_id):
    return db.execute("SELECT r.* FROM reservations r JOIN members m ON m.id=r.member_id LEFT JOIN users u ON u.id=m.user_id WHERE r.book_id=? AND r.status IN ('active','notified') AND m.is_active=1 AND (u.id IS NULL OR u.is_active=1) ORDER BY r.created_at,r.id",(book_id,)).fetchall()


def create_reservation(book_id, member_id, user_id):
    try:
        book_id,member_id = record_id(book_id,'Kitap'),record_id(member_id,'Üye')
    except ValueError as error:
        raise ReservationValidationError(str(error)) from None
    db = get_db()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            book = db.execute('SELECT * FROM book_inventory WHERE id=?',(book_id,)).fetchone()
            member = db.execute('SELECT m.*,u.is_active AS user_active FROM members m LEFT JOIN users u ON u.id=m.user_id WHERE m.id=?',(member_id,)).fetchone()
            if book is None or member is None:
                raise ReservationValidationError('Kitap veya üye bulunamadı.')
            if not member['is_active'] or member['user_active']==0:
                raise ReservationValidationError('Pasif üye için rezervasyon yapılamaz.')
            if book['available_copies']>0:
                raise ReservationValidationError('Mevcut kitap rezerve edilemez; ödünç işlemini kullanın.')
            if db.execute("SELECT 1 FROM reservations WHERE book_id=? AND member_id=? AND status IN ('active','notified')",(book_id,member_id)).fetchone():
                raise ReservationValidationError('Bu kitap için aktif rezervasyon zaten var.')
            if db.execute('SELECT 1 FROM loans WHERE book_id=? AND member_id=? AND returned_on IS NULL',(book_id,member_id)).fetchone():
                raise ReservationValidationError('Zaten ödünç aldığınız kitap için rezervasyon oluşturamazsınız.')
            reservation_id = db.execute('INSERT INTO reservations(book_id,member_id) VALUES(?,?)',(book_id,member_id)).lastrowid
            NotificationService(db).publish('reserved', reservation_id, f'“{book["title"]}” için rezervasyonunuz onaylandı.', [member_id])
            db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)',(user_id,'reservation_created',f'Rezervasyon #{reservation_id}; kitap #{book_id}; üye #{member_id}'))
    except sqlite3.IntegrityError as error:
        raise ReservationValidationError('Rezervasyon kaydedilemedi; aktif rezervasyon ve üye bilgilerini kontrol edin.') from error
    return reservation_id


def cancel_reservation(reservation_id, user_id, owner_member_id=None, admin=False):
    db = get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM reservations WHERE id=?',(reservation_id,)).fetchone()
        if row is None or (not admin and row['member_id'] != owner_member_id):
            raise LookupError('Rezervasyon bulunamadı.')
        if row['status'] not in ('active','notified'):
            raise ReservationValidationError('Bu rezervasyon zaten sonlandırılmış.')
        db.execute("UPDATE reservations SET status='cancelled' WHERE id=?",(reservation_id,))
        db.execute('DELETE FROM reservation_holds WHERE reservation_id=?', (reservation_id,))
        db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)',(user_id,'reservation_cancelled',f'Rezervasyon #{reservation_id} iptal edildi.'))
        NotificationService(db).publish_availability(row['book_id'])


def choices():
    db = get_db()
    books = db.execute('SELECT id,title FROM book_inventory WHERE available_copies=0 ORDER BY title').fetchall()
    members = db.execute('SELECT m.id,m.full_name FROM members m LEFT JOIN users u ON u.id=m.user_id WHERE m.is_active=1 AND (u.id IS NULL OR u.is_active=1) ORDER BY m.full_name').fetchall()
    return books,members


def list_reservations(member_id=None, only_member=False, status='active', page=1):
    db = get_db()
    clauses,params = [],[]
    if only_member:
        clauses.append('r.member_id=?')
        params.append(member_id if member_id is not None else -1)
    if status=='active':
        clauses.append("r.status IN ('active','notified')")
    elif status=='history':
        clauses.append("r.status IN ('cancelled','fulfilled')")
    where = ' AND '.join(clauses) or '1=1'
    count = db.execute(f'SELECT COUNT(*) FROM reservations r WHERE {where}',params).fetchone()[0]
    pages = max(1,(count+19)//20)
    page = min(max(page,1),pages)
    rows = db.execute(f'SELECT r.*,b.title,m.full_name,h.expires_at FROM reservations r JOIN books b ON b.id=r.book_id JOIN members m ON m.id=r.member_id LEFT JOIN reservation_holds h ON h.reservation_id=r.id WHERE {where} ORDER BY r.created_at,r.id LIMIT 20 OFFSET ?',(*params,(page-1)*20)).fetchall()
    queues = {row['book_id']:[item['id'] for item in eligible_queue(db,row['book_id'])] for row in rows}
    items = [{'row':row,'position':queues[row['book_id']].index(row['id'])+1 if row['id'] in queues[row['book_id']] else None} for row in rows]
    return items,count,page,pages
