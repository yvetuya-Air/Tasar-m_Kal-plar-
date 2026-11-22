# Kütüphane Yönetim Sistemi

**EBLG443 — Tasarım Kalıpları | Proje Gelişimi 1**

Python ve Flask ile geliştirilen kütüphane yönetim uygulaması. Kitap ve üye kayıtları, ödünç verme, iade, rezervasyon ve bildirim işlemleri tek bir sistemde yönetilir. Projede dört GoF tasarım kalıbı kullanılmıştır.

## Kullanılan teknolojiler

Python, Flask, SQLite, HTML, CSS, JavaScript ve pytest.

## Tasarım kalıpları

| Kalıp | Kullanım amacı | Kod |
| --- | --- | --- |
| Factory Method | Fiziksel, elektronik ve sesli kitap oluşturma | [factory_method.py](patterns/factory_method.py) |
| Adapter | Google Books ve Open Library verilerini ortak biçime dönüştürme | [adapter.py](patterns/adapter.py), [open_library_adapter.py](patterns/open_library_adapter.py) |
| Strategy | Üye türüne göre gecikme cezası hesaplama | [strategy.py](patterns/strategy.py) |
| Observer | İade edilen kitap için bekleyen üyeye bildirim gönderme | [observer.py](patterns/observer.py) |

## Kurulum ve çalıştırma (Windows PowerShell)

Komutları `app.py` ve `requirements.txt` dosyalarının bulunduğu proje klasöründe çalıştırın.

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Son komutla oluşturulan değeri `.env` dosyasındaki `SECRET_KEY=` satırına yazın. `.env` dosyasını GitHub'a yüklemeyin.

**İlk kurulumda**, boş veritabanı ve gösterim hesapları için:

```powershell
python.exe -m flask --app app:create_app init-db
python.exe -m flask --app app:create_app seed-demo
python.exe -m flask --app app:create_app demo-accounts
python.exe -m flask --app app:create_app check-db
python.exe -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

Uygulamayı tarayıcıdan açın: **http://127.0.0.1:5000/giris**

Sonraki çalıştırmalarda sanal ortamı etkinleştirip yalnızca `run` komutunu kullanmak yeterlidir. Mevcut veritabanını yeniden oluşturmayın.

## Testler

```powershell
python -m pytest -q
```

## Belgeler

- [Kurulum kılavuzu](docs/KURULUM.md)
- [Testler](docs/TEST.md)
- [Tasarım kalıpları ve UML](docs/TASARIM_KALIPLARI.md)
- [Gösterim adımları](docs/DEMO.md)

## Ekran görüntüsü

![Yönetici paneli](docs/screenshots/proje-gelisimi-1/dashboard-acik.png)
