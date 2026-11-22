"""Observer abonelerini yükler; bildirim yazmalarında dış işlemi korur."""
from patterns.observer import BookAvailabilitySubject, MemberObserver, MemberEventObserver, NotificationEventSubject
from database import get_db
from services.circulation_policy import EVENTS, hold_hours


class NotificationService:
    def __init__(self, db):
        self.db = db

    def _require_transaction(self):
        if not self.db.in_transaction:
            raise RuntimeError('Bildirim oluşturma açık SQLite işlemi gerektirir.')

    def publish_availability(self, book_id):
        self._require_transaction()
        book = self.db.execute('SELECT title,available_copies FROM book_inventory WHERE id=?',(book_id,)).fetchone()
        if book is None or book['available_copies'] <= 0:
            return 0
        subject = BookAvailabilitySubject(book_id,book['title'])
        rows = self.db.execute("SELECT r.id FROM reservations r JOIN members m ON m.id=r.member_id LEFT JOIN users u ON u.id=m.user_id WHERE r.book_id=? AND r.status IN ('active','notified') AND m.is_active=1 AND (u.id IS NULL OR u.is_active=1) ORDER BY r.created_at,r.id",(book_id,)).fetchall()
        for row in rows[:book['available_copies']]:
            subject.attach(MemberObserver(row['id'],self))
        return subject.notify()

    def notify_reserved_member(self, reservation_id, book_id, title):
        self._require_transaction()
        row = self.db.execute("SELECT r.member_id FROM reservations r JOIN members m ON m.id=r.member_id LEFT JOIN users u ON u.id=m.user_id JOIN book_inventory b ON b.id=r.book_id WHERE r.id=? AND r.book_id=? AND r.status IN ('active','notified') AND m.is_active=1 AND (u.id IS NULL OR u.is_active=1) AND b.available_copies>0",(reservation_id,book_id)).fetchone()
        if row is None:
            return False
        hours = hold_hours(self.db)
        hold = self.db.execute("INSERT OR IGNORE INTO reservation_holds VALUES(?,datetime('now',?))",
                               (reservation_id, f'+{hours} hours'))
        if not hold.rowcount:
            return False
        message = f'“{title}” kitabı sizin için {hours} saat ayrıldı.'
        cursor = None
        if self.allows(row['member_id'], 'available'):
            cursor = self.db.execute('INSERT INTO notifications(member_id,reservation_id,message) SELECT ?,?,? WHERE NOT EXISTS(SELECT 1 FROM notifications WHERE reservation_id=?)',
                                     (row['member_id'],reservation_id,message,reservation_id))
        self.db.execute("UPDATE reservations SET status='notified' WHERE id=? AND status='active'",(reservation_id,))
        return cursor is not None and cursor.rowcount == 1

    def allows(self, member_id, kind):
        return not self.db.execute('SELECT 1 FROM notification_preferences WHERE member_id=? AND kind=?',
                                   (member_id, kind)).fetchone()

    def publish(self, kind, event_key, message, member_ids):
        self._require_transaction()
        subject = NotificationEventSubject(event_key, message)
        for member_id in member_ids:
            subject.attach(MemberEventObserver(member_id, kind, self))
        return subject.notify()

    def store_event(self, member_id, kind, key, message):
        event_key = f'{kind}:{member_id}:{key}'
        if not self.allows(member_id, kind) or self.db.execute(
            'SELECT 1 FROM notification_events WHERE event_key=?', (event_key,),
        ).fetchone():
            return False
        notification_id = self.db.execute('INSERT INTO notifications(member_id,message) VALUES(?,?)',
                                          (member_id, message)).lastrowid
        self.db.execute('INSERT INTO notification_events VALUES(?,?,?)', (notification_id, kind, event_key))
        return True

    def expire_holds(self, book_id=None):
        self._require_transaction()
        rows = self.db.execute(
            """SELECT h.reservation_id,r.book_id,r.member_id,b.title FROM reservation_holds h
               JOIN reservations r ON r.id=h.reservation_id JOIN books b ON b.id=r.book_id
               WHERE h.expires_at<=CURRENT_TIMESTAMP AND r.status='notified' AND (? IS NULL OR r.book_id=?)""",
            (book_id, book_id),
        ).fetchall()
        for row in rows:
            self.db.execute("UPDATE reservations SET status='cancelled' WHERE id=?", (row['reservation_id'],))
            self.db.execute('DELETE FROM reservation_holds WHERE reservation_id=?', (row['reservation_id'],))
            self.publish('expired', row['reservation_id'], f'“{row["title"]}” ayırma süresi doldu.', [row['member_id']])
        for affected in sorted({row['book_id'] for row in rows}):
            self.publish_availability(affected)
        return len(rows)


def member_for_user(user_id):
    row = get_db().execute('SELECT id FROM members WHERE user_id=?',(user_id,)).fetchone()
    return row['id'] if row else None


def unread_count(user_id):
    member_id = member_for_user(user_id)
    return get_db().execute('SELECT COUNT(*) FROM notifications WHERE member_id=? AND is_read=0',(member_id,)).fetchone()[0]


def list_notifications(user_id, page=1, kind=''):
    db = get_db()
    member_id = member_for_user(user_id)
    category = "COALESCE(e.kind,CASE WHEN n.reservation_id IS NOT NULL THEN 'available' ELSE '' END)"
    joins = 'FROM notifications n LEFT JOIN notification_events e ON e.notification_id=n.id'
    where = f"WHERE n.member_id=? AND (?='' OR {category}=?)"
    count = db.execute(f'SELECT COUNT(*) {joins} {where}',(member_id, kind, kind)).fetchone()[0]
    pages = max(1,(count+19)//20)
    page = min(max(1,page),pages)
    rows = db.execute(f'SELECT n.*,{category} AS kind {joins} {where} ORDER BY n.created_at DESC,n.id DESC LIMIT 20 OFFSET ?',
                      (member_id,kind,kind,(page-1)*20)).fetchall()
    return rows,count,page,pages


def notification_options(user_id):
    return {row['kind'] for row in get_db().execute('SELECT kind FROM notification_preferences WHERE member_id=?',
                                                  (member_for_user(user_id),))}


def update_options(user_id, enabled):
    db = get_db()
    member_id = member_for_user(user_id)
    if member_id is None:
        return
    with db:
        db.execute('DELETE FROM notification_preferences WHERE member_id=?', (member_id,))
        db.executemany('INSERT INTO notification_preferences VALUES(?,?)',
                       ((member_id, kind) for kind in EVENTS if kind not in enabled))


def mark_all(user_id):
    db = get_db()
    with db:
        db.execute('UPDATE notifications SET is_read=1 WHERE member_id=?', (member_for_user(user_id),))


def mark_read(notification_id, user_id):
    db = get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        member_id = member_for_user(user_id)
        row = db.execute('SELECT id FROM notifications WHERE id=? AND member_id=?',(notification_id,member_id)).fetchone()
        if row is None:
            raise LookupError('Bildirim bulunamadı.')
        db.execute('UPDATE notifications SET is_read=1 WHERE id=? AND member_id=?',(notification_id,member_id))
