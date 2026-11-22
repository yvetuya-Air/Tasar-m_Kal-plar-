"""Kitap kataloğu ve yöneticiye özel kitap formları."""
from dataclasses import asdict
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from security import login_required, role_required
from services import book_service
from services.digital_service import validate_upload
from services.validation import requested_page

bp = Blueprint('books', __name__, url_prefix='/kitaplar')


@bp.get('')
@login_required
def index():
    query = request.args.get('q', '').strip()
    if len(query) > 200:
        abort(400)
    page = requested_page(request.args.get('page',1))
    filters = {key: request.args.get(key, '').strip() for key in
               ('title', 'author', 'isbn', 'language', 'category_id', 'publication_year', 'book_type', 'stock', 'sort', 'view')}
    if any(len(value) > 200 for value in filters.values()):
        abort(400)
    books, count, page, pages = book_service.search_books(query, page, filters)
    pagination = {'q': query, **{key: value for key, value in filters.items() if value}}
    return render_template('books.html', books=books, count=count, query=query, page=page,
                           pages=pages, filters=filters, categories=book_service.categories(), pagination=pagination)


def book_form(book_id=None):
    book = book_service.get_book(book_id) if book_id is not None else None
    if book_id is not None and book is None:
        abort(404)
    data = request.form if request.method == 'POST' else asdict(book) if book else {'book_type':'physical','total_copies':1}
    error = None
    if request.method == 'POST':
        try:
            file = request.files.get('media')
            media = validate_upload(file, data.get('book_type'), data.get('rights') == 'yes') if file and file.filename else None
            book_service.save_book(request.form, g.user.id, book_id, media)
        except ValueError as problem:
            error = str(problem)
        except LookupError:
            abort(404)
        else:
            flash('Kitap güncellendi.' if book_id else 'Kitap eklendi.', 'success')
            return redirect(url_for('books.index'))
    return render_template('book_form.html', data=data, book=book, categories=book_service.categories(), error=error), 422 if error else 200


@bp.route('/ekle', methods=['GET','POST'])
@role_required('admin')
def add():
    return book_form()


@bp.route('/<int:book_id>/duzenle', methods=['GET','POST'])
@role_required('admin')
def edit(book_id):
    return book_form(book_id)


@bp.route('/<int:book_id>/sil', methods=['GET','POST'])
@role_required('admin')
def delete(book_id):
    book = book_service.get_book(book_id)
    if book is None:
        abort(404)
    error = None
    if request.method == 'POST':
        try:
            book_service.delete_book(book_id, g.user.id)
        except book_service.BookValidationError as problem:
            error = str(problem)
        except LookupError:
            abort(404)
        else:
            flash('Kitap silindi.', 'success')
            return redirect(url_for('books.index'))
    return render_template('book_delete.html', book=book, error=error), 409 if error else 200
