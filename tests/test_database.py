import sqlite3
from dataclasses import FrozenInstanceError
import pytest
from app import create_app
from database import get_db, init_db
from seed import seed_demo
from models import Book, Member, Loan, Reservation, Notification, User, Category, ActivityLog


@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'test.sqlite3')})


@pytest.fixture
def db(app):
    with app.app_context():
        init_db()
        db = get_db()
        seed_demo(db)
        yield db


def test_schema_and_integrity(db):
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {'users','members','categories','books','loans','reservations','notifications','activity_logs',
                      'book_media','reading_progress','reading_bookmarks','member_books','member_cards',
                      'circulation_settings','loan_policies','loan_renewals','reservation_holds',
                      'notification_events','notification_preferences','login_attempts','password_resets'}
    assert db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()


@pytest.mark.parametrize('table,model', [('books',Book),('members',Member),('loans',Loan),('reservations',Reservation),('notifications',Notification),('users',User),('categories',Category),('activity_logs',ActivityLog)])
def test_model_mapping(db, table, model):
    instance = model.from_row(db.execute(f'SELECT * FROM {table} LIMIT 1').fetchone())
    assert instance.id == 1
    with pytest.raises(FrozenInstanceError):
        instance.id = 9
    if table == 'users':
        assert instance.password_hash not in repr(instance)


def test_init_and_seed_repeat_without_changes(db):
    before = db.total_changes
    init_db()
    assert seed_demo(db) is False
    assert db.total_changes == before


def test_seed_refuses_nonempty_database(app):
    with app.app_context():
        init_db()
        db = get_db()
        db.execute("INSERT INTO categories(name) VALUES('Gerçek koleksiyon')")
        db.commit()
        with pytest.raises(ValueError):
            seed_demo(db)
        assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0


@pytest.mark.parametrize('sql', [
    "INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(1,2,'2026-11-01','2026-11-20')",
    "INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(999,2,'2026-11-01','2026-11-20')",
    "INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(2,2,'2026-11-20','2026-11-01')",
    "INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(2,2,'yanlış','2026-11-20')",
    "UPDATE loans SET returned_on='2026-11-17' WHERE id=2",
    "UPDATE loans SET book_id=2 WHERE id=1",
    "DELETE FROM loans WHERE id=1",
    "DELETE FROM books WHERE id=1",
    "DELETE FROM members WHERE id=1",
    "INSERT INTO reservations(book_id,member_id) VALUES(2,2)",
    "INSERT INTO reservations(book_id,member_id) VALUES(1,2)",
    "UPDATE loans SET penalty_cents=-1 WHERE id=1",
    "UPDATE books SET total_copies=0 WHERE id=1",
    "UPDATE books SET file_url='x' WHERE id=1",
    "INSERT INTO members(full_name,email,member_type) VALUES('X','x@example.invalid','unknown')",
    "INSERT INTO members(full_name,email,member_type) VALUES('X','OGRENCI@example.invalid','student')",
])
def test_invalid_data_rejected(db, sql):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(sql)


def test_return_updates_derived_stock(db):
    assert db.execute('SELECT available_copies FROM book_inventory WHERE id=1').fetchone()[0] == 0
    db.execute("UPDATE loans SET returned_on=date('now') WHERE id=1")
    assert db.execute('SELECT available_copies FROM book_inventory WHERE id=1').fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE loans SET returned_on=date('now') WHERE id=1")


def test_inactive_member_cannot_borrow(db):
    db.execute('UPDATE members SET is_active=0 WHERE id=2')
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(2,2,'2026-11-01','2026-11-20')")


def test_reduce_stock_below_active_loans(db):
    db.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(2,1,'2026-11-01','2026-11-20')")
    db.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(2,2,'2026-11-01','2026-11-20')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('UPDATE books SET total_copies=1 WHERE id=2')


def test_cli_and_connection_cleanup(app):
    runner = app.test_cli_runner()
    for command in ('init-db','seed-demo','seed-demo','check-db'):
        result = runner.invoke(args=[command])
        assert result.exit_code == 0, result.output
    with app.app_context():
        connection = get_db()
        assert get_db() is connection
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute('SELECT 1')


def test_persistence(app):
    with app.app_context():
        init_db()
        seed_demo(get_db())
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM books').fetchone()[0] == 2
