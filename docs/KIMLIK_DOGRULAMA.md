# Backend ve kimlik doğrulama — Aşama 3

## Çalıştırma

Proje kökünde PowerShell:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app init-db
.\.venv\Scripts\python.exe -m flask --app app:create_app seed-demo
.\.venv\Scripts\python.exe -m flask --app app:create_app demo-accounts
.\.venv\Scripts\python.exe -m flask --app app:create_app run
```

`seed-demo` yalnızca boş veritabanına gösterim verisi ekler; mevcut gösterim kümesinde
tekrar çalıştırılabilir. Gerçek verilerin üzerine yazmaz. `demo-accounts` yalnızca
`demo_seed` işlem kaydıyla işaretli gösterim veritabanını kabul eder. İlk çalıştırmada
gösterim yöneticisinin parolasını aşağıdaki deneme parolasıyla günceller ve öğrenci
kaydına bağlı bir üye hesabı oluşturur. Sonraki çalıştırmalar parolaları değiştirmez.
Bu komut gerçek kullanıcı hesabı hazırlamak için kullanılmaz.

| Rol | Kullanıcı adı | Yerel deneme parolası |
| --- | --- | --- |
| Yönetici | demo_yonetici | DemoYonetici!2026 |
| Üye | demo_uye | DemoUye!2026 |

Bu bilgiler yalnızca yerel gösterim içindir; herkese açık bir sunucuda kullanılmamalıdır.
Veritabanında açık parola yerine Werkzeug `generate_password_hash` çıktısı tutulur.
Doğrulama `check_password_hash` ile yapılır. Mevcut kitap, ödünç ve rezervasyonlar korunur.

Adres: http://127.0.0.1:5000/giris

## Dosyalar ve sorumluluklar

| Dosya | Görev |
| --- | --- |
| app.py | Blueprint kayıtları, Türkçe hata sayfaları ve güvenlik başlıkları |
| routes/auth.py | Giriş/çıkış HTTP işlemleri ve istek başına kullanıcı yükleme |
| routes/dashboard.py | Özel panel ve rol korumalı sayfalar |
| services/auth_service.py | Parametreli kullanıcı sorguları, hash ve aktiflik denetimi |
| services/demo_accounts.py | İşlem içinde, tekrar çalıştırılabilir yerel hesap hazırlama |
| security.py | CSRF jetonu ve erişim dekoratörleri |
| templates/login.html | Türkçe ve duyarlı giriş formu |
| templates/panel.html | Rol bazlı panel ve oturumdaki üyeye ait profil |
| templates/error.html | Türkçe 400, 403, 404, 405 sayfaları |

## Rotalar

| Yol | Yöntem | Erişim |
| --- | --- | --- |
| / | GET | Herkes; önceki başlangıç sayfası |
| /giris | GET, POST | Herkes; POST için CSRF zorunlu |
| /cikis | POST | Oturum ve CSRF zorunlu; GET ile çıkış yapılamaz |
| /panel | GET | Aktif oturum |
| /yonetim | GET | Yalnızca Yönetici |
| /hesabim | GET | Yalnızca Üye; oturumdaki hesabın bağlı üye kaydı |

Oturumsuz ziyaretçi girişe yönlendirilir. Yanlış role 403 döner. Menüyü gizlemekten
bağımsız olarak sunucu tarafında izin kontrolü yapılır. Rol ve aktiflik her istekte
SQLite üzerinden yeniden okunur; istemciden rol veya üye kimliği kabul edilmez.
Pasif kullanıcı ve pasif üye kaydıyla giriş reddedilir; mevcut oturum da geçersiz olur.

## Oturum ve CSRF

Flask imzalı oturum çerezi kullanılır. İçerik şifrelenmiş değildir; parola veya hash
oturuma yazılmaz. Girişten önceki oturum temizlenir ve CSRF jetonu yenilenir.
Süre 30 dakikadır; her istekte otomatik uzatılmaz. Onuncu aşamada
`users.session_version` sunucu denetimi eklenmiştir. Çıkış bu sürümü artırır;
önceden kopyalanmış çerez ve aynı kullanıcının diğer tarayıcı oturumları reddedilir.
Üyelik pasifleştirme de sürümü artırır; yeniden etkinleştirme eski çerezi canlandırmaz.
Eski kurulumlar `init-db` çalıştırmalı ve yeniden giriş yapmalıdır.

Her POST/PUT/PATCH/DELETE isteğinde oturuma bağlı rastgele jeton doğrulanır.
Form `csrf_token` alanı veya `X-CSRF-Token` başlığı kabul edilir. Eksik/yanlış jetonda
400 döner; karşılaştırma `secrets.compare_digest` ile yapılır. Testlerde koruma kapatılmaz.

Çerez `HttpOnly` ve `SameSite=Lax` kullanır. Yerel HTTP için Secure kapalıdır.
HTTPS dağıtımında `.env` içine `SESSION_COOKIE_SECURE=true` yazılmalıdır.
`.env` içindeki kalıcı `SECRET_KEY` rastgele ve gizli tutulmalıdır. Örnek üretim:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Giriş yanıtı kullanıcı bulunamadı, yanlış parola veya pasif hesap ayrımını açıklamaz.
Harici `next` adreslerine yönlendirme yapılmaz. Jinja otomatik kaçış kullanır.
HTML yanıtları `Cache-Control: no-store` alır; CSP, çerçeveleme ve MIME başlıkları eklenir.
Herkese açık hesap açma, parola sıfırlama, MFA ve dağıtık giriş hız sınırlaması yoktur.
Dokuzuncu aşamada Yönetici, Üyeler formundan isteğe bağlı bağlı Üye hesabı
oluşturabilir. Yetkiler ve işlem kuralları: [Entegrasyon](ENTEGRASYON.md).

## Elle kontrol

1. `/panel` adresini oturumsuz açın: giriş sayfasına yönlenmelidir.
2. Yanlış parola girin: Türkçe hata görünmeli ve oturum açılmamalıdır.
3. Yöneticiyle giriş yapın: panel ve yönetici alanı açılmalıdır.
4. Çıkış yapın: yeniden `/panel` açıldığında giriş istenmelidir.
5. Üye ile giriş yapın: Hesabım sayfasında Demo Öğrenci görünmelidir.
6. Üye oturumunda `/yonetim` açın: Türkçe 403 sayfası görünmelidir.
7. Pencereyi daraltın: giriş sayfası tek sütuna geçmeli, alanlar taşmamalıdır.

Otomatik sonuçlar ve tamamlanan tarayıcı doğrulaması: [TEST.md](TEST.md).

## Eski sunucu / 404 sorunu

Kod değiştiğinde debug kapalı sunucu eski sürümü sunmaya devam edebilir.
Sunucunun açık olduğu terminalde `Ctrl+C` ile durdurup yukarıdaki `run` komutuyla
yeniden başlatın. `flask --app app:create_app routes` çıktısında `/giris` görünmelidir.

## Teknik kaynaklar

- [Flask güvenlik açıklamaları](https://flask.palletsprojects.com/en/stable/web-security/)
- [Werkzeug parola hash araçları](https://werkzeug.palletsprojects.com/en/stable/utils/)

Bu belge üçüncü aşamayı açıklar. Dördüncü aşamanın devamı:
[Kitap yönetimi](KITAPLAR.md) ve [Factory Method](TASARIM_KALIPLARI.md).
