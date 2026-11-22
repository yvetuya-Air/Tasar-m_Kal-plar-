"""Yönetici kategori bakımı."""
import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from database import get_db
from security import role_required
from services.book_service import categories
from services.validation import record_id

bp = Blueprint('categories', __name__)


@bp.route('/kategoriler', methods=['GET', 'POST'])
@role_required('admin')
def index():
    if request.method == 'GET':
        return render_template('categories.html', categories=categories())
    db = get_db()
    name = request.form.get('name', '').strip()
    operation = request.form.get('operation')
    try:
        if operation not in ('add', 'rename', 'delete'):
            raise ValueError('Geçerli bir işlem seçin.')
        if operation != 'delete' and not 1 <= len(name) <= 100:
            raise ValueError('Kategori adı 1–100 karakter olmalıdır.')
        with db:
            if operation == 'add':
                db.execute('INSERT INTO categories(name) VALUES(?)', (name,))
            else:
                category_id = record_id(request.form.get('category_id', ''), 'Kategori')
                if operation == 'delete':
                    result = db.execute('DELETE FROM categories WHERE id=?', (category_id,))
                else:
                    result = db.execute('UPDATE categories SET name=? WHERE id=?', (name, category_id))
                if result.rowcount != 1:
                    raise ValueError('Kategori bulunamadı.')
            db.execute("INSERT INTO activity_logs(user_id,action,details) VALUES(?,'category_changed',?)",
                       (g.user.id, name or 'Kategori silindi'))
    except (ValueError, sqlite3.IntegrityError) as error:
        message = 'Bu kategori kullanılıyor veya aynı ad zaten kayıtlı.' if isinstance(error, sqlite3.IntegrityError) else str(error)
        return render_template('categories.html', categories=categories(), error=message), 422
    flash('Kategori kaydedildi.', 'success')
    return redirect(url_for('categories.index'))
