"""Ödünç/iade, atomik işlem, stok, Strategy ve yetkilendirme testleri."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
import re
import sqlite3
import pytest
from app import create_app
from database import get_db, init_db
from seed import seed_demo
from services import loan_service
from services.demo_accounts import prepare_demo_accounts, DEMO_ADMIN_PASSWORD, DEMO_MEMBER_PASSWORD


@pytest.fixture
def app(tmp_path,monkeypatch):
    app=create_app({'TESTING':True,'SECRET_KEY':'loans-test','DATABASE':str(tmp_path/'loans.sqlite3')})
    monkeypatch.setattr(loan_service,'today',lambda:date(2026,11,17))
    with app.app_context():
        init_db()
        seed_demo(get_db())
        prepare_demo_accounts(get_db())
    return app


def csrf(client,path='/giris'):
    return re.search(rb'name="csrf_token" value="([^"]+)"',client.get(path).data).group(1).decode()


def login(app,role='admin'):
    client=app.test_client()
    result=client.post('/giris',data={'csrf_token':csrf(client),'username':'demo_yonetici' if role=='admin' else 'demo_uye',
                                    'password':DEMO_ADMIN_PASSWORD if role=='admin' else DEMO_MEMBER_PASSWORD})
    assert result.status_code==302
    return client


def add_loan(db,member_id=1,due='2026-11-12'):
    with db:
        return db.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(2,?,'2026-11-01',?)",(member_id,due)).lastrowid


def test_borrow_and_return_stock(app):
    with app.app_context():
        db=get_db()
        before=db.execute('SELECT available_copies FROM book_inventory WHERE id=2').fetchone()[0]
        loan_id=loan_service.borrow_book(2,1,'2026-11-20',1)
        assert db.execute('SELECT available_copies FROM book_inventory WHERE id=2').fetchone()[0]==before-1
        loan=loan_service.return_loan(loan_id,1)
        assert loan.returned_on=='2026-11-17' and loan.penalty_cents==0
        assert db.execute('SELECT available_copies FROM book_inventory WHERE id=2').fetchone()[0]==before
        assert db.execute("SELECT COUNT(*) FROM activity_logs WHERE action IN ('loan_created','loan_returned')").fetchone()[0]==2


@pytest.mark.parametrize('member_id,cents',[(1,1000),(2,500),(3,2500)])
def test_late_return_uses_member_type_from_db(app,member_id,cents):
    with app.app_context():
        loan_id=add_loan(get_db(),member_id)
        assert loan_service.return_loan(loan_id,1).penalty_cents==cents


@pytest.mark.parametrize('due',['2026-11-17','2026-11-20'])
def test_ontime_and_early_return(app,due):
    with app.app_context():
        loan_id=add_loan(get_db(),due=due)
        assert loan_service.return_loan(loan_id,1).penalty_cents==0


def test_unavailable_book_and_duplicate_active_loan(app):
    with app.app_context():
        with pytest.raises(loan_service.LoanValidationError):
            loan_service.borrow_book(1,2,'2026-11-20',1)
        loan_service.borrow_book(2,1,'2026-11-20',1)
        with pytest.raises(loan_service.LoanValidationError):
            loan_service.borrow_book(2,1,'2026-11-20',1)


@pytest.mark.parametrize('book_id,member_id,due',[(999,1,'2026-11-20'),(2,999,'2026-11-20'),(2,1,'bad'),(2,1,'2026-02-30'),(2,1,'2026-11-16')])
def test_invalid_borrow(app,book_id,member_id,due):
    with app.app_context():
        with pytest.raises(loan_service.LoanValidationError):
            loan_service.borrow_book(book_id,member_id,due,1)
        assert get_db().execute('SELECT COUNT(*) FROM loans').fetchone()[0]==2


@pytest.mark.parametrize('table,row_id',[('members',1),('users',2)])
def test_inactive_member_or_account(app,table,row_id):
    with app.app_context():
        with get_db() as db:
            db.execute(f'UPDATE {table} SET is_active=0 WHERE id=?',(row_id,))
        with pytest.raises(loan_service.LoanValidationError):
            loan_service.borrow_book(2,1,'2026-11-20',1)


def test_double_return_does_not_change_stock_or_amount(app):
    with app.app_context():
        db=get_db()
        loan_id=add_loan(db)
        first=loan_service.return_loan(loan_id,1)
        with pytest.raises(loan_service.LoanValidationError):
            loan_service.return_loan(loan_id,1)
        assert db.execute('SELECT penalty_cents FROM loans WHERE id=?',(loan_id,)).fetchone()[0]==first.penalty_cents
        assert db.execute('SELECT available_copies FROM book_inventory WHERE id=2').fetchone()[0]==2
        assert db.execute("SELECT COUNT(*) FROM activity_logs WHERE action='loan_returned'").fetchone()[0]==1


@pytest.mark.parametrize('action',['loan_created','loan_returned'])
def test_log_failure_rolls_back_entire_transaction(app,action):
    with app.app_context():
        db=get_db()
        loan_id=add_loan(db) if action=='loan_returned' else None
        with db:
            db.execute(f"CREATE TRIGGER fail_log BEFORE INSERT ON activity_logs WHEN NEW.action='{action}' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        before=db.execute('SELECT available_copies FROM book_inventory WHERE id=2').fetchone()[0]
        with pytest.raises((sqlite3.IntegrityError,loan_service.LoanValidationError)):
            if loan_id:
                loan_service.return_loan(loan_id,1)
            else:
                loan_service.borrow_book(2,1,'2026-11-20',1)
        assert db.execute('SELECT available_copies FROM book_inventory WHERE id=2').fetchone()[0]==before
        if loan_id:
            row=db.execute('SELECT returned_on,penalty_cents FROM loans WHERE id=?',(loan_id,)).fetchone()
            assert row['returned_on'] is None and row['penalty_cents']==0


def test_current_member_type_and_saved_final_amount(app):
    with app.app_context():
        db=get_db()
        loan_id=add_loan(db)
        with db:
            db.execute("UPDATE members SET member_type='teacher' WHERE id=1")
        assert loan_service.return_loan(loan_id,1).penalty_cents==500
        with db:
            db.execute("UPDATE members SET member_type='standard' WHERE id=1")
        items,*_=loan_service.list_loans(status='returned')
        saved=next(item for item in items if item['row']['id']==loan_id)
        assert saved['penalty_cents']==500 and saved['final']


def test_return_really_uses_replaceable_strategy(app,monkeypatch):
    from decimal import Decimal
    from patterns.strategy import PenaltyStrategy
    calls=[]
    class TestPenalty(PenaltyStrategy):
        def calculate(self,days_late):
            calls.append(days_late)
            return Decimal('3.00')*days_late
    monkeypatch.setitem(loan_service.PENALTY_STRATEGIES,'student',TestPenalty)
    with app.app_context():
        loan_id=add_loan(get_db())
        assert loan_service.return_loan(loan_id,1).penalty_cents==1500
        assert calls==[5]


def test_member_without_profile_has_no_loan_access(app):
    with app.app_context():
        with get_db() as db:
            db.execute('UPDATE members SET user_id=NULL WHERE user_id=2')
    response=login(app,'member').get('/odunc?status=all')
    assert response.status_code==200
    assert 'Ödünç kaydı bulunamadı'.encode() in response.data
    assert 'Demo Öğrenci'.encode() not in response.data


def test_concurrent_borrow_last_copy(app):
    with app.app_context():
        with get_db() as db:
            db.execute('UPDATE books SET total_copies=1 WHERE id=2')
    barrier=Barrier(2)
    def attempt(member_id):
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                loan_service.borrow_book(2,member_id,'2026-11-20',1)
                return True
            except loan_service.LoanValidationError:
                return False
    with ThreadPoolExecutor(max_workers=2) as workers:
        results=list(workers.map(attempt,[1,2]))
    assert sorted(results)==[False,True]
    with app.app_context():
        assert get_db().execute('SELECT available_copies FROM book_inventory WHERE id=2').fetchone()[0]==0


def test_concurrent_double_return(app):
    with app.app_context():
        loan_id=add_loan(get_db())
    barrier=Barrier(2)
    def attempt(_):
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                loan_service.return_loan(loan_id,1)
                return True
            except loan_service.LoanValidationError:
                return False
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(attempt,[1,2]))==[False,True]


def test_http_borrow_return_ignores_client_penalty_and_date(app):
    client=login(app)
    result=client.post('/odunc/ver',data={'csrf_token':csrf(client,'/odunc/ver'),'book_id':'2','member_id':'2','due_on':'2026-11-20'})
    assert result.status_code==302
    with app.app_context():
        loan_id=get_db().execute('SELECT MAX(id) FROM loans').fetchone()[0]
    result=client.post(f'/odunc/{loan_id}/iade',data={'csrf_token':csrf(client,'/odunc'),'penalty_cents':'999999','member_type':'standard','returned_on':'2099-01-01'})
    assert result.status_code==302
    with app.app_context():
        row=get_db().execute('SELECT * FROM loans WHERE id=?',(loan_id,)).fetchone()
        assert row['returned_on']=='2026-11-17' and row['penalty_cents']==0


def test_member_own_history_only(app):
    client=login(app,'member')
    result=client.get('/odunc?status=all&member_id=3')
    assert result.status_code==200
    assert 'Demo Öğrenci'.encode() in result.data
    assert 'Demo Normal Üye'.encode() not in result.data
    assert client.get('/odunc/ver').status_code==403
    assert client.post('/odunc/1/iade',data={'csrf_token':csrf(client,'/odunc')}).status_code==403
    assert client.post('/odunc/ver',data={'csrf_token':csrf(client,'/odunc'),'book_id':'2','member_id':'1','due_on':'2026-11-20'}).status_code==403


@pytest.mark.parametrize('path',['/odunc','/odunc/ver','/odunc/1/iade','/odunc/simulator'])
def test_anonymous_access(app,path):
    assert app.test_client().get(path).status_code==302


@pytest.mark.parametrize('path',['/odunc/ver','/odunc/1/iade','/odunc/simulator'])
def test_csrf(app,path):
    assert login(app).post(path,data={}).status_code==400


def test_overdue_and_final_displays(app):
    with app.app_context():
        loan_id=add_loan(get_db(),2)
    client=login(app)
    active=client.get('/odunc').data
    assert '5 gün gecikmiş'.encode() in active
    assert b'5,00 TL' in active
    assert 'Bugünkü tahmin'.encode() in active
    client.post(f'/odunc/{loan_id}/iade',data={'csrf_token':csrf(client,'/odunc')})
    assert 'Kesin tutar'.encode() in client.get('/odunc?status=returned').data
    assert client.post(f'/odunc/{loan_id}/iade',data={'csrf_token':csrf(client,'/odunc')}).status_code==409


def test_simulator_is_pure_and_uses_strategies(app):
    client=login(app,'member')
    for kind,amount in [('student','10,00 TL'),('teacher','5,00 TL'),('standard','25,00 TL')]:
        result=client.post('/odunc/simulator',data={'csrf_token':csrf(client,'/odunc/simulator'),'member_type':kind,'due_on':'2026-11-10','returned_on':'2026-11-15'})
        assert result.status_code==200 and amount.encode() in result.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM loans').fetchone()[0]==2
        assert get_db().execute("SELECT COUNT(*) FROM activity_logs WHERE action LIKE 'loan_%'").fetchone()[0]==0


@pytest.mark.parametrize('kind,due,returned',[('invalid','2026-11-10','2026-11-15'),('student','bad','2026-11-15')])
def test_invalid_simulator(app,kind,due,returned):
    client=login(app)
    assert client.post('/odunc/simulator',data={'csrf_token':csrf(client,'/odunc/simulator'),'member_type':kind,'due_on':due,'returned_on':returned}).status_code==422


def test_missing_loan_and_bad_borrow_form(app):
    client=login(app)
    assert client.get('/odunc/999/iade').status_code==404
    assert client.post('/odunc/999/iade',data={'csrf_token':csrf(client,'/odunc')}).status_code==404
    assert client.post('/odunc/ver',data={'csrf_token':csrf(client,'/odunc'),'book_id':'bad','member_id':'1','due_on':'2026-11-20'}).status_code==422
