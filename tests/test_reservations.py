"""Rezervasyon sırası, özel bildirimler, izinler ve yarış koşulları."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
import re
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from database import get_db, init_db
from seed import seed_demo
from services import reservation_service, loan_service, notification_service
from services.demo_accounts import prepare_demo_accounts, DEMO_ADMIN_PASSWORD, DEMO_MEMBER_PASSWORD


@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'reservations-test','DATABASE':str(tmp_path/'reservations.sqlite3')})
    with app.app_context():
        init_db()
        db=get_db()
        seed_demo(db)
        prepare_demo_accounts(db)
        with db:
            user_id=db.execute("INSERT INTO users(username,password_hash,role) VALUES('test_teacher',?,'member')",(generate_password_hash('TeacherTest!2026'),)).lastrowid
            db.execute('UPDATE members SET user_id=? WHERE id=2',(user_id,))
    return app


def csrf(client,path='/giris'):
    return re.search(rb'name="csrf_token" value="([^"]+)"',client.get(path).data).group(1).decode()


def login(app,role='admin'):
    username,password={'admin':('demo_yonetici',DEMO_ADMIN_PASSWORD),'student':('demo_uye',DEMO_MEMBER_PASSWORD),'teacher':('test_teacher','TeacherTest!2026')}[role]
    client=app.test_client()
    assert client.post('/giris',data={'csrf_token':csrf(client),'username':username,'password':password}).status_code==302
    return client


def due():
    return (loan_service.today()+timedelta(days=14)).isoformat()


def test_create_cancel_and_resubscribe(app):
    with app.app_context():
        db=get_db()
        reservation_id=reservation_service.create_reservation(1,3,1)
        items,*_=reservation_service.list_reservations()
        assert next(item['position'] for item in items if item['row']['id']==reservation_id)==2
        reservation_service.cancel_reservation(reservation_id,1,admin=True)
        assert db.execute('SELECT status FROM reservations WHERE id=?',(reservation_id,)).fetchone()[0]=='cancelled'
        replacement=reservation_service.create_reservation(1,3,1)
        assert replacement>reservation_id


@pytest.mark.parametrize('book_id,member_id',[(2,3),(1,2),(1,1),(999,3),(1,999)])
def test_invalid_reservations(app,book_id,member_id):
    with app.app_context():
        with pytest.raises(reservation_service.ReservationValidationError):
            reservation_service.create_reservation(book_id,member_id,1)
        assert get_db().execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==1


def test_inactive_member_and_account(app):
    with app.app_context():
        db=get_db()
        with db:
            db.execute('UPDATE members SET is_active=0 WHERE id=3')
        with pytest.raises(reservation_service.ReservationValidationError):
            reservation_service.create_reservation(1,3,1)
        with db:
            db.execute('UPDATE users SET is_active=0 WHERE id=(SELECT user_id FROM members WHERE id=2)')
        loan_service.return_loan(1,1)
        assert db.execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=1').fetchone()[0]==0


def test_fifo_borrow_fulfills_reservation_and_preserves_stock(app):
    with app.app_context():
        db=get_db()
        second=reservation_service.create_reservation(1,3,1)
        loan_service.return_loan(1,1)
        with pytest.raises(loan_service.LoanValidationError):
            loan_service.borrow_book(1,3,due(),1)
        loan_id=loan_service.borrow_book(1,2,due(),1)
        assert db.execute('SELECT status FROM reservations WHERE id=1').fetchone()[0]=='fulfilled'
        assert db.execute('SELECT available_copies FROM book_inventory WHERE id=1').fetchone()[0]==0
        loan_service.return_loan(loan_id,1)
        assert db.execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=?',(second,)).fetchone()[0]==1
        assert loan_service.borrow_book(1,3,due(),1)>loan_id


def test_cancellation_advances_queue_without_duplicate_notifications(app):
    with app.app_context():
        db=get_db()
        second=reservation_service.create_reservation(1,3,1)
        loan_service.return_loan(1,1)
        reservation_service.cancel_reservation(1,1,admin=True)
        assert db.execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=?',(second,)).fetchone()[0]==1
        assert loan_service.borrow_book(1,3,due(),1)


def test_cancel_before_return_prevents_notification(app):
    with app.app_context():
        reservation_service.cancel_reservation(1,1,admin=True)
        loan_service.return_loan(1,1)
        assert get_db().execute('SELECT COUNT(*) FROM notifications WHERE reservation_id=1').fetchone()[0]==0


def test_double_cancel_and_foreign_owner(app):
    with app.app_context():
        with pytest.raises(LookupError):
            reservation_service.cancel_reservation(1,2,owner_member_id=1)
        reservation_service.cancel_reservation(1,1,admin=True)
        with pytest.raises(reservation_service.ReservationValidationError):
            reservation_service.cancel_reservation(1,1,admin=True)


def test_cancel_failure_rolls_back_status(app):
    import sqlite3
    with app.app_context():
        db=get_db()
        with db:
            db.execute("CREATE TRIGGER fail_cancel BEFORE INSERT ON activity_logs WHEN NEW.action='reservation_cancelled' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with pytest.raises(sqlite3.IntegrityError):
            reservation_service.cancel_reservation(1,1,admin=True)
        assert db.execute('SELECT status FROM reservations WHERE id=1').fetchone()[0]=='active'


def test_reservation_log_failure_rolls_back_new_row(app):
    with app.app_context():
        db=get_db()
        with db:
            db.execute("CREATE TRIGGER fail_reservation BEFORE INSERT ON activity_logs WHEN NEW.action='reservation_created' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with pytest.raises(reservation_service.ReservationValidationError):
            reservation_service.create_reservation(1,3,1)
        assert db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==1


def test_inactive_first_member_does_not_block_active_queue(app):
    with app.app_context():
        db=get_db()
        reservation_service.create_reservation(1,3,1)
        with db:
            db.execute('UPDATE members SET is_active=0 WHERE id=2')
        loan_service.return_loan(1,1)
        assert loan_service.borrow_book(1,3,due(),1)


def test_member_without_profile_cannot_create_reservation(app):
    with app.app_context():
        with get_db() as db:
            db.execute('UPDATE members SET user_id=NULL WHERE user_id=2')
    student=login(app,'student')
    assert student.get('/rezervasyonlar/ekle').status_code==403
    assert student.get('/rezervasyonlar').status_code==200


def test_queue_order_uses_time_then_id(app):
    with app.app_context():
        db=get_db()
        second=reservation_service.create_reservation(1,3,1)
        with db:
            db.execute("UPDATE reservations SET created_at='2000-01-01 00:00:00' WHERE id=?",(second,))
        assert [r['id'] for r in reservation_service.eligible_queue(db,1)]==[second,1]
        with db:
            db.execute("UPDATE reservations SET created_at='2000-01-01 00:00:00'")
        assert [r['id'] for r in reservation_service.eligible_queue(db,1)]==[1,second]


def test_concurrent_duplicate_reservations(app):
    barrier=Barrier(2)
    def attempt(_):
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                reservation_service.create_reservation(1,3,1)
                return True
            except reservation_service.ReservationValidationError:
                return False
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(attempt,[1,2]))==[False,True]


def test_private_notifications_and_read_badge(app):
    with app.app_context():
        loan_service.return_loan(1,1)
        notification_id=get_db().execute('SELECT id FROM notifications WHERE reservation_id=1').fetchone()[0]
    teacher=login(app,'teacher')
    page=teacher.get('/bildirimler')
    assert page.status_code==200 and '2 okunmamış'.encode() in page.data
    assert '48 saat ayrıldı'.encode() in page.data
    token=csrf(teacher,'/bildirimler')
    assert teacher.post(f'/bildirimler/{notification_id}/oku',data={'csrf_token':token}).status_code==302
    assert '1 okunmamış'.encode() in teacher.get('/bildirimler').data
    assert teacher.post(f'/bildirimler/{notification_id}/oku',data={'csrf_token':token}).status_code==302
    for role in ('student','admin'):
        stranger=login(app,role)
        assert '48 saat ayrıldı'.encode() not in stranger.get('/bildirimler').data
        assert stranger.post(f'/bildirimler/{notification_id}/oku',data={'csrf_token':csrf(stranger,'/bildirimler')}).status_code==404
    with app.app_context():
        assert notification_service.unread_count(2)==1
        assert get_db().execute("""SELECT e.kind FROM notification_events e JOIN notifications n ON n.id=e.notification_id
                                  WHERE n.member_id=1 AND n.is_read=0""").fetchone()['kind']=='penalty'


def test_member_cannot_reserve_for_other_member(app):
    # Öğrenci kendi elindeki kitabı başkasının kimliğiyle rezerve edemez.
    student=login(app,'student')
    result=student.post('/rezervasyonlar/ekle',data={'csrf_token':csrf(student,'/rezervasyonlar'),'book_id':'1','member_id':'3'})
    assert result.status_code==422
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==1


def test_member_reserves_own_profile_and_cancels(app):
    with app.app_context():
        with get_db() as db:
            # Mevcut ikinci kitabın tüm lisansları öğrenci dışındaki üyelerce alınır.
            for member_id in (2,3):
                db.execute('INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(2,?,?,?)',(member_id,loan_service.today().isoformat(),due()))
    student=login(app,'student')
    result=student.post('/rezervasyonlar/ekle',data={'csrf_token':csrf(student,'/rezervasyonlar'),'book_id':'2','member_id':'3'})
    assert result.status_code==302
    with app.app_context():
        row=get_db().execute('SELECT * FROM reservations WHERE book_id=2').fetchone()
        assert row['member_id']==1
        reservation_id=row['id']
    assert student.post(f'/rezervasyonlar/{reservation_id}/iptal',data={'csrf_token':csrf(student,'/rezervasyonlar')}).status_code==302


def test_member_cannot_see_or_cancel_others_reservations(app):
    student=login(app,'student')
    assert 'Demo Öğretmen'.encode() not in student.get('/rezervasyonlar?member_id=2&status=all').data
    assert student.post('/rezervasyonlar/1/iptal',data={'csrf_token':csrf(student,'/rezervasyonlar')}).status_code==404
    teacher=login(app,'teacher')
    assert teacher.post('/rezervasyonlar/1/iptal',data={'csrf_token':csrf(teacher,'/rezervasyonlar')}).status_code==302
    assert teacher.post('/rezervasyonlar/1/iptal',data={'csrf_token':csrf(teacher,'/rezervasyonlar')}).status_code==409


@pytest.mark.parametrize('path',['/rezervasyonlar','/rezervasyonlar/ekle','/bildirimler'])
def test_anonymous_pages(app,path):
    assert app.test_client().get(path).status_code==302


@pytest.mark.parametrize('path',['/rezervasyonlar/ekle','/rezervasyonlar/1/iptal','/bildirimler/1/oku'])
def test_csrf_and_no_get_mutation(app,path):
    client=login(app)
    assert client.post(path,data={}).status_code==400
    if path!='/rezervasyonlar/ekle':
        assert client.get(path).status_code==405
