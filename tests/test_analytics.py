"""Analitik göstergelerin SQLite verileriyle doğrulanması."""
from test_adapter import app, login


def test_analytics_uses_real_inventory_and_validates_period(app):
    client = login(app)
    page = client.get('/analitik?start=2026-01-01&end=2026-12-31')
    assert page.status_code == 200
    assert b'Toplam Kitap</div><strong class="stat-value">2</strong>' in page.data
    assert b'<meter' in page.data
    assert client.get('/analitik?start=2026-12-31&end=2026-01-01').status_code == 422
    assert login(app, 'member').get('/analitik').status_code == 403
