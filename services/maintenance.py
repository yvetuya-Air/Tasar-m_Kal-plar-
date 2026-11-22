"""Zamanlanabilir rezervasyon ve ödünç bildirimleri."""
from datetime import timedelta

from database import get_db
from services.loan_service import today
from services.notification_service import NotificationService


def refresh_circulation():
    db = get_db()
    service = NotificationService(db)
    now = today()
    with db:
        db.execute('BEGIN IMMEDIATE')
        expired = service.expire_holds()
        for row in db.execute("SELECT DISTINCT book_id FROM reservations WHERE status IN ('active','notified')").fetchall():
            service.publish_availability(row['book_id'])
        rows = db.execute(
            """SELECT l.id,l.member_id,l.due_on,b.title FROM loans l JOIN books b ON b.id=l.book_id
               JOIN members m ON m.id=l.member_id WHERE l.returned_on IS NULL AND m.is_active=1 AND l.due_on<=?""",
            ((now + timedelta(days=3)).isoformat(),),
        ).fetchall()
        count = 0
        for row in rows:
            overdue = row['due_on'] < now.isoformat()
            kind = 'overdue' if overdue else 'due'
            message = f'“{row["title"]}” için iade tarihi {row["due_on"]}.'
            if overdue:
                message += ' İade süresi geçti.'
            count += service.publish(kind, f'{row["id"]}:{row["due_on"]}', message, [row['member_id']])
    return expired, count
