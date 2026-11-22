# Proje Gelişimi 1 test raporu

**EBLG443 — Tasarım Kalıpları · 20 Kasım 2026 · Türkiye saati**

## 1. Testlerin amacı

Rol ve kayıt sahipliği sınırlarını, kitap ve üye işlemlerini, SQLite kalıcılığını ve dört kalıbın gerçek iş akışlarındaki davranışını doğrulamak.

## 2. Test ortamı

Windows, Python 3.13.2, SQLite 3.45.3 ve Git 2.52.0 kullanıldı. Chromium 157.0.8103.79 kontrolleri 1440, 768 ve 390 piksel genişliklerde yürütüldü. Pytest başına geçici SQLite veritabanları ve tarayıcı çalıştırması için ayrı demo veritabanı kullanıldı. [Python paket sürümleri](audit/dependencies-stage443.json).

## 3. Kullanılan test araçları

pytest ve Flask test istemcisi HTTP ve hizmet testlerini çalıştırdı. Playwright yerel Chromium ile gerçek form, yönlendirme ve arayüz akışlarını denetledi. SQLite bütünlük ve yabancı anahtar kontrolleri, Git kaynak listesi ve yerel Mermaid çizim denetimi teslim doğrulamasını tamamladı.

## 4. Birim testleri

Ürün oluşturma ve doğrulama, dış verinin dönüşümü, tarih ve ceza hesabı, abone ekleme ve çıkarma, bildirim yayını ve diğer model kuralları sınandı.

## 5. Entegrasyon testleri

Flask rotalarının rol izinleri, CSRF, formlar, SQLite geçiş ve yeniden başlatma sonrası veri kalıcılığı ayrıca sınandı. Tam akış bir fiziksel kitap ve bir içe aktarılmış elektronik kitap oluşturur. Ardından üyeler, ödünç, rezervasyon, 6 TL ceza, otomatik bildirim, kayıt sahipliği ve yeniden başlatma sonrası değerler denetlenir. Dış sağlayıcının HTTP cevabı taklit edilir. [Entegrasyon testi](../tests/test_integration.py).

## 6. Tasarım kalıpları testleri

- **Factory Method** — Somut üreticiler kendi ürünlerini döndürür. Ortak hazırlama metodu geçersiz alanları denetler. [test_factory.py](../tests/test_factory.py)
- **Adapter** — Google Books ve Open Library alanları BookImportData biçimine dönüştürülür. Taklit yanıtta zaman aşımı ve kota sonrası kaynak geçişi de sınanır. [test_adapter.py](../tests/test_adapter.py) · [test_catalog_v2.py](../tests/test_catalog_v2.py)
- **Strategy** — Aynı PenaltyCalculator nesnesi strateji değiştirdiğinde beş günlük ücret sırasıyla 10, 5 ve 25 TL olur. [test_strategy.py](../tests/test_strategy.py)
- **Observer** — Rezervasyonlu kitap dönünce doğru üye bilgilendirilir. Yayın tekrarlandığında eş kayıt oluşmaz, bildirim hatasında iade işlemi geri alınır. [test_observer.py](../tests/test_observer.py)

## 7–9. Fonksiyonel test senaryoları, beklenen ve gerçek sonuçlar

| Test No | Test Adı | Beklenen Sonuç | Gerçek Sonuç | Durum |
| --- | --- | --- | --- | --- |
| T01 | Giriş, çıkış ve rol izinleri | Yönetici ve üye giriş yapar. Üye yönetici alanında 403 alır. Çıkış oturumu kapatır. | Pytest giriş, çıkış ve rol testleri geçti. Chromium hatalı girişte 401 ve üye erişiminde 403 gördü. | Başarılı |
| T02 | Kitap yönetimi ve Factory Method | Türüne uygun doğrulanan ürün katalogda görünür. | Üretici testleri ve Chromium kitap formu geçti. Eğitim ekranında EBookCreator ve EBook görüldü. | Başarılı |
| T03 | Üye yönetimi | Üye kaydı oluşturulur, düzenlenir ve etkinlik durumu güncellenir. | Üye kaydı, güncelleme, pasifleştirme ve bağlı hesabın rolü doğrulandı. | Başarılı |
| T04 | Ödünç ve rezervasyon | Kopya ödünçteyken stok düşer ve ikinci üye bekleme sırasına alınır. | Tarayıcı ve entegrasyon akışları geçti. | Başarılı |
| T05 | İade ve Strategy | Gecikme üye tarifesiyle hesaplanır. Beş günde 10 / 5 / 25 TL çıkar. | Eğitim sayfasında üç tutar görüldü. Entegrasyon testinde üç günlük öğrenci gecikmesi 600 kuruş olarak SQLite’a yazıldı. | Başarılı |
| T06 | Observer ve bildirim | İade sonrası rezervasyon sahibine tek bildirim görünür. | Tarayıcıda üye bildirimi gördü ve okundu olarak işaretledi. Tekilleştirme ve geri alma testleri geçti. | Başarılı |
| T07 | Adapter, taklit dış veri | Dış JSON ortak şemaya dönüşür, yetkili kayıt SQLite’a yazılır. | İçe aktarma entegrasyonu ve çevrimdışı eğitim gösterimi geçti. | Başarılı |
| T08 | SQLite ve temiz kaynak kopyası | Hazırlama komutları çalışır, tekrarlar veriyi çoğaltmaz. | 12 adım geçti. SQLite bütünlük ve yabancı anahtar kontrolleri başarılı. | Başarılı |
| T09 | Chromium arayüz paketi | Temel ve mevcut ek akışlarda beklenmeyen tarayıcı hatası oluşmaz. | 137 kontrol geçti. JavaScript hatası gözlenmedi. Dört eğitim sonucu ayrıca tarayıcıda doğrulandı. | Başarılı |
| T10 | Canlı dış katalog | 9780306406157 ISBN aramasına sağlayıcı yanıt verir. | Google Books ve Open Library bağlantı hatası döndürdü. | Bağlantı kurulamadı |
| T11 | Yeni sanal ortama paket kurulumu | pip requirements.txt bağımlılıklarını yükler. | Sanal ortam oluşturuldu. Paket kaynağı Flask için kullanılabilir dağıtım döndürmedi. Kurulu ortamın pip check sonucu başarılı. | Tamamlanamadı |
| T12 | UML ve ER çizimi | Dört sınıf diyagramı ve mimari çizimler oluşturulur. | Chromium’da 7 Mermaid kaynağı çizildi. Uygulamadaki 4 SVG yüklendi. | Başarılı |
| T13 | İkinci işletim sistemi, uzak GitHub klonu ve fiziksel cihaz | Kurulum ve görüntüleme farklı ortamlarda tekrarlanabilir. | Bu teslimde bu ortamlarda test yapılmadı. | Çalıştırılmadı |

## 10. Başarılı ve başarısız testler

İlk tam koşuda **409 geçti, 1 başarısız**. Kalıp sayfası düzenlenirken mevcut ön yüz testinin denetlediği “Gerçek kalıp sınıfları” ifadesi kaldırılmıştı. İfade aynı açıklamada geri getirildi. Hedefli ön yüz koşusunda **35 test geçti**.

Düzeltilmiş teslim kodunda tam pytest koşusu **410 ge?ti, 0 ba?ar?s?z, 0 hata, 0 atland? (172,51 saniye)**. Hiçbir test silinmedi. [Son tam JUnit sonucu](audit/pytest-proje-gelisimi-1.xml) · [Tarayıcı kaydı](screenshots/proje-gelisimi-1/ui-test-result.json) · [Kurulum kaydı](audit/setup-stage443.json) · [Mermaid kaydı](audit/diagrams-stage443.json).

## 11. Genel değerlendirme

Temel iş akışları ayrı veritabanlarıyla doğrulandı. Dört kalıp uygulamanın iş kurallarında ve eğitim ekranında çalıştı. Canlı katalog ve yeni ortamda paket indirme ağ ve paket kaynağına bağlıdır. Harici katalog erişimi yoksa Adapter gösterimi iki sağlayıcının örnek JSON verisiyle çalışır.

### Tekrar çalıştırma

PowerShell’de proje kökünde, [kurulum](KURULUM.md) sonrasında:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q tests/test_factory.py tests/test_adapter.py tests/test_catalog_v2.py tests/test_strategy.py tests/test_observer.py tests/test_integration.py
.\.venv\Scripts\python.exe scripts/sync_doc_sources.py --check
.\.venv\Scripts\python.exe scripts/check_docs.py --stage 443
```

Tarayıcı paketi için Windows’ta Node.js ve kurulu Chrome veya Edge gerekir. İki ayrı terminal kullanın. Her çalıştırmada daha önce kullanılmamış bir test veritabanı adı seçin.

```powershell
# İlk terminal
.\.venv\Scripts\python.exe scripts/ui_preview.py --database .test-tmp/yeni-arayuz-testi.sqlite3 --port 5001
# İkinci terminal
npm.cmd install --prefix .ui-tools --no-save --package-lock=false playwright
$env:UI_TEST_STAGE = '443'
$env:UI_TEST_OUTPUT = '.test-tmp/yeni-arayuz-sonucu'
node scripts/check_ui.cjs
```
