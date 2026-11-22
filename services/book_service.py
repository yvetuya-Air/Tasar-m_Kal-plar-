"""Kitap doğrulama, Factory Method ile üretim ve SQLite işlemleri."""
import sqlite3
from database import get_db
from models.book import Book
from models.isbn import valid_isbn, normalize_isbn, isbn_variants
from patterns.factory_method import CREATORS
from patterns.adapter import safe_thumbnail
from services.notification_service import NotificationService
from services.validation import record_id, escaped_like


class BookValidationError(ValueError):
    pass


def categories():
    return get_db().execute('SELECT * FROM categories ORDER BY name').fetchall()


def get_book(book_id):
    row = get_db().execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
    return Book.from_row(row) if row else None


def prepare_book(form, existing=None, media=None):
    data = {key: str(form.get(key, '')).strip() for key in ('title','author','isbn','category_id','book_type','total_copies','shelf_location','file_url')}
    if not 1 <= len(data['title']) <= 200 or not 1 <= len(data['author']) <= 160:
        raise BookValidationError('Kitap adı (1–200 karakter) ve yazar (1–160 karakter) zorunludur.')
    isbn = normalize_isbn(data['isbn'])
    if isbn and not valid_isbn(isbn):
        raise BookValidationError('ISBN, kontrol basamağı doğru olan 10 veya 13 karakter içermelidir.')
    try:
        copies = int(data['total_copies'])
        category_id = record_id(data['category_id'],'Kategori') if data['category_id'] else None
    except ValueError as error:
        raise BookValidationError('Adet ve kategori geçerli tamsayı olmalıdır.') from error
    if not 1 <= copies <= 10000:
        raise BookValidationError('Adet veya lisans sayısı 1 ile 10000 arasında olmalıdır.')
    if category_id is not None and not get_db().execute('SELECT 1 FROM categories WHERE id=?', (category_id,)).fetchone():
        raise BookValidationError('Seçilen kategori bulunamadı.')
    creator_class = CREATORS.get(data['book_type'])
    if creator_class is None:
        raise BookValidationError('Geçerli bir kitap türü seçin.')
    metadata = {}
    for field, limit in (('cover_url', 2000), ('description', 10000),
                         ('publisher', 200), ('language', 50), ('publication_year', 4)):
        raw = form.get(field, getattr(existing, field, None))
        value = str(raw).strip() if raw is not None else ''
        if len(value) > limit:
            raise BookValidationError('Bibliyografik alanlardan biri çok uzun.')
        metadata[field] = value or None
    if metadata['cover_url']:
        metadata['cover_url'] = safe_thumbnail(metadata['cover_url'])
        if not metadata['cover_url']:
            raise BookValidationError('Kapak adresi Google Books veya Open Library kaynağından olmalıdır.')
    year = metadata['publication_year']
    if year:
        if not year.isascii() or not year.isdecimal() or int(year) == 0:
            raise BookValidationError('Yayın yılı 1 ile 9999 arasında olmalıdır.')
        metadata['publication_year'] = int(year)
    try:
        return creator_class().prepare_book(
            id=existing.id if existing else None, title=data['title'], author=data['author'],
            isbn=isbn or None, category_id=category_id, total_copies=copies,
            shelf_location=data['shelf_location'] or None, file_url=data['file_url'] or None,
            created_at=existing.created_at if existing else '',
            managed_media=bool(media or (existing and existing.managed_media)), **metadata)
    except ValueError as error:
        raise BookValidationError(str(error)) from error


def has_history(db, book_id):
    return db.execute('SELECT 1 FROM loans WHERE book_id=? UNION ALL SELECT 1 FROM reservations WHERE book_id=? LIMIT 1', (book_id,book_id)).fetchone() is not None


def save_book(form, user_id, book_id=None, media=None):
    db = get_db()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            existing = get_book(book_id) if book_id is not None else None
            if book_id is not None and existing is None:
                raise LookupError('Kitap bulunamadı.')
            if existing and existing.managed_media and (media or form.get('book_type') != existing.book_type):
                raise BookValidationError('Yüklü dosyası olan kitabın dosyası ve türü değiştirilemez.')
            if media and media.mime not in {'ebook': ('application/pdf',), 'audio': ('audio/mpeg', 'audio/wav')}.get(form.get('book_type'), ()):
                raise BookValidationError('Yüklenen dosya kitap türüyle eşleşmiyor.')
            book = prepare_book(form, existing, media)
            variants = isbn_variants(book.isbn)
            if variants:
                placeholders = ','.join('?' for _ in variants)
                duplicate = db.execute(f'SELECT id FROM books WHERE isbn IN ({placeholders}) AND id != ?', (*variants, book_id or -1)).fetchone()
                if duplicate:
                    raise BookValidationError('Bu ISBN zaten kayıtlı. Aynı ISBN-10/ISBN-13 baskısı tekrar eklenemez.')
            if existing and existing.book_type != book.book_type and has_history(db, existing.id):
                raise BookValidationError('Ödünç veya rezervasyon geçmişi olan kitabın türü değiştirilemez.')
            if existing and book.total_copies < existing.total_copies:
                committed = db.execute(
                    """SELECT (SELECT count(*) FROM loans WHERE book_id=? AND returned_on IS NULL) +
                       (SELECT count(*) FROM reservation_holds h JOIN reservations r ON r.id=h.reservation_id
                        WHERE r.book_id=? AND r.status='notified' AND h.expires_at>CURRENT_TIMESTAMP)""",
                    (existing.id, existing.id),
                ).fetchone()[0]
                if book.total_copies < committed:
                    raise BookValidationError('Adet etkin ödünç ve ayrılmış kopya toplamından az olamaz.')
            values = (book.title,book.author,book.isbn,book.category_id,book.book_type,book.total_copies,book.shelf_location,book.file_url)
            values += (book.cover_url, book.description, book.publisher, book.publication_year, book.language, book.managed_media)
            if existing:
                db.execute('UPDATE books SET title=?,author=?,isbn=?,category_id=?,book_type=?,total_copies=?,shelf_location=?,file_url=?,cover_url=?,description=?,publisher=?,publication_year=?,language=?,managed_media=? WHERE id=?', (*values,book_id))
                action = 'book_updated'
            else:
                book_id = db.execute('INSERT INTO books(title,author,isbn,category_id,book_type,total_copies,shelf_location,file_url,cover_url,description,publisher,publication_year,language,managed_media) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values).lastrowid
                action = 'book_created'
            if media:
                db.execute('INSERT INTO book_media(book_id,mime,content,page_count,duration) VALUES(?,?,?,?,?)',
                           (book_id, media.mime, media.content, media.page_count, media.duration))
            db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)', (user_id,action,f'Kitap #{book_id}: {book.title}'))
            if existing:
                NotificationService(db).publish_availability(book_id)
            elif book.category_id is not None:
                subscribers = db.execute(
                    """SELECT DISTINCT m.id FROM members m JOIN member_books f ON f.user_id=m.user_id
                       JOIN books b ON b.id=f.book_id WHERE m.is_active=1 AND b.category_id=?""",
                    (book.category_id,),
                ).fetchall()
                NotificationService(db).publish('new_book', book_id, f'Koleksiyona “{book.title}” eklendi.',
                                                [row['id'] for row in subscribers])
    except sqlite3.IntegrityError as error:
        message = 'Bu ISBN zaten kayıtlı.' if 'books.isbn' in str(error) else 'Kitap kaydedilemedi. Adet aktif ödünç sayısından az olamaz; ilişkili kayıtları kontrol edin.'
        raise BookValidationError(message) from error
    return get_book(book_id)


def delete_book(book_id, user_id):
    db = get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        book = get_book(book_id)
        if book is None:
            raise LookupError('Kitap bulunamadı.')
        if has_history(db, book_id):
            raise BookValidationError('Ödünç veya rezervasyon geçmişi olan kitap silinemez.')
        db.execute('DELETE FROM books WHERE id=?', (book_id,))
        db.execute('INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)', (user_id,'book_deleted',f'Kitap #{book_id}: {book.title}'))


def search_books(query='', page=1, filters=None):
    db = get_db()
    # LIKE jokerleri kullanıcı girdisinde normal karakter olarak aranır.
    pattern = escaped_like(query)
    where = ["(tr_fold(title) LIKE tr_fold(?) ESCAPE '\\' OR tr_fold(author) LIKE tr_fold(?) ESCAPE '\\' OR isbn LIKE ? ESCAPE '\\')"]
    params = [pattern, pattern, pattern]
    filters = filters or {}
    for field in ('title', 'author', 'isbn', 'language'):
        if filters.get(field):
            where.append(f"tr_fold({field}) LIKE tr_fold(?) ESCAPE '\\'")
            params.append(escaped_like(filters[field]))
    for field in ('category_id', 'book_type', 'publication_year'):
        if filters.get(field):
            where.append(f'{field}=?')
            params.append(filters[field])
    availability = {'available': 'available_copies>0', 'unavailable': 'available_copies=0'}
    if filters.get('stock') in availability:
        where.append(availability[filters['stock']])
    where = ' AND '.join(where)
    order = {'title': 'tr_fold(title),id', 'popular': '(SELECT COUNT(*) FROM loans WHERE book_id=book_inventory.id) DESC,id DESC'}
    order_by = order.get(filters.get('sort'), 'id DESC')
    count = db.execute(f'SELECT COUNT(*) FROM book_inventory WHERE {where}', params).fetchone()[0]
    pages = max(1, (count + 19)//20)
    page = min(max(page,1), pages)
    rows = db.execute(f'SELECT * FROM book_inventory WHERE {where} ORDER BY {order_by} LIMIT 20 OFFSET ?', (*params,(page-1)*20)).fetchall()
    return [(Book.from_row(row), row['available_copies']) for row in rows], count, page, pages
