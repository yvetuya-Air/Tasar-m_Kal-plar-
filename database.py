"""SQLite bağlantı yaşam döngüsü ve kurulum komutları."""
import sqlite3
import sys
from pathlib import Path
import click
from flask import current_app, g


def echo_tr(message):
    """Yönlendirilmiş Windows terminallerinde Türkçe UTF-8 çıktı."""
    stream = sys.stdout
    try:
        message.encode(stream.encoding or 'utf-8')
    except UnicodeEncodeError:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    click.echo(message, file=stream)


def get_db():
    if 'db' not in g:
        path = Path(current_app.config['DATABASE'])
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.create_function('tr_fold', 1, turkish_fold, deterministic=True)
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def turkish_fold(value):
    return (value or '').translate(str.maketrans({'I': 'ı', 'İ': 'i'})).casefold()


def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db=get_db()
    schema = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
    db.executescript(schema)
    # Aşama 10: mevcut hesapları silmeden oturum iptal sürümünü ekle.
    with db:
        db.execute('BEGIN IMMEDIATE')
        columns={row['name'] for row in db.execute('PRAGMA table_info(users)')}
        if 'session_version' not in columns:
            db.execute("ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0 CHECK(typeof(session_version)='integer' AND session_version>=0)")
        book_columns = {row['name'] for row in db.execute('PRAGMA table_info(books)')}
        for name, sql_type in (('cover_url', 'TEXT'), ('description', 'TEXT'),
                               ('publisher', 'TEXT'), ('publication_year', 'INTEGER'),
                               ('language', 'TEXT')):
            if name not in book_columns:
                db.execute(f'ALTER TABLE books ADD COLUMN {name} {sql_type}')
    migrate_book_types(db, schema)


def migrate_book_types(db, schema):
    if any(row['name'] == 'managed_media' for row in db.execute('PRAGMA table_info(books)')):
        return
    db.execute('PRAGMA foreign_keys = OFF')
    db.execute('PRAGMA legacy_alter_table = ON')
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            columns = [row['name'] for row in db.execute('PRAGMA table_info(books)')]
            if 'managed_media' in columns:
                return
            triggers = db.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name='books'").fetchall()
            db.execute('ALTER TABLE books RENAME TO books_stage13')
            create_books = schema.split('CREATE TABLE IF NOT EXISTS books (', 1)[1].split('\n);', 1)[0]
            db.execute(f'CREATE TABLE books ({create_books}\n)')
            fields = ', '.join(f'"{name}"' for name in columns)
            db.execute(f'INSERT INTO books ({fields}) SELECT {fields} FROM books_stage13')
            db.execute('DROP TABLE books_stage13')
            for trigger in triggers:
                db.execute(trigger['sql'])
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise sqlite3.IntegrityError('Kitap türü geçişi ilişkileri koruyamadı.')
    finally:
        db.execute('PRAGMA legacy_alter_table = OFF')
        db.execute('PRAGMA foreign_keys = ON')


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command('refresh-circulation')
    def refresh_command():
        from services.maintenance import refresh_circulation
        expired, reminders = refresh_circulation()
        echo_tr(f'{expired} ayırma süresi doldu; {reminders} yeni hatırlatma oluşturuldu.')

    @app.cli.command('issue-password-reset')
    @click.argument('username')
    def issue_reset_command(username):
        from services.account_security import issue_reset
        try:
            token = issue_reset(username)
        except LookupError as error:
            raise click.ClickException(str(error)) from error
        echo_tr(token)

    @app.cli.command('backup-db')
    @click.argument('destination', type=click.Path(path_type=Path, dir_okay=False))
    def backup_command(destination):
        from services.backups import write_backup
        try:
            result = write_backup(app.config['DATABASE'], destination)
        except (ValueError, OSError, sqlite3.Error) as error:
            raise click.ClickException(str(error)) from error
        echo_tr(f'Yedek hazır: {result}')

    @app.cli.command('restore-db')
    @click.argument('source', type=click.Path(path_type=Path, exists=True, dir_okay=False))
    def restore_command(source):
        from services.backups import restore_backup
        click.confirm('Sunucunun durdurulduğunu ve veritabanını geri yüklemeyi onaylıyor musunuz?', abort=True)
        try:
            previous = restore_backup(app.config['DATABASE'], source)
        except (ValueError, OSError, sqlite3.Error) as error:
            raise click.ClickException(str(error)) from error
        echo_tr(f'Geri yükleme tamamlandı. Önceki yedek: {previous}')

    @app.cli.command('demo-accounts')
    def demo_accounts_command():
        from services.demo_accounts import prepare_demo_accounts
        try:
            created = prepare_demo_accounts(get_db())
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        echo_tr('Yerel gösterim hesapları hazırlandı.' if created else 'Gösterim hesapları zaten mevcut; parolalar değiştirilmedi.')

    @app.cli.command('init-db')
    def init_command():
        init_db()
        echo_tr('Veritabanı hazırlandı; mevcut kayıtlar korundu.')

    @app.cli.command('demo-reading')
    def demo_reading_command():
        from services.demo_accounts import prepare_demo_reading
        try:
            loan = prepare_demo_reading(get_db())
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        echo_tr(f'Gösterim PDF ödüncü hazır: #{loan}')

    @app.cli.command('seed-demo')
    def seed_command():
        from seed import seed_demo
        init_db()
        try:
            created = seed_demo(get_db())
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        echo_tr('Gösterim verileri eklendi.' if created else 'Gösterim verileri zaten mevcut.')

    @app.cli.command('check-db')
    def check_command():
        db = get_db()
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise click.ClickException('Bütünlük kontrolü başarısız.')
        echo_tr('Veritabanı bütünlüğü ve yabancı anahtarlar geçerli.')
