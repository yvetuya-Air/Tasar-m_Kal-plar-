"""İşaretli gösterim veritabanı için iki yerel deneme hesabı."""
from werkzeug.security import generate_password_hash

DEMO_ADMIN_PASSWORD = 'DemoYonetici!2026'
DEMO_MEMBER_PASSWORD = 'DemoUye!2026'


def prepare_demo_reading(db):
    from datetime import timedelta
    from services.circulation_policy import display_policy
    from services.loan_service import borrow_book, today

    row = db.execute(
        """SELECT b.id AS book_id,m.id AS member_id,m.member_type,a.id AS admin_id
           FROM books b JOIN categories c ON c.id=b.category_id
           JOIN book_media d ON d.book_id=b.id AND d.mime='application/pdf'
           JOIN members m ON m.email='ogrenci@example.invalid' AND m.is_active=1
           JOIN users u ON u.id=m.user_id AND u.username='demo_uye' AND u.role='member' AND u.is_active=1
           JOIN users a ON a.username='demo_yonetici' AND a.role='admin' AND a.is_active=1
           WHERE b.title='Demo E-Kitap' AND b.author='Gösterim Yazarı'
             AND c.name='Gösterim Koleksiyonu' AND b.book_type='ebook'
             AND EXISTS(SELECT 1 FROM activity_logs WHERE action='demo_auth_seed')""",
    ).fetchone()
    if row is None:
        raise ValueError('Gösterim PDF dosyası ve demo hesapları bulunamadı.')
    active = db.execute('SELECT id FROM loans WHERE book_id=? AND member_id=? AND returned_on IS NULL',
                        (row['book_id'], row['member_id'])).fetchone()
    if active:
        return active['id']
    days = min(7, display_policy(row['member_type'])['loan_days'])
    return borrow_book(row['book_id'], row['member_id'], (today() + timedelta(days=days)).isoformat(), row['admin_id'])


def prepare_demo_accounts(db):
    with db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute("SELECT 1 FROM activity_logs WHERE action='demo_seed'").fetchone():
            raise ValueError('Önce boş veritabanında seed-demo komutunu çalıştırın.')
        if db.execute("SELECT 1 FROM activity_logs WHERE action='demo_auth_seed'").fetchone():
            return False
        admin = db.execute("SELECT * FROM users WHERE username='demo_yonetici'").fetchone()
        member = db.execute("SELECT * FROM members WHERE email='ogrenci@example.invalid'").fetchone()
        if not admin or admin['role'] != 'admin' or not member or member['user_id'] is not None or db.execute("SELECT 1 FROM users WHERE username='demo_uye'").fetchone():
            raise ValueError('Gösterim hesapları beklenen durumda değil; mevcut hesaplar değiştirilmedi.')
        db.execute('UPDATE users SET password_hash=? WHERE id=?',
                   (generate_password_hash(DEMO_ADMIN_PASSWORD), admin['id']))
        cursor = db.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',
                            ('demo_uye', generate_password_hash(DEMO_MEMBER_PASSWORD), 'member'))
        db.execute('UPDATE members SET user_id=? WHERE id=?', (cursor.lastrowid, member['id']))
        db.execute("INSERT INTO activity_logs(user_id,action,details) VALUES(?,'demo_auth_seed','Yerel gösterim hesapları hazırlandı; gerçek kullanım için değildir.')", (admin['id'],))
    return True
