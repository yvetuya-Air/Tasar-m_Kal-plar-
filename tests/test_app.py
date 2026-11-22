"""İlk aşamanın uygulama oluşturma ve başlangıç sayfası kontrolleri."""

from app import create_app


def test_home_page():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only'})
    response = app.test_client().get('/')
    assert response.status_code == 200
    assert 'Kütüphane'.encode() in response.data
    assert 'lang="tr"'.encode() in response.data


def test_test_config_is_applied():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only'})
    assert app.testing
    assert app.config['SECRET_KEY'] == 'test-only'


def test_unknown_page_returns_404():
    app = create_app({'TESTING': True})
    assert app.test_client().get('/olmayan-sayfa').status_code == 404
