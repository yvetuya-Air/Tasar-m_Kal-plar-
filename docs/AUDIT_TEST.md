# Test ve Hata Düzeltme — Aşama 10

## Gerçek sonuçlar — 18 Kasım 2026

- Tam Python paketi: **374 başarılı, 0 başarısız, 0 hata, 0 atlandı**; 224,35 saniye.
- Hedefli yeni güvenlik + kimlik doğrulama paketi: **65 başarılı**; 68,26 saniye.
- Son favicon değişiminden sonra başlangıç kontrolleri: **3 başarılı**; 0,77 saniye.
- İzole Chrome kontrolü: **100 doğrulama başarılı**. Beklenmeyen HTTP/JS/CSP hatası yok.
- `pip check`, JavaScript sözdizimi ve SQLite bütünlük kontrolleri başarılı.
- Ana sunucu yeniden başlatmasında sekiz tablonun satır/özetleri korunmuştur.

Vaka numarası, ad, amaç, adımlar, beklenen/gerçek sonuç ve durum:
[TEST.md](TEST.md). Kaynak kanıtlar: [JUnit XML](audit/pytest-stage10.xml),
[vaka JSON](audit/stage10-results.json), [tarayıcı sonucu](screenshots/ui-test-result.json),
[bağımlılık sürümleri](audit/dependencies-stage10.json).

## Bulunan hatalar ve düzeltmeler

| Numara | Bulgu | Düzeltme | Doğrulama |
| --- | --- | --- | --- |
| B10-01 | Bozuk/bilinmeyen parola hash'i doğrulamada ValueError verebiliyordu | Genel 401 ile güvenli ret; ham hash/hata gösterilmez | Dört bozuk hash biçimi ve geçerli/geçersiz parola testleri |
| B10-02 | Çıkıştan önce kopyalanmış imzalı çerez süre sonuna kadar kullanılabiliyordu | users.session_version sunucu tarafında kontrol edilir; çıkış sürümü artırır | Kopya çerezin çıkış sonrası reddi, yeniden giriş |
| B10-03 | Pasiflik sonrası tekrar açılan hesapta eski çerez yeniden kullanılabilirdi | Pasifleştirme aynı işlemde oturum sürümünü artırır | Eski çerez reddi; yeni giriş başarısı |
| B10-04 | URL'de NUL/kontrol karakteri veya boş kullanıcı bilgisi kabul edilebiliyordu | Ortak models/urls.py doğrulaması; geçersiz adres reddi | EBook, kapak ve yanlış türde ürün girdisi testleri |
| B10-05 | Favicon eksikliği 404 konsol hatası üretiyordu | Yerel SVG favicon ve açık link eklendi | Aynı sıkı tarayıcı betiği yeniden geçti |
| B10-06 | Tarayıcı betiği bütün 4xx konsol hatalarını dışlıyordu; eski başarılı JSON başarısız çalışmadan sonra kalabilirdi | Yalnız kasıtlı /giris 401 ve /uyeler 403 ayrı kaydedilir; diğer hatalar başarısızdır. running/failed/passed durumu her çalışmada yazılır | İlk 404 hatası yakalandı, kaydedildi ve düzeltme sonrası yeniden denendi |

İlk tarayıcı başarısızlığı silinmemiştir:
[ui-stage10-initial-failure.json](audit/ui-stage10-initial-failure.json).
Beklenen 401 ve 403, başarısız ürün testleri değildir; yanlış parola ve yetkisiz
erişim testlerinin istenen sonucudur. Diğer HTTP hataları gizlenmez.
Hiçbir mevcut test kaldırılmamış veya xfail/skip ile etkisizleştirilmemiştir.

## Test kapsamı ve yalıtım

Önceki Factory Method, Adapter, Strategy, Observer, modeller, hizmetler,
kimlik doğrulama, kitap/üye yönetimi, ödünç/iade, rezervasyon/bildirim, gerçek
dashboard ve yeni süreçte kalıcılık testleri korunmuştur.

Yeni `test_security.py`: tuzlu hash, bozuk hash, imzalı çerez tekrar kullanımı,
oturum iptali, rol/veri erişimi, SQL saldırı girdisi, kaydedilmiş/yansıtılmış XSS,
CSRF başlık/oturum bağı, URL karakterleri ve eski veritabanı geçişini sınar.
Katalog ve işlem günlüğündeki XSS ayrıca gerçek Chromium içinde çalıştırılmıştır;
zararlı HTML metin olarak kalmış, DOM işareti veya resim olayı oluşmamıştır.

Pytest verileri `tmp_path` ile `.test-tmp` altında bağımsız SQLite dosyalarındadır.
Ortak fixture taklit edilmeyen `requests` HTTP çağrısını engeller; yalnız dış sınır
taklit edilir. Gerçek Factory/Strategy/Observer ve SQL işlemleri çalışır.
Node tarayıcı betiği yalnız 127.0.0.1:5001'i kabul eder; ayrı test veritabanına yazar.
Ana veritabanına test üyesi/kitabı/ödüncü eklenmemiştir.

## Oturum sürümü geçişi

`users.session_version INTEGER NOT NULL DEFAULT 0` eklendi. `init-db`, eski
veritabanında sütun yoksa yalnız `ALTER TABLE ... ADD COLUMN` uygular; var olan
hesap/kitap/geçmiş verisini silmez. Yedek `instance/library.pre-stage10-<zaman>.sqlite3`
dosyasına SQLite backup API ile alınmıştır. Eski sütunların bütün satırları ve
hashler geçiş öncesi/sonrası eşit doğrulanmıştır.

Mevcut kurulumda komutlar:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app init-db
.\.venv\Scripts\python.exe -m flask --app app:create_app check-db
.\.venv\Scripts\python.exe -m flask --app app:create_app run
```

Eski sürümsüz çerezler reddedilir; kullanıcı tekrar giriş yapmalıdır.
Çıkış aynı kullanıcıya ait bütün tarayıcı oturumlarını iptal eder. Farklı
kullanıcıların oturumları etkilenmez. Oturum süresi yine 30 dakika, rol/aktiflik
denetimi her istekte SQL üzerinden yapılır. Yeni tablo veya dış oturum hizmeti yoktur.

## Otomasyon / görsel inceleme / henüz yapılmayanlar

| Test numarası | Test adı | Test amacı | Test adımları | Beklenen sonuç | Gerçek sonuç | Test durumu |
| --- | --- | --- | --- | --- | --- | --- |
| V01 | Görsel inceleme, ajan | Metin ve düzenin gözle okunması | Son giriş hata görüntüsü ve 390 px mobil dashboard PNG'lerini açıp incele. | Hata okunur, alanlar kesilmez, mobil bölümler taşmaz. | İki PNG bu aşamada görüntülenip incelendi. Bu fiziksel cihaz testi değildir. | Gerçekleştirildi |
| G01 | Gerçek Google Books çağrısı | Dış servis erişimini doğrulama | Pytest dışında gerçek Nutuk araması gönder. | Kullanılabilir canlı kitap sonucu. | Anahtar yok; quota yanıtı. İç aktarım yolu taklit yanıtlarla başarılı. | Harici kota nedeniyle engellendi |
| M01 | Fiziksel telefon | Gerçek dokunma/klavye davranışı | Android/iOS cihazda akışı elle çalıştır. | İşlevler ve giriş rahat. | Bu aşamada fiziksel cihaz kullanılmadı. | Yürütülmedi |
| M02 | Ekran okuyucu | Yardımcı teknolojiyle gerçek kullanım | NVDA/VoiceOver ile menü/formları gez. | Etiketler ve odak anlaşılır. | Etiket ve klavye otomasyonu insan testinin yerine sunulmaz. | Yürütülmedi |
| M03 | Firefox/Safari | Diğer tarayıcı motorları | Aynı akışı bu motorlarda çalıştır. | Aynı iş sonuçları. | Yerel Chromium 157.0.8103.78 kullanıldı. | Yürütülmedi |

Canlı Google kanıtı: [google-books-stage10.json](audit/google-books-stage10.json).
`pip check` bağımlılık uyumluluğunu sınar; çevrimiçi CVE taraması yapıldığı iddia edilmez.
Hız sınırlama, MFA ve herkese açık yayın sertifikasyonu bu yerel ders aşamasında yoktur.

## Raporu yeniden üretme

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=docs/audit/pytest-stage10.xml
# ARAYUZ.md talimatıyla yeni .test-tmp veritabanında test sunucusunu açın.
node scripts/check_ui.cjs
.\.venv\Scripts\python.exe scripts/build_test_report.py --junit docs/audit/pytest-stage10.xml
```

Rapor betiği gerçek XML'deki her parametre varyantını numaralandırır. Hata/atlama
kayıtlarını silmez. Güncel başarılı tarayıcı sonucu yoksa eski sonucu başarı saymaz.
Önceki aşama kayıtlarını TEST.md içinde korur. Bu belge onuncu aşamanın denetim
kaydını korur; on birinci aşamanın güncel belgeleri [DOKUMANTASYON.md](DOKUMANTASYON.md) içindedir.
