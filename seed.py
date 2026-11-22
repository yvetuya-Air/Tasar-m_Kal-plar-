"""Yalnızca açık komutla yüklenen, gerçek kullanıcı içermeyen gösterim verileri."""
from datetime import date, timedelta
from io import BytesIO
import secrets
from reportlab.pdfgen.canvas import Canvas
from werkzeug.security import generate_password_hash


def install_demo_pdf(db):
    book = db.execute(
        """SELECT b.id FROM books b JOIN categories c ON c.id=b.category_id
           WHERE b.title='Demo E-Kitap' AND b.author='Gösterim Yazarı'
             AND c.name='Gösterim Koleksiyonu' AND b.book_type='ebook'
             AND b.file_url='https://example.invalid/demo.pdf' AND b.managed_media=0""",
    ).fetchone()
    if book is None:
        return
    output = BytesIO()
    pdf = Canvas(output)
    for number in (1, 2):
        pdf.setFont('Helvetica-Bold', 24)
        pdf.drawString(64, 760, 'Dijital Kitap')
        pdf.setFont('Helvetica', 14)
        pdf.drawString(64, 720, f'Deneme PDF belgesi - Sayfa {number}')
        pdf.showPage()
    pdf.save()
    db.execute('UPDATE books SET file_url=NULL,managed_media=1 WHERE id=?', (book['id'],))
    db.execute("INSERT INTO book_media(book_id,mime,content,page_count) VALUES(?,'application/pdf',?,2)",
               (book['id'], output.getvalue()))


def seed_demo(db):
    # Kısmi veya gerçek veriye gösterim kaydı karıştırılmaz.
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM activity_logs WHERE action='demo_seed'").fetchone():
            install_demo_pdf(db)
            return False
        tables = ('users','members','books','categories','loans','reservations','notifications','activity_logs')
        if any(db.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone() for table in tables):
            raise ValueError('Gösterim verileri yalnızca boş veritabanına yüklenebilir.')
        today = date.today()
        # Rastgele parola saklanmaz veya yayımlanmaz; giriş üçüncü aşamadadır.
        db.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',
                   ('demo_yonetici', generate_password_hash(secrets.token_urlsafe(32)), 'admin'))
        for name, email, kind in [('Demo Öğrenci','ogrenci@example.invalid','student'),
                                 ('Demo Öğretmen','ogretmen@example.invalid','teacher'),
                                 ('Demo Normal Üye','uye@example.invalid','standard')]:
            db.execute('INSERT INTO members(full_name,email,member_type) VALUES(?,?,?)', (name,email,kind))
        db.execute("INSERT INTO categories(name) VALUES('Gösterim Koleksiyonu')")
        db.execute("INSERT INTO books(title,author,category_id,book_type,total_copies,shelf_location) VALUES('Demo Fiziksel Kitap','Gösterim Yazarı',1,'physical',1,'A-01')")
        db.execute("INSERT INTO books(title,author,category_id,book_type,total_copies,file_url) VALUES('Demo E-Kitap','Gösterim Yazarı',1,'ebook',2,'https://example.invalid/demo.pdf')")
        db.execute('INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(1,1,?,?)',
                   ((today-timedelta(days=20)).isoformat(),(today-timedelta(days=6)).isoformat()))
        db.execute('INSERT INTO loans(book_id,member_id,borrowed_on,due_on,returned_on) VALUES(2,3,?,?,?)',
                   ((today-timedelta(days=10)).isoformat(),(today+timedelta(days=4)).isoformat(),today.isoformat()))
        db.execute('INSERT INTO reservations(book_id,member_id) VALUES(1,2)')
        db.execute("INSERT INTO notifications(member_id,message) VALUES(2,'Gösterim bildirimi: Bu kayıt gerçek bir kullanılabilirlik olayı değildir.')")
        db.execute("INSERT INTO activity_logs(user_id,action,details) VALUES(1,'demo_seed','Gerçek işlem değildir: gösterim veri kümesi yüklendi.')")
        install_demo_pdf(db)
    return True
