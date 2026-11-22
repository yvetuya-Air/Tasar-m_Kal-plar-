"""Observer sözleşmesi, SQLite abonelikleri ve atomik bildirim testleri."""
from unittest.mock import Mock
import sqlite3
import pytest
from app import create_app
from database import get_db, init_db
from seed import seed_demo
from patterns.observer import Observer, Subject, BookAvailabilitySubject, MemberObserver
from services.notification_service import NotificationService
from services import loan_service, book_service, reservation_service


class RecordingObserver(Observer):
    def __init__(self, events):
        self.events = events

    def update(self, book_id, title):
        self.events.append((book_id,title))
        return True


def test_abstract_contracts():
    for cls in (Observer,Subject):
        with pytest.raises(TypeError):
            cls()


def test_attach_detach_and_notify():
    events=[]
    observer=RecordingObserver(events)
    subject=BookAvailabilitySubject(7,'Kitap')
    subject.attach(observer)
    subject.attach(observer)
    assert subject.notify()==1 and events==[(7,'Kitap')]
    subject.detach(observer)
    subject.detach(observer)
    assert subject.notify()==0
    with pytest.raises(TypeError):
        subject.attach(object())


def test_member_observer_delegates_to_notification_service():
    service=Mock()
    service.notify_reserved_member.return_value=True
    assert MemberObserver(12,service).update(7,'Kitap')
    service.notify_reserved_member.assert_called_once_with(12,7,'Kitap')


def test_notify_uses_snapshot_of_subscribers():
    events=[]
    subject=BookAvailabilitySubject(1,'Kitap')
    second=RecordingObserver(events)
    class DetachingObserver(Observer):
        def update(self,book_id,title):
            subject.detach(second)
            return True
    subject.attach(DetachingObserver())
    subject.attach(second)
    assert subject.notify()==2 and events==[(1,'Kitap')]
    assert subject.notify()==1


@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'observer-test','DATABASE':str(tmp_path/'observer.sqlite3')})
    with app.app_context():
        init_db()
        seed_demo(get_db())
    return app


def publish(db,book_id=1):
    with db:
        db.execute('BEGIN IMMEDIATE')
        return NotificationService(db).publish_availability(book_id)


def test_return_reserved_book_automatically_notifies(app):
    with app.app_context():
        db=get_db()
        loan_service.return_loan(1,1)
        row=db.execute('SELECT * FROM notifications WHERE reservation_id=1').fetchone()
        assert row and row['member_id']==2 and row['is_read']==0
        assert '48 saat ayrıldı' in row['message']
        assert db.execute('SELECT status FROM reservations WHERE id=1').fetchone()[0]=='notified'
        assert db.execute('SELECT available_copies FROM book_inventory WHERE id=1').fetchone()[0]==1


def test_repeat_publication_and_unique_database_constraint(app):
    with app.app_context():
        db=get_db()
        loan_service.return_loan(1,1)
        assert publish(db)==0
        assert publish(db)==0
        assert db.execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=1').fetchone()[0]==1
        with pytest.raises(sqlite3.IntegrityError):
            with db:
                db.execute("INSERT INTO notifications(member_id,reservation_id,message) VALUES(2,1,'Tekrar')")


def test_no_available_copy_no_notification(app):
    with app.app_context():
        assert publish(get_db())==0
        assert get_db().execute('SELECT COUNT(*) FROM notifications WHERE reservation_id IS NOT NULL').fetchone()[0]==0


def test_cancelled_and_inactive_subscribers_are_skipped(app):
    with app.app_context():
        db=get_db()
        with db:
            db.execute('UPDATE members SET is_active=0 WHERE id=2')
        loan_service.return_loan(1,1)
        assert db.execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=1').fetchone()[0]==0
        with db:
            db.execute('UPDATE members SET is_active=1 WHERE id=2')
            db.execute("UPDATE reservations SET status='cancelled' WHERE id=1")
        assert publish(db)==0


def test_subscribers_loaded_in_chronological_order(app,monkeypatch):
    with app.app_context():
        db=get_db()
        next_id=reservation_service.create_reservation(1,3,1)
        with db:
            db.execute('UPDATE books SET total_copies=2 WHERE id=1')
        seen=[]
        original=MemberObserver.update
        def tracked(self,book_id,title):
            seen.append(self.reservation_id)
            return original(self,book_id,title)
        monkeypatch.setattr(MemberObserver,'update',tracked)
        loan_service.return_loan(1,1)
        assert seen==[1,next_id]
        assert db.execute('SELECT COUNT(*) FROM notifications WHERE reservation_id IS NOT NULL').fetchone()[0]==2


def test_notification_failure_rolls_back_return_penalty_stock_and_log(app):
    with app.app_context():
        db=get_db()
        with db:
            db.execute("CREATE TRIGGER fail_notification BEFORE INSERT ON notifications WHEN NEW.reservation_id IS NOT NULL BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with pytest.raises(sqlite3.IntegrityError):
            loan_service.return_loan(1,1)
        row=db.execute('SELECT returned_on,penalty_cents FROM loans WHERE id=1').fetchone()
        assert row['returned_on'] is None and row['penalty_cents']==0
        assert db.execute('SELECT available_copies FROM book_inventory WHERE id=1').fetchone()[0]==0
        assert db.execute('SELECT status FROM reservations WHERE id=1').fetchone()[0]=='active'
        assert db.execute("SELECT COUNT(*) FROM activity_logs WHERE action='loan_returned'").fetchone()[0]==0


def test_partial_notification_failure_rolls_back_all_subscribers(app):
    with app.app_context():
        db=get_db()
        reservation_service.create_reservation(1,3,1)
        with db:
            db.execute('UPDATE books SET total_copies=2 WHERE id=1')
            db.execute("CREATE TRIGGER fail_second_notification BEFORE INSERT ON notifications WHEN NEW.member_id=3 BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with pytest.raises(sqlite3.IntegrityError):
            loan_service.return_loan(1,1)
        assert db.execute('SELECT COUNT(*) FROM notifications WHERE reservation_id IS NOT NULL').fetchone()[0]==0
        assert {r[0] for r in db.execute('SELECT status FROM reservations')}=={'active'}


def test_stock_increase_also_emits_availability_event(app):
    with app.app_context():
        form={'title':'Demo Fiziksel Kitap','author':'Gösterim Yazarı','book_type':'physical','total_copies':'2','shelf_location':'A-01'}
        book_service.save_book(form,1,1)
        assert get_db().execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=1').fetchone()[0]==1
        book_service.save_book(form,1,1)
        assert get_db().execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=1').fetchone()[0]==1


def test_publication_requires_caller_transaction(app):
    with app.app_context():
        with pytest.raises(RuntimeError):
            NotificationService(get_db()).publish_availability(1)


def test_two_concurrent_publications_do_not_duplicate(app):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    with app.app_context():
        db=get_db()
        # Olay yayınlanmadan önce doğrudan SQL ile mevcut hale getirilir.
        with db:
            db.execute("UPDATE loans SET returned_on=? WHERE id=1",(loan_service.today().isoformat(),))
    barrier=Barrier(2)
    def attempt(_):
        with app.app_context():
            barrier.wait(timeout=5)
            return publish(get_db())
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(attempt,[1,2]))==[0,1]
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=1').fetchone()[0]==1
