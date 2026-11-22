# Frontend ve kullanıcı arayüzü — Aşama 8

## Kapsam

HTML5, Jinja2, CSS3 ve bağımlılıksız JavaScript ile ortak uygulama kabuğu oluşturuldu.
Mevcut Flask hizmetleri korunur; kitap, ödünç, rezervasyon, bildirim ve Google Books
işlemleri aynı gerçek uç noktalara bağlıdır. Devamındaki denetim: [Entegrasyon](ENTEGRASYON.md).

Yeni Python bağımlılığı veya veritabanı şema geçişi yoktur. Kod güncellemesinden sonra
sunucuyu yeniden başlatın:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app run
```

Adres: http://127.0.0.1:5000/giris. Giriş sonrası `/panel` genel bakış sayfasını açar.

## Görsel sistem

- Lacivert sabit sidebar; beyaz/gri çalışma alanı ve turkuaz vurgu.
- Profil, tema düğmesi ve kişisel bildirim bağlantısı içeren üst çubuk.
- Ortak butonlar, form alanları, durum etiketleri, tablolar ve yerel SVG ikonları.
- Açık/koyu/sistem temaları; rahat/kompakt tablo yoğunluğu.
- 980 piksel altında klavyeyle kullanılabilen mobil çekmece; Escape ve arka planla kapanır.
- Tablet/telefon düzenleri; geniş tablolar yalnızca kendi kapsayıcısında kaydırılır.
- Odak göstergeleri, içeriğe geç bağlantısı, etiketli alanlar, başlıklı tablolar,
  canlı durum mesajları ve azaltılmış hareket tercihine saygı.
- JavaScript kapalıyken form/arama/oturum işlevleri sunucuda çalışır; mobil menü
  normal belge akışında gösterilir. Tema tercih düğmeleri JavaScript gerektirir.

Tema ve yoğunluk yalnızca `localStorage` içinde, bu tarayıcıda saklanır.
Sunucudaki hesap veya SQLite kayıtlarını değiştirmez; aynı tarayıcıyı paylaşan
hesaplar görünüm tercihini paylaşır. Depolama engellenirse tercih
yalnızca mevcut sayfaya uygulanır ve kullanıcıya bu durum bildirilir.

## Sayfalar ve erişim

| Sayfa | Yol | Erişim / gerçek veri |
| --- | --- | --- |
| Genel Bakış | /panel | Oturum; role göre gerçek SQLite istatistikleri |
| Kitaplar | /kitaplar | Oturum; düzenleme işlemleri Yönetici |
| Üyeler | /uyeler | Yalnızca Yönetici |
| Ödünç İşlemleri | /odunc | Yönetici tüm, üye kendi kayıtları |
| Rezervasyonlar | /rezervasyonlar | Yönetici tüm, üye kendi kayıtları |
| Bildirimler | /bildirimler | Yalnızca oturum sahibinin mesajları |
| Tasarım Kalıpları | /tasarim-kaliplari | Oturum; gerçek kaynak kodu ve eğitim örnekleri |
| Ayarlar | /ayarlar | Oturum; tarayıcı tercihleri ve kendi hesap bilgisi |
| Giriş | /giris | Herkes; mevcut CSRF korumalı kimlik doğrulama |

Önceki `/yonetim`, `/hesabim`, simülatör, Google Books ve CRUD yolları korunmuştur.
Menüde saklamak erişim kontrolü sayılmaz; rotaların sunucu dekoratörleri sürmektedir.

## Gerçek dashboard verileri

`services/dashboard_service.py` değerleri her istekte SQLite'tan hesaplar:

- Yönetici: toplam kitap kaydı, en az bir kopyası/lisansı mevcut kitap kaydı,
  toplam üye, aktif ödünç, gecikmiş ödünç, bekleyen rezervasyon.
- Üye: kendi okunmamış mesajı, aktif ödüncü, gecikmiş ödüncü ve bekleyen rezervasyonu.
- Son altı ayın ödünç/iade sayıları; üyede yalnızca kendi işlemleri.
- Katalogdaki fiziksel/elektronik kayıt dağılımı; katalog oturum sahiplerine açıktır.
- Yöneticide gerçek işlem günlüğü; üyede kendi ödünç/iade olayları.
- En eski son teslim tarihine göre en fazla beş gecikmiş aktif ödünç.

Kitap sayısı kopya sayısı değildir; kart açıklamaları bunu belirtir. Boş veritabanında
sıfır ve boş durum gösterilir. Rastgele artış yüzdesi veya sabit örnek istatistik yoktur.
`demo_seed` kaydı varsa veritabanının gösterim kayıtları içerdiği açıkça belirtilir.
Gösterim kayıtları gerçek bir kütüphanenin üretim verisi olarak sunulmaz.

Grafikler yerel SVG ile oluşturulur; grafik kütüphanesi veya CDN gerekmez. Çubuklar
odak/üzerine gelme bilgisi, title ve aria etiketleri içerir. Aylık grafik ayrıca
açılabilir veri tablosuyla sunulur. Grafik değerleri sunucudaki aynı sorgulardan gelir.

## Üye sayfası

Yönetici üye ekleyebilir, ad/e-posta/tür bilgilerini değiştirebilir, üyeliği aktif/pasif
yapabilir ve son 50 ödünç kaydını görebilir. E-posta benzersizdir; geçersiz alanlar 422
ile Türkçe hata verir. Bütün yazmalar POST + CSRF + sunucu rol denetiminden geçer.
Değişiklik ve işlem günlüğü aynı SQLite işleminde yazılır.

Silme yerine pasifleştirme uygulanır; geçmiş korunur. Pasif üyeye yeni ödünç/rezervasyon
verilmez; mevcut kitabı iade edilebilir. Bağlı hesabın mevcut oturumu sonraki istekte
geçersiz olur. Dokuzuncu aşamada Yöneticiye isteğe bağlı giriş hesabı oluşturma
alanları eklenmiştir. Boş bırakılırsa yalnız üye kaydı oluşur; doldurulursa Üye
rolü, parola hash'i ve hesap bağlantısı aynı işlemde kaydedilir.
Üyelik türü değişikliği gelecekteki iade tarifesini etkiler; önce kaydedilmiş kesin cezalar korunur.

## Onay, hata ve boş durumlar

Rezervasyon iptali ve üye aktifliği değişimi erişilebilir dialog ile onay ister.
Vazgeçme veri yazmaz. JavaScript yoksa sunucuya gönderilen açık etiketli POST işlemi
çalışmaya devam eder. Kitap silme ve iade mevcut ayrı onay sayfalarını korur.
Flash mesajları kapatılabilir; form hataları girilen değerleri korur. Arama sonucu
yok, bildirim yok, üye geçmişi boş ve geciken ödünç yok durumları ayrı metinle sunulur.

## Tasarım Kalıpları eğitim sayfası

Dört kalıp için tanım, problem, çözüm, proje kullanımı, avantaj/dezavantaj,
sınıflar, gerçek Python kaynağından kod ve SVG UML diyagramı gösterilir.
`scripts/generate_uml.py` SVG'leri tekrar üretir; Mermaid kaynakları `docs/diagrams/` altında korunur.
SVG sunum nitelikleri CSP ile uyumludur; uzaktan çizim hizmeti kullanılmaz.

Çalışan gösterimler gerçek sınıfları çağırır, eğitim örneği olarak etiketlenir ve veri yazmaz:

- Factory Method: tür seçilince gerçek somut oluşturucu ve ürün oluşturulur/doğrulanır.
- Adapter: mevcut katalog kaydından Google biçiminde türetilen JSON gerçek adaptörden geçirilir;
  bunun canlı dış API yanıtı olmadığı belirtilir.
  Canlı Google araması mevcut Kitaplar sayfasında çalışmaya devam eder; gerçek kota sınırı korunur.
- Strategy: aynı PenaltyCalculator üzerinde üç strateji dinamik değiştirilir.
- Observer: gerçek konuya iki eğitim gözlemcisi bağlanır; ikinci abonelik kaldırılıp yayın denenebilir.
  Gerçek üyeye mesaj gönderildiği söylenmez; gerçek iade bildirim akışı değiştirilmez.

## Dosya haritası

| Dosya | Görev |
| --- | --- |
| templates/base.html | Sidebar, üst çubuk, profil, bildirim ve onay dialogu |
| templates/_icons.html | Ortak, yerel SVG ikon makrosu |
| templates/overview.html | SQLite dashboard ve SVG grafikler |
| static/css/style.css | Tasarım değişkenleri, iki tema ve responsive bileşenler |
| static/css/no-script.css | JavaScript'siz mobil menü |
| static/js/theme.js | İlk çizim öncesi tarayıcı tercihini uygular |
| static/js/ui.js | Tema, yoğunluk, mobil menü, onaylar ve grafik açıklamaları |
| services/dashboard_service.py | Role göre panel sorguları |
| services/member_service.py | Üye doğrulama ve işlemler |
| routes/members.py | Yönetici üye rotaları |
| routes/design_patterns.py | Kalıp içeriği ve gerçek sınıflı eğitim örnekleri |
| routes/settings.py | Tercihler ve güvenli hesap görünümü |

## Otomatik tarayıcı kontrolünü tekrar çalıştırma

Uygulama için Node.js gerekmez. Aşağıdaki araç yalnızca isteğe bağlı geliştirme kontrolüdür.
Yerel Chrome veya Edge ve Node.js varsa:

```powershell
npm.cmd install --prefix .ui-tools --no-save --package-lock=false playwright
# Her denemede yeni bir veritabanı adı kullanın; klasör .test-tmp altında kalmalıdır.
.\.venv\Scripts\python.exe scripts/ui_preview.py --database .test-tmp/ui-yeni.sqlite3 --port 5001
# İkinci terminal:
node scripts/check_ui.cjs
```

Test sunucusu yalnızca `.test-tmp` altındaki veritabanlarını kabul eder. Tarayıcı betiği
yalnızca `127.0.0.1:5001` üzerinde çalışır. Ana `instance/library.sqlite3` dosyasına yazmaz.
Yeni üye/kitap oluşturma gibi kontroller yalnızca bu ayrı gösterim veritabanında yapılır.
Test bittiğinde bu test sunucusunu `Ctrl+C` ile durdurun.

Ekran görüntüleri `docs/screenshots/` altında, makine okunur kontrol sonucu
`ui-test-result.json` içindedir. Mobil görüntüde kontrol sırasında oluşturulmuş ayrı
test kitap/üyesi bulunabilir; bütün sayılar o test SQLite dosyasının gerçek kayıtlarıdır.
Güncel gerçek test sonuçları [TEST.md](TEST.md) belgesindedir.
