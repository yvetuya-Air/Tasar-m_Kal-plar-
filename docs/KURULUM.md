# Kurulum Kılavuzu

## V2 yükseltmesi

Sunucuyu durdurun, SQLite dosyasının [yedekleme komutuyla](GUVENLIK.md) yedeğini alın ve `init-db` ile `check-db` çalıştırın. Dijital dosyalar yeni yedeklerde SQLite verisiyle birlikte tutulur. Var olan kurulumda `seed-demo` komutunu çalıştırmanız gerekmez.

20 Kasım 2026 tarihinde temiz kaynak kopyasında Python 3.13.2 ve mevcut sanal ortamla 12 kurulum, giriş ve sayfa adımı başarıyla doğrulandı. Yeni sanal ortam oluşturuldu, ancak paket kaynağı Flask için kullanılabilir dağıtım döndürmedi. Linux/macOS ve GitHub üzerinden klonlama bu teslimde doğrulama kapsamı dışında kaldı. [Kurulum kaydı](audit/setup-stage443.json) · [GitHub komutları](GITHUB_YAYINLAMA.md).

**EBLG443 — Tasarım Kalıpları · Kütüphane Yönetim Sistemi · Proje Gelişimi 1**

## 1. Sistem gereksinimleri

Python 3.11+, pip, Git ve güncel tarayıcı gerekir. SQLite Python ile gelir. PDF ve ses doğrulaması, QR, PDF raporu ve Excel için requirements.txt içindeki bağımlılıkları kurun. İnternet paket kurulumu ve harici katalog aramaları için gerekir. Kamera erişimi için HTTPS veya yerel adres kullanılır. Node.js/Playwright tarayıcı testinde kullanılır.

## 2. Python ve Git kurulumu

Python'u [resmî indirme sayfasından](https://www.python.org/downloads/), Git'i [resmî Git sayfasından](https://git-scm.com/downloads) kurun. Windows'ta PATH ve Python launcher seçeneklerini etkinleştirin; terminali yeniden açın.

```powershell
py --version
git --version
```

`py` yoksa `python --version` ile yorumlayıcıyı doğrulayıp `py` yerine `python` kullanın. Linux/macOS'ta genellikle `python3` kullanılır; pip/venv işletim sistemi paketlerinden sağlanabilir.

## 3. Projenin indirilmesi

Henüz atanmış uzak depo URL'si yoktur; sahte adres verilmez. Yayın sonrasında GitHub **Code → HTTPS** adresini kopyalayıp:

```powershell
$repoUrl = Read-Host 'Gerçek Git depo adresi'
git clone $repoUrl proje_tasarim
Set-Location proje_tasarim
```

ZIP kullanıyorsanız arşivi açın ve `app.py` ile `requirements.txt` bulunan klasörde terminal açın. Mevcut çalışma kopyasında bu adımı atlayın. Gerçek uzak depo bulunmadığından clone adımı canlı depoya karşı yürütülmemiştir.

## 4. Sanal ortam ve bağımlılıkların yüklenmesi

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Etkinleştirme zorunlu değildir; açık Python yolu PowerShell yürütme ilkesini değiştirmez. İsteğe bağlı `.\.venv\Scripts\Activate.ps1` kullanılabilir. [requirements.txt](../requirements.txt) sürüm aralıkları belirtir; kilit dosyası değildir. [Teslim test ortamı sürümleri](audit/dependencies-stage443.json) ayrıca saklanır.

## 5. Ortam değişkenlerinin ayarlanması

Mevcut `.env` yoksa:

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Çıktıyı yalnız yerel `.env` içindeki `SECRET_KEY` alanına yazın; paylaşmayın.

| Değişken | Anlamı |
| --- | --- |
| SECRET_KEY | İmzalı oturum anahtarı. Boşsa süreç başına rastgele üretilir; yeniden başlatma eski çerezleri geçersiz kılar. Kalıcı, gizli değer önerilir. |
| GOOGLE_BOOKS_API_KEY | İsteğe bağlı sunucu anahtarı; anahtarsız erişim kota nedeniyle reddedilebilir. |
| SESSION_COOKIE_SECURE | Yerel HTTP için false, HTTPS için true. HTTP üzerinde true oturum çerezinin gönderilmesini engeller. |

`config.py`, kökteki `.env` dosyasını okur. Değişiklikten sonra sunucuyu yeniden başlatın. Normal veritabanı yolu `instance/library.sqlite3`'tür; `DATABASE` adlı ortam değişkeni otomatik okunmaz. Testler yolu `create_app` yapılandırmasıyla değiştirir. `.env`, gerçek veritabanı ve yedekler Git dışında tutulur.

## 6. Veritabanının hazırlanması ve demo hesaplar

Boş yerel gösterim kurulumu için sıralı komutlar:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app init-db
.\.venv\Scripts\python.exe -m flask --app app:create_app seed-demo
.\.venv\Scripts\python.exe -m flask --app app:create_app demo-accounts
.\.venv\Scripts\python.exe -m flask --app app:create_app check-db
```

`init-db` SQLite tablolarını, indeksleri, görünümleri ve tetikleyicileri hazırlar. Mevcut kayıtları korur. Eski users tablosunda eksikse session_version ekler. `seed-demo` yalnız boş veritabanını kabul eder; işaretli küme zaten varsa tekrar yüklemez. `demo-accounts` gösterim işaretini gerektirir ve ilk hazırlamadan sonra parolaları değiştirmez. Yalnız init-db çalıştırılmış boş sistemde giriş hesabı yoktur; herkese açık kayıt veya üretim hesabı oluşturma CLI'si bulunmaz.

| Rol | Kullanıcı adı | Yalnız yerel gösterim parolası |
| --- | --- | --- |
| Yönetici | demo_yonetici | DemoYonetici!2026 |
| Üye | demo_uye | DemoUye!2026 |

Bu açık test hesapları özel parola değildir. Gösterim kümesinde iki kitap, üç üye, bir kategori, iki ödünç, bir rezervasyon ve etiketli bir gösterim bildirimi vardır. demo_uye öğrenci kaydına bağlıdır; başlangıç bildirimi öğretmen kaydına aittir. Bu nedenle demo üyesinin bildirim sayısı sıfır olabilir.

Gösterim tarihleri yükleme makinesinin takvim gününden türetilir. Gerçek ödünç/iade hizmetleri ise açıkça UTC+3 Türkiye gününü kullanır; test senaryolarının sabit tarihleri ana veriye uygulanmaz.

Mevcut veritabanını güncellerken sunucuyu durdurup SQLite backup API veya uygun araçla yedek alın. Sonra yalnız `init-db`, `check-db` çalıştırın. Gerçek veri varsa `seed-demo` çalıştırmayın; hatayı aşmak için dosyayı silmeyin. Oturum sürümü geçişinden sonra yeniden giriş gerekir.

Aşama 13 geçişinde `init-db` kitap tablosuna kapak adresi, açıklama, yayınevi, yayın yılı ve dil sütunlarını ekler. Mevcut kayıtlar ve ilişkiler korunur. Open Library anahtar gerektirmez. Google Books kurulumu ve kota davranışı [harici katalog kılavuzunda](ADAPTER.md) açıklanır.

## 7. Uygulamanın çalıştırılması

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

http://127.0.0.1:5000/giris giriş sayfası, `/` tanıtım, `/panel` gerçek paneldir. Terminal açık kalmalıdır; `Ctrl+C` durdurur. Port meşgulse `--port 5001` kullanılabilir; aynı anda arayüz test sunucusu bu portta çalışmamalıdır. Flask geliştirme sunucusu yerel ders gösterimine yöneliktir.

### Linux / macOS karşılıkları

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
cp .env.example .env
.venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
# Çıktıyı .env içindeki SECRET_KEY alanına yazın.
.venv/bin/python -m flask --app app:create_app init-db
.venv/bin/python -m flask --app app:create_app seed-demo
.venv/bin/python -m flask --app app:create_app demo-accounts
.venv/bin/python -m flask --app app:create_app check-db
.venv/bin/python -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

POSIX komutları yol karşılıklarıdır; bu aşamada Linux/macOS üzerinde yürütülmemiştir.

## 8. Test ve belge kontrolleri

İkinci terminalde:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/sync_doc_sources.py --check
.\.venv\Scripts\python.exe scripts/check_docs.py
```

Test verisi `.test-tmp` altındadır; ana veritabanını temizlemek gerekmez. Gerçek sonuçlar ve isteğe bağlı tarayıcı kurulumu [TEST.md](TEST.md), kurulum doğrulaması [teslim kaydındadır](audit/setup-stage443.json).

## 9. Olası hatalar ve çözümleri

| Belirti | Neden ve çözüm |
| --- | --- |
| ERR_CONNECTION_REFUSED | Sunucu kapalı/farklı portta. run başlatın; terminalde gösterilen adresi açın. |
| 404 | Yanlış yol/eski süreç. /giris veya /panel kullanın; proje kökünden yeniden başlatın. |
| pip: No matching distribution found | Python sürümünü ve paket indeksine ağ erişimini kontrol edin. |
| ModuleNotFoundError | Yanlış Python. .venv içindeki açık yorumlayıcıyla pip install ve run kullanın. |
| SQLite 503 / no such table | init-db eksik veya dosya erişilemiyor. Yedekleyip init-db, check-db çalıştırın; yazma iznini kontrol edin. |
| 401 | Hatalı giriş veya pasif hesap. Demo için seed-demo sonrasında demo-accounts gereklidir. |
| 400 form reddi | Eksik/eski CSRF veya bozuk girdi. Sayfayı yenileyin, gerekirse tekrar giriş yapın; korumayı kapatmayın. |
| 403 | Rol yetkisiz. Yönetici işlemlerinde Yönetici hesabı gerekir. |
| 409 / 422 | Çift iade, geçmişli kitap silme, ISBN tekrarı veya geçersiz alan. Türkçe açıklamayı izleyin. |
| Oturum tutulmuyor | HTTP üzerinde Secure=true veya değişen SECRET_KEY. Yerelde false ve sabit gizli anahtar kullanın. |
| Google kota/erişim hatası | Ağ, izin veya kota. Anahtarı yerel ortamda kontrol edin; yeniden başlatın veya daha sonra deneyin. |
| pytest WinError 5 | Geçici dizin izni/kilidi. Güncel conftest benzersiz .test-tmp yolu üretir; proje yazma iznini kontrol edin. |
| database is locked | Eşzamanlı uzun yazma. Diğer işlemi bitirip tekrar deneyin; transaction korumasını kaldırmayın. |
| Eski CSS/JS | Ctrl+F5; doğru süreç ve portu kontrol edin. |

[Ana sayfa](../README.md) · [Kullanım](KULLANIM_KILAVUZU.md) · [Mimari](MIMARI.md)
