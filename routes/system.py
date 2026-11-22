"""Yönetim günlüğü ve yetkili veritabanı yedeği."""
from pathlib import Path
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile, TemporaryDirectory

from flask import Blueprint, current_app, render_template, request, send_file

from database import get_db
from security import role_required
from services.backups import write_backup
from services.validation import requested_page

bp = Blueprint('system', __name__)
ACTIONS = {
    'login': 'Giriş', 'login_failed': 'Başarısız giriş', 'logout': 'Çıkış',
    'book_created': 'Kitap eklendi', 'book_updated': 'Kitap güncellendi', 'book_deleted': 'Kitap silindi',
    'member_saved': 'Üye kaydedildi', 'member_status': 'Üye durumu güncellendi', 'profile_updated': 'Profil güncellendi',
    'loan_created': 'Ödünç verildi', 'loan_returned': 'İade alındı', 'loan_renewed': 'Ödünç yenilendi',
    'reservation_created': 'Rezervasyon oluşturuldu', 'reservation_cancelled': 'Rezervasyon iptal edildi',
    'settings_changed': 'Ayarlar değişti', 'category_changed': 'Kategori güncellendi',
    'reset_issued': 'Parola sıfırlama oluşturuldu', 'password_reset': 'Parola sıfırlandı',
    'password_changed': 'Parola değiştirildi', 'demo_seed': 'Gösterim verisi',
}


@bp.get('/islem-gecmisi')
@role_required('admin')
def audit():
    db = get_db()
    pages = max(1, (db.execute('SELECT count(*) FROM activity_logs').fetchone()[0] + 49) // 50)
    page = min(requested_page(request.args.get('page', 1)), pages)
    items = db.execute(
        '''SELECT a.*,u.username FROM activity_logs a LEFT JOIN users u ON u.id=a.user_id
           ORDER BY a.id DESC LIMIT 50 OFFSET ?''', ((page - 1) * 50,),
    ).fetchall()
    return render_template('audit.html', items=items, actions=ACTIONS, page=page, pages=pages)


@bp.get('/ayarlar/yedek')
@role_required('admin')
def backup():
    source = Path(current_app.config['DATABASE']).resolve()
    stream = SpooledTemporaryFile(max_size=8*1024*1024, mode='w+b', dir=source.parent)
    try:
        with TemporaryDirectory(prefix='kys-backup-', dir=source.parent) as directory:
            path = write_backup(source, Path(directory) / 'kutuphane.sqlite3')
            with path.open('rb') as backup_file:
                copyfileobj(backup_file, stream)
        size = stream.tell()
        stream.seek(0)
        response = send_file(stream, mimetype='application/octet-stream', as_attachment=True,
                             download_name='kutuphane-yedek.sqlite3')
    except Exception:
        stream.close()
        raise
    response.content_length = size
    response.cache_control.no_store = True
    return response
