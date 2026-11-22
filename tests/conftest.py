"""Test verilerini kullanıcı profilinden bağımsız, proje içinde tutar."""
from pathlib import Path
from uuid import uuid4
import pytest
import requests


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch):
    """Pytest sırasında dış HTTP yalnız açıkça taklit edilmiş istemcilerden gelir."""
    def blocked(*args,**kwargs):
        raise AssertionError('Otomatik testte gerçek HTTP isteği engellendi.')
    monkeypatch.setattr(requests.sessions.Session,'request',blocked)


def pytest_configure(config):
    # Açıkça verilen --basetemp seçeneğine öncelik verilir.
    # Her çalıştırmaya yeni yol: eşzamanlı testler ve eski dosya izinleri ayrılır.
    if config.option.basetemp is None:
        root = Path(__file__).resolve().parents[1] / '.test-tmp'
        root.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(root / f'run-{uuid4().hex}')
