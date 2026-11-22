"""Ödünç/iade işlemleri ve Strategy ile kesin ceza kaydı."""
from datetime import date, datetime, timedelta, timezone
import sqlite3
from database import get_db
from models.loan import Loan
from patterns.strategy import PENALTY_STRATEGIES, PenaltyCalculator
from services.notification_service import NotificationService
from services.reservation_service import eligible_queue
from services.validation import record_id
from services.circulation_policy import ConfiguredPenalty, configured_policy, display_policy


class LoanValidationError(ValueError):
    pass


def today():
    # Türkiye güncel takvim günü; Windows zoneinfo paketinden bağımsızdır.
    return datetime.now(timezone(timedelta(hours=3))).date()


def parse_date(value):
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError
        return result
    except (ValueError,TypeError):
        raise LoanValidationError('Geçerli bir tarih girin (YYYY-AA-GG).') from None


def penalty_for(member_type, due_on, returned_on):
    strategy = PENALTY_STRATEGIES.get(member_type)
    if strategy is None:
        raise LoanValidationError('Geçerli bir üye türü seçin.')
    policy = configured_policy(member_type)
    calculator = PenaltyCalculator(ConfiguredPenalty(policy) if policy else strategy())
    return calculator.overdue_days(due_on,returned_on), calculator.calculate(due_on,returned_on)


def borrow_book(book_id, member_id, due_on, user_id):
    try:
        book_id,member_id = record_id(book_id,'Kitap'),record_id(member_id,'Üye')
    except ValueError as error:
        raise LoanValidationError(str(error)) from None
    due = parse_date(due_on)
    borrowed = today()
    if due < borrowed:
        raise LoanValidationError('Son teslim tarihi ödünç tarihinden önce olamaz.')
    db = get_db()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            member = db.execute('SELECT * FROM members WHERE id=?',(member_id,)).fetchone()
            book = db.execute('SELECT * FROM book_inventory WHERE id=?',(book_id,)).fetchone()
            if member is None or book is None:
                raise LoanValidationError('Kitap veya üye bulunamadı.')
            if not member['is_active']:
                raise LoanValidationError('Pasif üyeye ödünç verilemez.')
            if member['user_id'] is not None:
                account = db.execute('SELECT is_active FROM users WHERE id=?',(member['user_id'],)).fetchone()
                if not account['is_active']:
                    raise LoanValidationError('Üyenin kullanıcı hesabı pasif.')
            policy = display_policy(member['member_type'])
            if due > borrowed + timedelta(days=policy['loan_days']):
                raise LoanValidationError('Son teslim tarihi izin verilen ödünç süresini aşıyor.')
            if db.execute('SELECT COUNT(*) FROM loans WHERE member_id=? AND returned_on IS NULL',
                          (member_id,)).fetchone()[0] >= policy['max_books']:
                raise LoanValidationError('Üye en fazla izin verilen kitap sayısına ulaştı.')
            if book['available_copies'] <= 0:
                raise LoanValidationError('Bu kitap şu anda mevcut değil.')
            if db.execute('SELECT 1 FROM loans WHERE book_id=? AND member_id=? AND returned_on IS NULL',(book_id,member_id)).fetchone():
                raise LoanValidationError('Üyenin bu kitap için aktif ödüncü zaten var.')
            notifications = NotificationService(db)
            notifications.expire_holds(book_id)
            queue = eligible_queue(db,book_id)
            prioritized = queue[:book['available_copies']]
            reservation = next((row for row in prioritized if row['member_id'] == member_id), None)
            if reservation is None and len(prioritized) >= book['available_copies']:
                raise LoanValidationError('Bu kitap için kronolojik bekleme sırasındaki ilk aktif üyeye öncelik verilir.')
            loan_id = db.execute('INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(?,?,?,?)',
                                 (book_id,member_id,borrowed.isoformat(),due.isoformat())).lastrowid
            if reservation:
                db.execute("UPDATE reservations SET status='fulfilled' WHERE id=?", (reservation['id'],))
                db.execute('DELETE FROM reservation_holds WHERE reservation_id=?', (reservation['id'],))
            notifications.publish_availability(book_id)
            db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)',
                       (user_id,'loan_created',f'Ödünç #{loan_id}; kitap #{book_id}; üye #{member_id}'))
    except sqlite3.IntegrityError as error:
        raise LoanValidationError('Ödünç kaydedilemedi. Stok, üye ve aktif ödünç bilgilerini kontrol edin.') from error
    return loan_id


def loan_details(loan_id):
    return get_db().execute('SELECT l.*,b.title,m.full_name,m.member_type FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id WHERE l.id=?',(loan_id,)).fetchone()


def return_loan(loan_id, user_id):
    db = get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = loan_details(loan_id)
        if row is None:
            raise LookupError('Ödünç kaydı bulunamadı.')
        if row['returned_on'] is not None:
            raise LoanValidationError('Bu kitap zaten iade edilmiş.')
        returned = today()
        if returned < parse_date(row['borrowed_on']):
            raise LoanValidationError('İade tarihi ödünç tarihinden önce olamaz.')
        days, amount = penalty_for(row['member_type'], parse_date(row['due_on']), returned)
        cents = int(amount * 100)
        cursor = db.execute('UPDATE loans SET returned_on=?,penalty_cents=? WHERE id=? AND returned_on IS NULL',
                            (returned.isoformat(),cents,loan_id))
        if cursor.rowcount != 1:
            raise LoanValidationError('Bu kitap zaten iade edilmiş.')
        db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)',
                   (user_id,'loan_returned',f'Ödünç #{loan_id}; {days} gün gecikme; {cents} kuruş; üye türü: {row["member_type"]}'))
        notifications = NotificationService(db)
        if cents:
            notifications.publish('penalty', loan_id, f'“{row["title"]}” iadesinde {amount:.2f} TL gecikme cezası kaydedildi.',
                                  [row['member_id']])
        notifications.expire_holds(row['book_id'])
        notifications.publish_availability(row['book_id'])
    return Loan.from_row(db.execute('SELECT * FROM loans WHERE id=?',(loan_id,)).fetchone())


def renew_loan(loan_id, user):
    db = get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT l.*,m.user_id,m.member_type FROM loans l JOIN members m ON m.id=l.member_id WHERE l.id=?',
                         (loan_id,)).fetchone()
        if row is None or (user.role != 'admin' and row['user_id'] != user.id):
            raise LookupError
        current_due = parse_date(row['due_on'])
        if row['returned_on'] or current_due < today():
            raise LoanValidationError('İade edilmiş veya gecikmiş ödünç yenilenemez.')
        NotificationService(db).expire_holds(row['book_id'])
        if any(waiting['member_id'] != row['member_id'] for waiting in eligible_queue(db, row['book_id'])):
            raise LoanValidationError('Kitabı bekleyen başka bir üye var.')
        policy = display_policy(row['member_type'])
        count = db.execute('SELECT COUNT(*) FROM loan_renewals WHERE loan_id=?', (loan_id,)).fetchone()[0]
        if count >= policy['renewals']:
            raise LoanValidationError('Yenileme hakkı kalmadı.')
        new_due = (current_due + timedelta(days=policy['loan_days'])).isoformat()
        db.execute('UPDATE loans SET due_on=? WHERE id=?', (new_due, loan_id))
        db.execute('INSERT INTO loan_renewals(loan_id,old_due_on,new_due_on) VALUES(?,?,?)',
                   (loan_id, row['due_on'], new_due))
        db.execute("INSERT INTO activity_logs(user_id,action,details) VALUES(?,'loan_renewed',?)",
                   (user.id, f'Ödünç #{loan_id}: {new_due}'))


def list_loans(member_id=None, only_member=False, status='active', page=1):
    db = get_db()
    clauses, params = [], []
    if only_member:
        clauses.append('l.member_id=?')
        params.append(member_id if member_id is not None else -1)
    if status == 'active':
        clauses.append('l.returned_on IS NULL')
    elif status == 'returned':
        clauses.append('l.returned_on IS NOT NULL')
    where = ' AND '.join(clauses) or '1=1'
    count = db.execute(f'SELECT COUNT(*) FROM loans l WHERE {where}',params).fetchone()[0]
    pages = max(1,(count+19)//20)
    page = min(max(page,1),pages)
    rows = db.execute(f'SELECT l.*,b.title,m.full_name,m.member_type FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id WHERE {where} ORDER BY l.id DESC LIMIT 20 OFFSET ?',(*params,(page-1)*20)).fetchall()
    items = []
    for row in rows:
        final = row['returned_on'] is not None
        # İade edilmiş kayıtta güncel strateji yerine kaydedilmiş kesin tutar gösterilir.
        if final:
            days = PenaltyCalculator.overdue_days(parse_date(row['due_on']),parse_date(row['returned_on']))
            cents = row['penalty_cents']
        else:
            days, amount = penalty_for(row['member_type'],parse_date(row['due_on']),today())
            cents = int(amount*100)
        renewals = db.execute('SELECT old_due_on,new_due_on FROM loan_renewals WHERE loan_id=? ORDER BY id', (row['id'],)).fetchall()
        items.append({'row':row,'days_late':days,'penalty_cents':cents, 'final':final,'renewals':renewals})
    return items,count,page,pages


def borrowing_choices():
    db = get_db()
    books = db.execute('SELECT id,title,available_copies FROM book_inventory WHERE available_copies>0 ORDER BY title').fetchall()
    members = db.execute('SELECT m.id,m.full_name,m.member_type FROM members m LEFT JOIN users u ON u.id=m.user_id WHERE m.is_active=1 AND (u.id IS NULL OR u.is_active=1) ORDER BY m.full_name').fetchall()
    return books,members
