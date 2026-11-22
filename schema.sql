BEGIN;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE CHECK(length(trim(username))>0),
 password_hash TEXT NOT NULL CHECK(length(password_hash)>0),
 role TEXT NOT NULL CHECK(role IN ('admin','member')),
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 session_version INTEGER NOT NULL DEFAULT 0 CHECK(typeof(session_version)='integer' AND session_version>=0)
);
CREATE TABLE IF NOT EXISTS members (
 id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
 full_name TEXT NOT NULL CHECK(length(trim(full_name))>0),
 email TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(trim(email))>0),
 member_type TEXT NOT NULL CHECK(member_type IN ('student','teacher','standard')),
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS categories (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE CHECK(length(trim(name))>0)
);
CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL CHECK(length(trim(title))>0),
 author TEXT NOT NULL CHECK(length(trim(author))>0), isbn TEXT UNIQUE,
 category_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
 book_type TEXT NOT NULL CHECK(book_type IN ('physical','ebook','audio')),
 total_copies INTEGER NOT NULL DEFAULT 1 CHECK(typeof(total_copies)='integer' AND total_copies>=1),
 shelf_location TEXT, file_url TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 cover_url TEXT, description TEXT, publisher TEXT, publication_year INTEGER, language TEXT,
 managed_media INTEGER NOT NULL DEFAULT 0 CHECK(managed_media IN (0,1)),
 CHECK((book_type='physical' AND shelf_location IS NOT NULL AND length(trim(shelf_location))>0 AND file_url IS NULL AND managed_media=0)
 OR (book_type='ebook' AND shelf_location IS NULL AND ((managed_media=0 AND file_url IS NOT NULL AND length(trim(file_url))>0) OR (managed_media=1 AND file_url IS NULL)))
 OR (book_type='audio' AND managed_media=1 AND shelf_location IS NULL AND file_url IS NULL))
);
CREATE TABLE IF NOT EXISTS book_media (
 book_id INTEGER PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
 mime TEXT NOT NULL CHECK(mime IN ('application/pdf','audio/mpeg','audio/wav')),
 content BLOB NOT NULL CHECK(length(content)>0),
 page_count INTEGER,
 duration REAL
);
CREATE TABLE IF NOT EXISTS reading_progress (
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 book_id INTEGER NOT NULL REFERENCES book_media(book_id) ON DELETE CASCADE,
 position REAL NOT NULL CHECK(position>=0),
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(user_id,book_id)
);
CREATE TABLE IF NOT EXISTS reading_bookmarks (
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 book_id INTEGER NOT NULL REFERENCES book_media(book_id) ON DELETE CASCADE,
 page INTEGER NOT NULL CHECK(page>=1),
 PRIMARY KEY(user_id,book_id,page)
);
CREATE TABLE IF NOT EXISTS member_books (
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
 list_type TEXT NOT NULL CHECK(list_type IN ('favorite','reading')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(user_id,book_id,list_type)
);
CREATE TABLE IF NOT EXISTS member_cards (
 member_id INTEGER PRIMARY KEY REFERENCES members(id) ON DELETE CASCADE,
 token TEXT NOT NULL UNIQUE CHECK(length(token)=48)
);
INSERT OR IGNORE INTO member_cards(member_id,token) SELECT id,lower(hex(randomblob(24))) FROM members;
CREATE TRIGGER IF NOT EXISTS create_member_card AFTER INSERT ON members BEGIN
 INSERT INTO member_cards(member_id,token) VALUES(NEW.id,lower(hex(randomblob(24))));
END;
CREATE TABLE IF NOT EXISTS loans (
 id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
 member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
 borrowed_on TEXT NOT NULL CHECK(date(borrowed_on) IS NOT NULL AND borrowed_on=date(borrowed_on)),
 due_on TEXT NOT NULL CHECK(date(due_on) IS NOT NULL AND due_on=date(due_on) AND due_on>=borrowed_on),
 returned_on TEXT CHECK(returned_on IS NULL OR (date(returned_on) IS NOT NULL AND returned_on=date(returned_on) AND returned_on>=borrowed_on)),
 penalty_cents INTEGER NOT NULL DEFAULT 0 CHECK(typeof(penalty_cents)='integer' AND penalty_cents>=0)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_loan ON loans(book_id,member_id) WHERE returned_on IS NULL;
CREATE INDEX IF NOT EXISTS loans_book_active ON loans(book_id) WHERE returned_on IS NULL;
CREATE TABLE IF NOT EXISTS reservations (
 id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
 member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','notified','cancelled','fulfilled')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_reservation ON reservations(book_id,member_id) WHERE status IN ('active','notified');
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY, member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
 reservation_id INTEGER REFERENCES reservations(id) ON DELETE RESTRICT,
 message TEXT NOT NULL CHECK(length(trim(message))>0), is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0,1)),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS activity_logs (
 id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
 action TEXT NOT NULL CHECK(length(trim(action))>0), details TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS circulation_settings (
 key TEXT PRIMARY KEY,
 value INTEGER NOT NULL CHECK(value>0)
);
CREATE TABLE IF NOT EXISTS loan_policies (
 member_type TEXT PRIMARY KEY CHECK(member_type IN ('student','teacher','standard')),
 daily_cents INTEGER NOT NULL CHECK(daily_cents>=0),
 max_cents INTEGER NOT NULL CHECK(max_cents>=0),
 loan_days INTEGER NOT NULL CHECK(loan_days>0),
 max_books INTEGER NOT NULL CHECK(max_books>0),
 renewals INTEGER NOT NULL CHECK(renewals>=0),
 grace_days INTEGER NOT NULL CHECK(grace_days>=0)
);
CREATE TABLE IF NOT EXISTS loan_renewals (
 id INTEGER PRIMARY KEY,
 loan_id INTEGER NOT NULL REFERENCES loans(id) ON DELETE RESTRICT,
 old_due_on TEXT NOT NULL,
 new_due_on TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reservation_holds (
 reservation_id INTEGER PRIMARY KEY REFERENCES reservations(id) ON DELETE CASCADE,
 expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notification_events (
 notification_id INTEGER PRIMARY KEY REFERENCES notifications(id) ON DELETE CASCADE,
 kind TEXT NOT NULL,
 event_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS notification_preferences (
 member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
 kind TEXT NOT NULL,
 PRIMARY KEY(member_id,kind)
);
CREATE TABLE IF NOT EXISTS login_attempts (
 id INTEGER PRIMARY KEY,
 account_bucket TEXT NOT NULL,
 address_bucket TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS login_attempt_account ON login_attempts(account_bucket,created_at);
CREATE INDEX IF NOT EXISTS login_attempt_address ON login_attempts(address_bucket,created_at);
CREATE TABLE IF NOT EXISTS password_resets (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 token_hash TEXT NOT NULL UNIQUE,
 expires_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_reservation_notification ON notifications(reservation_id) WHERE reservation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS reservation_queue ON reservations(book_id,created_at,id) WHERE status IN ('active','notified');
CREATE INDEX IF NOT EXISTS unread_member_notifications ON notifications(member_id) WHERE is_read=0;
CREATE VIEW IF NOT EXISTS book_inventory AS
 SELECT b.*, b.total_copies-(SELECT COUNT(*) FROM loans l WHERE l.book_id=b.id AND l.returned_on IS NULL) AS available_copies FROM books b;
CREATE TRIGGER IF NOT EXISTS validate_new_loan BEFORE INSERT ON loans BEGIN
 SELECT CASE WHEN NEW.returned_on IS NULL AND (SELECT available_copies FROM book_inventory WHERE id=NEW.book_id)<=0 THEN RAISE(ABORT,'Kitap mevcut değil') END;
 SELECT CASE WHEN (SELECT is_active FROM members WHERE id=NEW.member_id)=0 THEN RAISE(ABORT,'Üye aktif değil') END;
END;
CREATE TRIGGER IF NOT EXISTS protect_loan_update BEFORE UPDATE ON loans BEGIN
 SELECT CASE WHEN NEW.book_id!=OLD.book_id OR NEW.member_id!=OLD.member_id OR NEW.borrowed_on!=OLD.borrowed_on THEN RAISE(ABORT,'Ödünç kimliği değiştirilemez') END;
 SELECT CASE WHEN OLD.returned_on IS NOT NULL THEN RAISE(ABORT,'İade edilmiş kayıt değiştirilemez') END;
END;
CREATE TRIGGER IF NOT EXISTS protect_loan_delete BEFORE DELETE ON loans BEGIN
 SELECT RAISE(ABORT,'Ödünç geçmişi silinemez');
END;
CREATE TRIGGER IF NOT EXISTS protect_stock BEFORE UPDATE OF total_copies ON books BEGIN
 SELECT CASE WHEN NEW.total_copies<(SELECT COUNT(*) FROM loans WHERE book_id=OLD.id AND returned_on IS NULL) THEN RAISE(ABORT,'Stok aktif ödünç sayısından az olamaz') END;
END;
CREATE TRIGGER IF NOT EXISTS validate_reservation BEFORE INSERT ON reservations WHEN NEW.status IN ('active','notified') BEGIN
 SELECT CASE WHEN (SELECT available_copies FROM book_inventory WHERE id=NEW.book_id)>0 THEN RAISE(ABORT,'Mevcut kitap rezerve edilemez') END;
 SELECT CASE WHEN (SELECT is_active FROM members WHERE id=NEW.member_id)=0 THEN RAISE(ABORT,'Üye aktif değil') END;
END;
CREATE TRIGGER IF NOT EXISTS protect_reservation_update BEFORE UPDATE ON reservations BEGIN
 SELECT CASE WHEN NEW.book_id!=OLD.book_id OR NEW.member_id!=OLD.member_id THEN RAISE(ABORT,'Rezervasyon kimliği değiştirilemez') END;
 SELECT CASE WHEN NEW.status!=OLD.status AND NOT ((OLD.status='active' AND NEW.status IN ('notified','cancelled','fulfilled')) OR (OLD.status='notified' AND NEW.status IN ('cancelled','fulfilled'))) THEN RAISE(ABORT,'Geçersiz rezervasyon geçişi') END;
END;
COMMIT;
