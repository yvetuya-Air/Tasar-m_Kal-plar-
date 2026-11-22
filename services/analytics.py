"""SQLite tabanlı dönem raporları ve gösterge serileri."""
from datetime import date

from database import get_db
from services.loan_service import parse_date, today


def selected_period(values):
    end = parse_date(values.get('end') or today().isoformat())
    start = parse_date(values.get('start') or date.fromordinal(max(1, end.toordinal() - 29)).isoformat())
    if start > end or (end - start).days > 366:
        raise ValueError('Başlangıç ve bitiş arasındaki süre 0–366 gün olmalıdır.')
    return start.isoformat(), end.isoformat()


def dashboard(period):
    db = get_db()
    stats = (
        ('Toplam Kitap', 'SELECT count(*) FROM books', ()),
        ('Fiziksel Kitaplar', "SELECT count(*) FROM books WHERE book_type='physical'", ()),
        ('Elektronik Kitaplar', "SELECT count(*) FROM books WHERE book_type='ebook'", ()),
        ('Sesli Kitaplar', "SELECT count(*) FROM books WHERE book_type='audio'", ()),
        ('Mevcut Kitaplar', 'SELECT count(*) FROM book_inventory WHERE available_copies>0', ()),
        ('Toplam Üye', 'SELECT count(*) FROM members', ()),
        ('Aktif Üyeler', 'SELECT count(*) FROM members WHERE is_active=1', ()),
        ('Aktif Ödünçler', 'SELECT count(*) FROM loans WHERE returned_on IS NULL', ()),
        ('Geciken Kitaplar', 'SELECT count(*) FROM loans WHERE returned_on IS NULL AND due_on<?', (today().isoformat(),)),
        ('Aktif Rezervasyonlar', "SELECT count(*) FROM reservations WHERE status IN ('active','notified')", ()),
        ('Toplam Cezalar (TL)', 'SELECT coalesce(sum(penalty_cents),0)/100.0 FROM loans WHERE returned_on BETWEEN ? AND ?', period),
        ('Yeni Üyeler', 'SELECT count(*) FROM members WHERE date(created_at) BETWEEN ? AND ?', period),
    )
    cards = [(label, db.execute(sql, args).fetchone()[0]) for label, sql, args in stats]

    def chart(label, sql, args=()):
        rows = db.execute(sql, args).fetchall()
        return {'title': label, 'rows': rows, 'total': max((row[1] for row in rows), default=0) or 1}

    charts = []
    groups = {'Günlük Ödünç İşlemleri': '%Y-%m-%d', 'Haftalık Ödünç İşlemleri': '%Y-%W',
              'Aylık Ödünç İşlemleri': '%Y-%m'}
    for label, group in groups.items():
        charts.append(chart(label, 'SELECT strftime(?,borrowed_on) AS period,count(*) FROM loans WHERE borrowed_on BETWEEN ? AND ? GROUP BY period ORDER BY period', (group, *period)))
    charts.extend((
        chart('Kitap Kategorileri', "SELECT coalesce(c.name,'Kategorisiz'),count(*) FROM books b LEFT JOIN categories c ON b.category_id=c.id GROUP BY b.category_id ORDER BY count(*) DESC"),
        chart('En Çok Okunan Kitaplar', 'SELECT b.title,count(*) FROM reading_progress r JOIN books b ON b.id=r.book_id WHERE date(r.updated_at) BETWEEN ? AND ? GROUP BY b.id ORDER BY count(*) DESC,b.id LIMIT 10', period),
        chart('En Çok Ödünç Alınan Kitaplar', 'SELECT b.title,count(*) FROM loans l JOIN books b ON b.id=l.book_id WHERE l.borrowed_on BETWEEN ? AND ? GROUP BY b.id ORDER BY count(*) DESC,b.id LIMIT 10', period),
        chart('En Aktif Üyeler', 'SELECT m.full_name,count(*) FROM loans l JOIN members m ON m.id=l.member_id WHERE l.borrowed_on BETWEEN ? AND ? GROUP BY m.id ORDER BY count(*) DESC,m.id LIMIT 10', period),
        chart('Üye Türleri Dağılımı', "SELECT CASE member_type WHEN 'student' THEN 'Öğrenci' WHEN 'teacher' THEN 'Öğretmen' ELSE 'Normal Üye' END,count(*) FROM members GROUP BY member_type"),
        chart('İade ve Gecikme İstatistikleri', "SELECT CASE WHEN returned_on>due_on THEN 'Gecikmeli iade' ELSE 'Zamanında iade' END,count(*) FROM loans WHERE returned_on BETWEEN ? AND ? GROUP BY returned_on>due_on", period),
        chart('Dijital Okuma İstatistikleri', "SELECT CASE b.book_type WHEN 'audio' THEN 'Sesli Kitap' ELSE 'Elektronik Kitap' END,count(*) FROM reading_progress r JOIN books b ON b.id=r.book_id WHERE date(r.updated_at) BETWEEN ? AND ? GROUP BY b.book_type", period),
        chart('Aylık Ceza İstatistikleri (TL)', 'SELECT substr(returned_on,1,7),sum(penalty_cents)/100.0 FROM loans WHERE returned_on BETWEEN ? AND ? AND penalty_cents>0 GROUP BY 1 ORDER BY 1', period),
    ))
    return cards, charts
