"""Harici katalog keşfi ve yöneticiye özel içe aktarma."""
from flask import Blueprint, current_app, g, render_template, request
from patterns.adapter import GoogleBooksAdapter, GoogleBooksAPI, BookProviderError, search_fields
from patterns.open_library_adapter import OpenLibraryAdapter
from security import login_required, role_required
from services.book_service import categories
from services.catalog_cache import CatalogCache
from services.open_library_api import OpenLibraryAPI

bp = Blueprint('google_books', __name__)
SOURCES = {'google': 'Google Books', 'open_library': 'Open Library'}
MAX_PAGE = 100


@bp.record_once
def setup(state):
    state.app.extensions['catalog_cache'] = {source: CatalogCache() for source in SOURCES}


def provider(source='google'):
    if source == 'open_library':
        return OpenLibraryAdapter(OpenLibraryAPI())
    return GoogleBooksAdapter(GoogleBooksAPI(current_app.config['GOOGLE_BOOKS_API_KEY']))


def cached(source, key, fetch):
    return current_app.extensions['catalog_cache'][source].load(key, fetch)


def search_provider(source, values, page):
    return cached(source, ('search', page, *values.values()),
                  lambda: provider(source).search_page(**values, page=page))


def search_context(values, source='google', **kwargs):
    discovery = request.endpoint in ('google_books.discover', 'google_books.detail')
    return render_template('google_books.html', values=values, source=source,
                           sources=SOURCES, discovery=discovery, **kwargs)


@bp.route('/kitaplar/google', methods=['GET', 'POST'])
@role_required('admin')
def search():
    return catalog_search()


@bp.route('/kitap-kesfet', methods=['GET', 'POST'])
@login_required
def discover():
    return catalog_search()


def catalog_search():
    values = {key:request.form.get(key,'').strip() for key in ('title','author','isbn')}
    if request.method == 'GET':
        return search_context(values)
    source = request.form.get('source', 'google')
    try:
        page = int(request.form.get('page', '1'))
        if source not in SOURCES or not 1 <= page <= MAX_PAGE:
            raise ValueError
    except ValueError:
        return search_context(values, error='Geçerli bir kaynak ve sayfa seçin.'), 422
    try:
        values = dict(zip(values, search_fields(**values)))
    except ValueError as problem:
        return search_context(values, source, error=str(problem)), 422

    notice = None
    try:
        result = search_provider(source, values, page)
    except BookProviderError as problem:
        error = str(problem)
        status = 502 if problem.kind == 'invalid_response' else 503
        alternative_source = 'google' if source == 'open_library' else 'open_library'
        try:
            result = search_provider(alternative_source, values, 1)
        except BookProviderError as alternative:
            return search_context(values, source, error=f'{error} {alternative}'), status
        source, page = alternative_source, 1
        notice = f'{error} {SOURCES[source]} sonuçları gösteriliyor.'
    return search_context(values, source, result=result, page=page,
                          has_next=result.has_next and page < MAX_PAGE, notice=notice)


@bp.post('/kitap-kesfet/ayrinti')
@login_required
def detail():
    return catalog_book()


@bp.post('/kitaplar/google/aktar')
@role_required('admin')
def preview():
    return catalog_book(edit=True)


def catalog_book(edit=False):
    source = request.form.get('source', 'google')
    if source not in SOURCES:
        return search_context({}, error='Geçersiz kitap kaynağı.'), 422
    source_id = request.form.get('source_id', '')
    try:
        draft = cached(source, ('book', source_id), lambda: provider(source).get_book(source_id))
    except BookProviderError as problem:
        status = 422 if problem.kind == 'invalid_id' else 404 if problem.kind == 'not_found' else 502
        return search_context({}, source, error=str(problem)), status
    if not edit:
        return render_template('catalog_detail.html', book=draft, source=source,
                               source_label=SOURCES[source], can_import=g.user.role == 'admin')
    return render_template('book_form.html', data=draft.to_form(), book=None,
                           categories=categories(), error=None, import_draft=draft,
                           import_source=SOURCES[source])
