"""Süreli ayırma, zamanlanmış bildirim ve yenileme."""
from datetime import timedelta

from database import get_db
from services import loan_service, reservation_service
from services.maintenance import refresh_circulation
from test_adapter import app, csrf, login


def test_expiration_gives_copy_to_next_member(app):
    with app.app_context():
        db = get_db()
        second = reservation_service.create_reservation(1, 3, 1)
        loan_service.return_loan(1, 1)
        assert [row[0] for row in db.execute('SELECT reservation_id FROM reservation_holds')] == [1]
        with db:
            db.execute("UPDATE reservation_holds SET expires_at='2000-01-01 00:00:00'")
        assert refresh_circulation()[0] == 1
        assert [row[0] for row in db.execute('SELECT reservation_id FROM reservation_holds')] == [second]
        assert refresh_circulation() == (0, 0)
        assert db.execute("SELECT count(*) FROM notification_events WHERE kind='expired'").fetchone()[0] == 1


def test_member_renewal_and_history(app):
    member = login(app, 'member')
    with app.app_context():
        db = get_db()
        member_id = db.execute('SELECT id FROM members WHERE user_id IS NOT NULL').fetchone()[0]
        due = loan_service.today() + timedelta(days=2)
        loan = loan_service.borrow_book(2, member_id, due.isoformat(), 1)
    token = csrf(member, '/odunc')
    for _ in range(2):
        assert member.post(f'/odunc/{loan}/yenile', data={'csrf_token': token}).status_code == 302
    with app.app_context():
        rows = get_db().execute('SELECT old_due_on,new_due_on FROM loan_renewals WHERE loan_id=?', (loan,)).fetchall()
        assert [tuple(row) for row in rows] == [(due.isoformat(), (due + timedelta(days=14)).isoformat())]
