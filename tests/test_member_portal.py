"""Üye rafı, özel profil ve katalog filtreleri."""
from database import get_db
from services import loan_service
from test_adapter import app, csrf, login


def test_lists_are_private_and_profile_updates_own_record(app):
    member = login(app, 'member')
    admin = login(app)
    token = csrf(member, '/kitaplar')
    assert member.post('/kitaplarim/1/liste', data={'csrf_token': token, 'kind': 'favorite', 'operation': 'add'}).status_code == 302
    with app.app_context():
        title = get_db().execute('SELECT title FROM books WHERE id=1').fetchone()[0]
    assert title.encode() in member.get('/favorilerim').data
    assert admin.get('/favorilerim').status_code == 403
    with app.app_context():
        member_id = get_db().execute('SELECT id FROM members WHERE user_id IS NOT NULL').fetchone()[0]
        loan_service.borrow_book(2, member_id, loan_service.today().isoformat(), 1)
    assert b'Demo E-Kitap' in member.get('/kitaplarim').data
    assert member.post('/profilim', data={'csrf_token': token, 'full_name': 'Güncel Üye',
                                         'email': 'guncel@example.test', 'user_id': 1}).status_code == 302
    with app.app_context():
        assert get_db().execute('SELECT email FROM members WHERE user_id IS NOT NULL').fetchone()[0] == 'guncel@example.test'


def test_catalog_filters_grid_and_categories(app):
    admin = login(app)
    token = csrf(admin, '/kategoriler')
    assert admin.post('/kategoriler', data={'csrf_token': token, 'name': 'Yeni kategori', 'operation': 'add'}).status_code == 302
    response = admin.get('/kitaplar?book_type=physical&view=grid&sort=title')
    assert response.status_code == 200 and b'import-card' in response.data
    assert 'Yeni kategori'.encode() in response.data
