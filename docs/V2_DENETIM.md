# V2.0 Uygulama ve Denetim Raporu

## Kapsam

| Aşama | Uygulanan çalışma |
| --- | --- |
| 14 | PDF/MP3/WAV yükleme, erişim denetimi, PDF okuyucu ve ses oynatıcı, ilerleme ve ayraçlar |
| 15 | Üye rafı, özel profil, parola değişikliği, kategoriler ve katalog filtreleri |
| 16 | Opak QR, kişisel üye kartı, PDF/PNG, kamera ve numarayla üye tanıma |
| 17 | Sıralı süreli ayırma, yenileme, ceza politikaları, bildirim tercihleri ve zamanlanabilir bakım |
| 18 | Yönetici analitiği ve SQLite sorgularına bağlı dönem grafikleri |
| 19 | Sekiz rapor, dönem filtresi, yazdırma ve PDF/Excel/CSV çıktıları |
| 20 | Açık/koyu görünüm, rol odaklı ana sayfa, daraltılabilir gezinme, arama ve işlem geri bildirimi |
| 21 | Giriş sınırlaması, tek kullanımlık parola kodu, işlem geçmişi, doğrulanmış yedek ve çevrimdışı geri yükleme |
| 22 | Gerçek sınıflarla eğitim örnekleri ve yalıtılmış dolaşım senaryosu |
| 23 | Regresyon, tarayıcı, medya, dışa aktarma, izin ve geçiş denetimleri |

## Şema ve mimari

Kitap tablosu sesli kitap türünü ve uygulama içi dosya durumunu destekler. Geçiş kitap kimliklerini, ISBN’leri, bağlantıları ve eski satırları koruyarak tabloyu işlem içinde yeniden kurar.

- Dijital içerik ve okuma: `book_media`, `reading_progress`, `reading_bookmarks`.
- Kişisel raf ve kart: `member_books`, `member_cards`.
- Dolaşım ve bildirim: `circulation_settings`, `loan_policies`, `loan_renewals`, `reservation_holds`, `notification_events`, `notification_preferences`.
- Hesap güvenliği: `login_attempts`, `password_resets`.

Flask Blueprint’leri istekleri ve yetkileri yönetir. Hizmetler iş kurallarını ve SQLite işlemlerini taşır. Factory Method üçüncü ürün olan AudioBook’u kurar. Adapter iki harici kaynağı ortak modele dönüştürür. Strategy kayıtlı ceza politikasını uygular. Observer hem stok yayınını hem genel bildirim olaylarını iletir. [Mimari](MIMARI.md) · [Tasarım kalıpları](TASARIM_KALIPLARI.md)

## Çözülen sorunlar

PDF sayfa nesneleri, destekledikleri kapatma arayüzüyle serbest bırakıldı. Windows’ta yedek indirme sırasında kilitli geçici dosya bırakılması engellendi. Geri yükleme sonrası eski oturumlar ve sıfırlama kodları iptal edilir. Çalışan bir ayırma, stok düşürülürken hesaba katılır. Tarayıcı ve entegrasyon kontrolleri, yeni bildirim türleri ve ikili yanıtları ayırt edecek şekilde güncellendi.

## İşletim

Var olan kurulumda önce yedek alın, sonra `init-db` ve `check-db` çalıştırın. Yeni gösterim veritabanında ayrıca `seed-demo` ve `demo-accounts` çalıştırın. Windows PowerShell’den uygulamayı başlatın:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app:create_app run
```

| Yerel gösterim rolü | Kullanıcı adı | Parola |
| --- | --- | --- |
| Yönetici | demo_yonetici | DemoYonetici!2026 |
| Üye | demo_uye | DemoUye!2026 |

Dağıtım hakkı yükleme sırasında yönetici tarafından doğrulanır. Kamera için tarayıcı izni ve HTTPS veya yerel adres gerekir. Parola sıfırlama kodu işletici aracılığıyla verilir. Zamanlanmış dolaşım bakımı için `refresh-circulation` komutunu görev zamanlayıcıya ekleyin.

## Bilinen sınırlar

- Google Books canlı sorgusu Aşama 13 sırasında kota yanıtı verdi. Open Library’ye canlı geçiş doğrulandı.
- Kamera akışı ve QR çözümü Chromium’da oluşturulan video akışıyla sınandı. Fiziksel kamera, Firefox, Safari ve ekran okuyucuyla ayrı deneme yürütülmedi.
- PDF okuyucusunda görsel ve seçilebilir metin görünümleri bulunur. Arama, gömülü metni kullanır. Taranmış görüntülerde OCR yapılmaz.
- PDF, MP3 ve PCM WAV yüklemeleri 32 MB ile sınırlıdır. Tarayıcı ses desteği ayrıca kullanılan biçime bağlıdır.

[Kurulum ve geçiş](KURULUM.md) · [Kullanım kılavuzu](KULLANIM_KILAVUZU.md) · [Güvenlik](GUVENLIK.md) · [Test raporu](TEST.md)


## Olu?turulan dosyalar (58)

- `CHANGELOG.md`
- `docs/GUVENLIK.md`
- `docs/V2_DENETIM.md`
- `docs/audit/documentation-links-stage23.json`
- `docs/screenshots/stage23/analitik.png`
- `docs/screenshots/stage23/dashboard-acik.png`
- `docs/screenshots/stage23/dashboard-koyu.png`
- `docs/screenshots/stage23/dashboard-mobil.png`
- `docs/screenshots/stage23/giris-hatasi.png`
- `docs/screenshots/stage23/giris.png`
- `docs/screenshots/stage23/pdf-okuyucu.png`
- `docs/screenshots/stage23/raporlar.png`
- `docs/screenshots/stage23/sesli-kitap.png`
- `docs/screenshots/stage23/tasarim-kaliplari.png`
- `docs/screenshots/stage23/ui-test-result.json`
- `docs/screenshots/stage23/uye-karti.png`
- `routes/analytics.py`
- `routes/categories.py`
- `routes/digital.py`
- `routes/member_cards.py`
- `routes/member_portal.py`
- `routes/reports.py`
- `routes/system.py`
- `services/account_security.py`
- `services/analytics.py`
- `services/backups.py`
- `services/circulation_policy.py`
- `services/digital_service.py`
- `services/maintenance.py`
- `services/member_card.py`
- `services/member_portal.py`
- `services/reports.py`
- `static/js/digital.js`
- `static/js/print.js`
- `static/js/scan.js`
- `static/vendor/jsQR.LICENSE`
- `static/vendor/jsQR.js`
- `templates/analytics.html`
- `templates/audit.html`
- `templates/categories.html`
- `templates/circulation_settings.html`
- `templates/digital_library.html`
- `templates/digital_reader.html`
- `templates/member_card.html`
- `templates/member_profile.html`
- `templates/member_scan.html`
- `templates/member_shelf.html`
- `templates/password.html`
- `templates/password_reset.html`
- `templates/penalties.html`
- `templates/reports.html`
- `tests/test_analytics.py`
- `tests/test_circulation_v2.py`
- `tests/test_digital.py`
- `tests/test_member_cards.py`
- `tests/test_member_portal.py`
- `tests/test_reports.py`
- `tests/test_system_v2.py`

## G?ncellenen dosyalar (49)

- `README.md`
- `app.py`
- `database.py`
- `docs/KULLANIM_KILAVUZU.md`
- `docs/KURULUM.md`
- `docs/MIMARI.md`
- `docs/TASARIM_KALIPLARI.md`
- `docs/TEST.md`
- `docs/diagrams/factory_method.mmd`
- `models/book.py`
- `patterns/factory_method.py`
- `patterns/observer.py`
- `requirements.txt`
- `routes/auth.py`
- `routes/books.py`
- `routes/design_patterns.py`
- `routes/loans.py`
- `routes/notifications.py`
- `routes/settings.py`
- `schema.sql`
- `scripts/check_ui.cjs`
- `scripts/generate_uml.py`
- `services/book_service.py`
- `services/dashboard_service.py`
- `services/loan_service.py`
- `services/member_service.py`
- `services/notification_service.py`
- `services/reservation_service.py`
- `static/css/style.css`
- `static/images/uml-factory.svg`
- `static/js/books.js`
- `static/js/theme.js`
- `static/js/ui.js`
- `templates/base.html`
- `templates/book_form.html`
- `templates/books.html`
- `templates/design_patterns.html`
- `templates/error.html`
- `templates/loans.html`
- `templates/login.html`
- `templates/notifications.html`
- `templates/overview.html`
- `templates/reservations.html`
- `templates/settings.html`
- `tests/test_database.py`
- `tests/test_frontend.py`
- `tests/test_integration.py`
- `tests/test_observer.py`
- `tests/test_reservations.py`

## Oluşturulan dosyalar (59)

- `CHANGELOG.md`
- `docs/GUVENLIK.md`
- `docs/V2_DENETIM.md`
- `docs/audit/documentation-links-stage23.json`
- `docs/audit/pytest-stage23.json`
- `docs/screenshots/stage23/analitik.png`
- `docs/screenshots/stage23/dashboard-acik.png`
- `docs/screenshots/stage23/dashboard-koyu.png`
- `docs/screenshots/stage23/dashboard-mobil.png`
- `docs/screenshots/stage23/giris-hatasi.png`
- `docs/screenshots/stage23/giris.png`
- `docs/screenshots/stage23/pdf-okuyucu.png`
- `docs/screenshots/stage23/raporlar.png`
- `docs/screenshots/stage23/sesli-kitap.png`
- `docs/screenshots/stage23/tasarim-kaliplari.png`
- `docs/screenshots/stage23/ui-test-result.json`
- `docs/screenshots/stage23/uye-karti.png`
- `routes/analytics.py`
- `routes/categories.py`
- `routes/digital.py`
- `routes/member_cards.py`
- `routes/member_portal.py`
- `routes/reports.py`
- `routes/system.py`
- `services/account_security.py`
- `services/analytics.py`
- `services/backups.py`
- `services/circulation_policy.py`
- `services/digital_service.py`
- `services/maintenance.py`
- `services/member_card.py`
- `services/member_portal.py`
- `services/reports.py`
- `static/js/digital.js`
- `static/js/print.js`
- `static/js/scan.js`
- `static/vendor/jsQR.LICENSE`
- `static/vendor/jsQR.js`
- `templates/analytics.html`
- `templates/audit.html`
- `templates/categories.html`
- `templates/circulation_settings.html`
- `templates/digital_library.html`
- `templates/digital_reader.html`
- `templates/member_card.html`
- `templates/member_profile.html`
- `templates/member_scan.html`
- `templates/member_shelf.html`
- `templates/password.html`
- `templates/password_reset.html`
- `templates/penalties.html`
- `templates/reports.html`
- `tests/test_analytics.py`
- `tests/test_circulation_v2.py`
- `tests/test_digital.py`
- `tests/test_member_cards.py`
- `tests/test_member_portal.py`
- `tests/test_reports.py`
- `tests/test_system_v2.py`

## Güncellenen dosyalar (49)

- `README.md`
- `app.py`
- `database.py`
- `docs/KULLANIM_KILAVUZU.md`
- `docs/KURULUM.md`
- `docs/MIMARI.md`
- `docs/TASARIM_KALIPLARI.md`
- `docs/TEST.md`
- `docs/diagrams/factory_method.mmd`
- `models/book.py`
- `patterns/factory_method.py`
- `patterns/observer.py`
- `requirements.txt`
- `routes/auth.py`
- `routes/books.py`
- `routes/design_patterns.py`
- `routes/loans.py`
- `routes/notifications.py`
- `routes/settings.py`
- `schema.sql`
- `scripts/check_ui.cjs`
- `scripts/generate_uml.py`
- `services/book_service.py`
- `services/dashboard_service.py`
- `services/loan_service.py`
- `services/member_service.py`
- `services/notification_service.py`
- `services/reservation_service.py`
- `static/css/style.css`
- `static/images/uml-factory.svg`
- `static/js/books.js`
- `static/js/theme.js`
- `static/js/ui.js`
- `templates/base.html`
- `templates/book_form.html`
- `templates/books.html`
- `templates/design_patterns.html`
- `templates/error.html`
- `templates/loans.html`
- `templates/login.html`
- `templates/notifications.html`
- `templates/overview.html`
- `templates/reservations.html`
- `templates/settings.html`
- `tests/test_database.py`
- `tests/test_frontend.py`
- `tests/test_integration.py`
- `tests/test_observer.py`
- `tests/test_reservations.py`
