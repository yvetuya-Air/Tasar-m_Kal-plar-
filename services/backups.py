"""SQLite yedekleme ve denetimli çevrimdışı geri yükleme."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def open_readonly(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    connection.execute('PRAGMA trusted_schema=OFF')
    return connection


def verify(connection):
    if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('SQLite bütünlük denetimi başarısız.')
    if connection.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('Veritabanında geçersiz yabancı anahtar var.')


def schema_tables(connection):
    return {name: tuple(row[1] for row in connection.execute('SELECT * FROM pragma_table_info(?)', (name,)))
            for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def write_backup(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file() or destination.exists():
        raise ValueError('Kaynak dosya bulunamadı veya yedek hedefi zaten mevcut.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.touch(exist_ok=False)
    try:
        with closing(open_readonly(source)) as current, closing(sqlite3.connect(destination)) as copy:
            current.backup(copy)
            verify(copy)
    except (ValueError, OSError, sqlite3.Error):
        destination.unlink(missing_ok=True)
        raise
    return destination


def restore_backup(target, source):
    target, source = Path(target).resolve(), Path(source).resolve()
    if target == source or not target.is_file() or not source.is_file():
        raise ValueError('Geri yükleme için iki ayrı ve mevcut SQLite dosyası gerekir.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    with closing(open_readonly(source)) as checked, closing(open_readonly(target)) as current:
        verify(checked)
        if schema_tables(checked) != schema_tables(current):
            raise ValueError('Yedek şeması mevcut uygulama sürümüyle eşleşmiyor.')
        previous = write_backup(target, target.with_name(f'{target.stem}.before-restore-{stamp}.sqlite3'))
        with closing(sqlite3.connect(target, timeout=15)) as restored:
            checked.backup(restored)
            verify(restored)
            with restored:
                restored.execute('UPDATE users SET session_version=abs(random() % 900000000000000000)+1')
                restored.execute('DELETE FROM password_resets')
                restored.execute('DELETE FROM login_attempts')
    return previous
