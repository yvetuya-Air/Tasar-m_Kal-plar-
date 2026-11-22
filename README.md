# Kütüphane Yönetim Sistemi

**EBLG443 — Tasarım Kalıpları · Proje Gelişimi 1 · 23 Kasım 2026 teslimi**

## Proje hakkında ve amacı

Kütüphane Yönetim Sistemi, kitap ve üye kayıtlarını, ödünç işlemlerini ve rezervasyonları tek bir arayüzden yönetir. Dersin amacı Factory Method, Adapter, Strategy ve Observer kalıplarını çalışan iş akışlarında göstermektir.

- [Kurulum kılavuzu](docs/KURULUM.md)
- [Test raporu ve tekrar çalıştırma komutları](docs/TEST.md)
- [Tasarım kalıpları, UML ve kaynak kod](docs/TASARIM_KALIPLARI.md)
- [Sunum senaryosu](docs/DEMO.md)
- [Son kontrol raporu](docs/TESLIM_KONTROL.md)

## Teknolojiler ve temel özellikler

Python 3.11+, Flask, Jinja2, SQLite, HTML/CSS/JavaScript ve pytest kullanılır. Harici katalog istemcileri HTTP isteklerini requests ile gönderir.

- Yönetici ve üye girişi, çıkış ve rol bazlı erişim.
- Fiziksel, elektronik ve sesli kitap kaydı. Üye ekleme, güncelleme ve hesap etkinliği yönetimi.
- Ödünç verme, iade, rezervasyon, üye türüne göre gecikme cezası ve uygulama içi bildirim.
- Kitap Keşfet üzerinden Google Books veya Open Library araması ve yönetici tarafından içe aktarma.
- Dört kalıp için UML, gerçek kod ve tekrar çalıştırılabilen gösterimler.

## Kullanılan tasarım kalıpları

| Kalıp | Uygulamadaki görevi | Kaynak |
| --- | --- | --- |
| Factory Method | Kitap türüne göre uygun ürün ve doğrulama akışını seçer. | [factory_method.py](patterns/factory_method.py) |
| Adapter | Dış katalog yanıtlarını BookImportData modeline dönüştürür. | [Google Books](patterns/adapter.py), [Open Library](patterns/open_library_adapter.py) |
| Strategy | Gecikme cezasını üye türüne göre hesaplar. Başlangıç tarifeleri öğrenci 2, öğretmen 1 ve normal üye 5 TL/gündür. | [strategy.py](patterns/strategy.py) |
| Observer | Kitap uygun hâle geldiğinde rezervasyon sahibine bildirim kaydeder. | [observer.py](patterns/observer.py) |

## Sistem mimarisi ve klasör yapısı

Tarayıcıdan gelen isteği Flask Blueprint karşılar. İş kuralları hizmet katmanında yürütülür. Hizmetler kalıpları kullanır ve SQLite kayıtlarını günceller. Jinja2 sonucu Türkçe arayüze dönüştürür. [Mimari ve veri modeli](docs/MIMARI.md).

| Konum | Sorumluluk |
| --- | --- |
| app.py, config.py | Uygulama fabrikası ve ortam yapılandırması |
| database.py, schema.sql, seed.py | SQLite şeması, CLI ve örnek veri |
| routes/, services/ | HTTP yönlendirmesi ve iş kuralları |
| models/, patterns/ | Veri nesneleri ve kalıp uygulamaları |
| templates/, static/ | Türkçe arayüz, stiller, JavaScript ve UML görselleri |
| tests/, scripts/, docs/ | Testler, doğrulama araçları ve teslim belgeleri |

## Kurulum ve çalıştırma

ZIP’i açın veya yayınlanan GitHub deposunu klonlayın. Python sanal ortamını kurup bağımlılıkları yükleyin, .env.example dosyasını .env olarak kopyalayın ve yerel SECRET_KEY oluşturun. Komutlar ve örnek hesaplar [kurulum kılavuzunda](docs/KURULUM.md).

Windows PowerShell’de proje kökünde, hazırladığınız sanal ortamla çalıştırın.

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app init-db
.\.venv\Scripts\python.exe -m flask --app app:create_app seed-demo
.\.venv\Scripts\python.exe -m flask --app app:create_app demo-accounts
.\.venv\Scripts\python.exe -m flask --app app:create_app check-db
.\.venv\Scripts\python.exe -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

Tarayıcıda <http://127.0.0.1:5000/giris> adresini açın.

## Testler

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Gerçek sonuçlar, tarayıcı kontrolleri ve harici katalog sınırları [test raporunda](docs/TEST.md) kayıtlıdır.

## Ekran görüntüleri

Görüntüler ayrı SQLite gösterim verisiyle çalışan uygulamadan alınmıştır.

![Yönetici genel bakış ekranı](docs/screenshots/proje-gelisimi-1/dashboard-acik.png)

[Giriş ekranı](docs/screenshots/proje-gelisimi-1/giris.png) · [Tasarım Kalıpları](docs/screenshots/proje-gelisimi-1/tasarim-kaliplari.png) · [Mobil panel](docs/screenshots/proje-gelisimi-1/dashboard-mobil.png) · [Tüm teslim görüntüleri](docs/screenshots/proje-gelisimi-1)

## Geliştirme durumu

Akademik teslim, V2.0 geliştirme dalındaki f81a939 sürümüne dayanır. Var olan özellikler korunur. Teslim değişiklikleri kalıp sayfası, UML ve doğrulama belgelerine odaklanır. [GitHub yayınlama adımları](docs/GITHUB_YAYINLAMA.md).
