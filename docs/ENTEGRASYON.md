# Frontend ve Backend Entegrasyonu — Aşama 9

## Kapsam

Mevcut Flask/SQLite projesinde 30 rota, Jinja form hedefleri, dahili bağlantılar,
statik dosyalar, rol izinleri, CRUD, üye geçmişi, dört kalıp ve kalıcılık denetlendi.
Proje yeniden oluşturulmadı. Onuncu aşama başlatılmamıştır.

Son sonuç: **338 Pytest başarılı**, **93 tarayıcı kontrolü başarılı**.
Gerçek Google Books araması kota nedeniyle başarısızdır; dış hizmet sonucu
yerel entegrasyon başarısıyla karıştırılmamıştır.

Yazma testleri `.test-tmp` altındaki ayrı veritabanlarını kullanır. Ana veritabanına
kitap, üye, ödünç veya rezervasyon eklenmedi/silinmedi.

## Düzeltilen bulgular

| Bulgu | Önce | Sonra |
| --- | --- | --- |
| Unicode CSRF | compare_digest TypeError verebiliyordu | 400, veri/oturum korunur |
| Çok büyük kimlik | SQLite OverflowError oluşabiliyordu | Formda 422, URL'de 404 |
| /uyeler/0/duzenle | Yanlışlıkla ekleme formu gösterebiliyordu | 404 |
| Google önizleme hatası | Arama yanlışlıkla tekrar /aktar yoluna gidebiliyordu | Açık action: /kitaplar/google |
| Boyut/SQL hataları | Genel veya İngilizce hata | Ayrıntı sızdırmayan Türkçe 413/503 |
| Statik kaynaklar | Oturum için SQL sorgusu çalışıyordu | CSS/JS veritabanından bağımsız |
| Boşluk raf konumu | Doğrudan ürün doğrulaması kabul edebiliyordu | Factory ürünü de reddeder |
| Yeni üyenin özel mesaj erişimi | Oluşturulan üye için bağlı hesap yolu yoktu | Yönetici isteğe bağlı Üye hesabı oluşturabilir |

Kimlik sınırı 1–9223372036854775807'dir. Çok uzun ve geçersiz değer SQL'e gönderilmez.
Sayfalama ve LIKE kaçışı ortak yardımcıya taşındı; kullanılmayan importlar kaldırıldı.

## Rotalar, formlar ve yetkiler

Envanter: [audit/routes.json](audit/routes.json). HEAD/OPTIONS Flask tarafından üretilir.
`test_every_flask_route_permissions` bütün rotaları oturumsuz/Yönetici/Üye
bağlamlarında sınar; tüm POST yolları CSRF'siz isteği reddeder.

`test_rendered_forms_navigation_and_assets` açılabilen bütün sayfalarda form
action/yönteminin gerçek rotaya eşleşmesini, POST jetonunu, dahili bağlantıları,
sayfa içi hedefleri ve yerel CSS/JS/UML dosyalarını doğrular.
Tarayıcı kontrolü düğmeleri ve iki ayrı kullanıcı oturumunu da çalıştırır.

Üyeler dizini ve yönetim yazmaları yalnız Yöneticiye açıktır. Üyeler yalnız kendi
ödünç, rezervasyon ve bildirimlerini görür. URL/formdaki başka `member_id`, rol veya
ücret verisi bu kapsamı genişletmez. Başkasının özel mesaj/rezervasyon işlemi 404 döner.

## Üye ile giriş hesabı bağlantısı

Yeni veya henüz hesabı olmayan üyede **Giriş kullanıcı adı** ve **Yeni hesap parolası**
alanları isteğe bağlıdır. İkisi boşsa önceki davranış korunur: yalnız üye oluşur.

- Kullanıcı adı 3–80 ASCII harf/rakam/nokta/alt çizgi/tire; parola 8–256 karakter.
- Rol sunucuda daima `member`; formdan `role=admin` göndermek yetki vermez.
- Parola Werkzeug ile hashlenir; hata yanıtı veya günlüğe açık yazılmaz.
- Üye, hesap, bağlantı ve günlük tek SQLite işlemindedir; hata hepsini geri alır.
- Mevcut bağlı hesap bu formdan yeniden adlandırılmaz veya parolası değiştirilmez.
- Pasifleştirme geçmişi korur, yeni ödünç/rezervasyonu ve bağlı oturumu engeller.
  İade yapılabilir; yeniden aktifleştirme aynı hesabı kullanır.

Bu herkese açık kayıt veya parola sıfırlama değildir. Son 50 ödünç kaydı ve kesin
cezalar yönetici üye geçmişinde gösterilir; üyelik türü gelecekteki iade tarifesini belirler.

## Tam senaryo — gerçek uygulama yolları

`test_complete_factory_adapter_strategy_observer_workflow_and_restart`, boş bir
test SQLite dosyasında aşağıdaki zinciri HTTP formlarıyla çalıştırır:

| Adım | İşlem | Doğrulama |
| --- | --- | --- |
| 1 | Yönetici girişi | /giris |
| 2 | Factory Method ile fiziksel kitap | /kitaplar/ekle |
| 3 | Adapter arama/önizleme/düzeltme/elektronik kayıt | Yalnız dış HTTP yanıtı taklit; gerçek Adapter ve Factory |
| 4 | İki üye ve bağlı Üye hesapları | /uyeler/ekle; rol yükseltme girdisi etkisiz |
| 5 | İlk üyeye ödünç | Stok 0 |
| 6 | İkinci üyeye rezervasyon | Aktif bekleme kaydı |
| 7 | Üç gün gecikmiş iade | /odunc/ID/iade |
| 8 | Strategy | Öğrenci 2 TL × 3 gün = 6 TL; 600 kuruş |
| 9 | Observer | İkinci üyeye tek özel bildirim; notified durumu |
| 10 | Dashboard | Aynı SQLite kayıtlarından doğru sayaçlar |

Yalnız testte saat 1 Kasım'dan 11 Kasım'a ilerletilir; son teslim 8 Kasım'dır.
Ürün arayüzü sahte geçmiş iade tarihi veya ücret kabul etmez. Çift iade ve yinelenen
ISBN reddedilir. Bildirim sahibi okundu yapabilir; diğer üye okuyamaz/işaretleyemez.

Son panel: **2 kitap, 2 mevcut kitap kaydı, 2 üye, 0 aktif ödünç, 0 gecikmiş ödünç,
1 bekleyen/bildirilmiş rezervasyon**. Bunlar ana kütüphanenin istatistikleri değil,
izole senaryonun gerçek test kayıtlarıdır.

## Yeniden başlatma kalıcılığı

Senaryonun sonunda yeni Python sürecinde yeni Flask uygulaması oluşturulur.
Kitap/üye sayısı, 600 kuruş ceza, iade tarihi, rezervasyon ve okunma durumu doğrulanır;
üye yeniden giriş yapıp bildirim sayfasını açar.

Ayrıca gerçek ana sunucu yeniden başlatıldı. `scripts/check_persistence.py` sekiz
tablonun satır sayıları ve bütün içeriklerinin SHA-256 özetlerini önce/sonra eşit
buldu. Özet dosyası kişisel kayıt veya parola içeriği barındırmaz ve Git dışında tutulur.

```powershell
.\.venv\Scripts\python.exe scripts/check_persistence.py capture --snapshot .test-tmp/restart.json
# Sunucuyu Ctrl+C ile durdurup normal Flask komutuyla yeniden başlatın.
.\.venv\Scripts\python.exe scripts/check_persistence.py verify --snapshot .test-tmp/restart.json
```

## Sabit örnek veri temizliği

Operasyonel ekranlarda sabit kitap/üye listesi veya istatistik yoktur. Gösterim
veritabanı panelde etiketlenir; boş veride sıfır/boş durum gösterilir.
Kalıp gösterimlerindeki sabit hayalî kitap adları da kaldırıldı. Factory ve Observer
katalogdaki gerçek kaydı kullanır; Adapter aynı kayıttan Google biçimli JSON üretir.
Bu JSON'un canlı Google yanıtı olmadığı açıkça belirtilir. Boş katalogda sahte kayıt
üretilmez. Strategy güncel tarih ve kullanıcının gün sayısını kullanır.
Eğitim örnekleri veri yazmaz; gerçek iş akışlarının yerine geçmez.

## Gerçek Google Books sınırı

Bu aşamadaki ayrı gerçek `Nutuk` araması, anahtar olmayan mevcut yapılandırmada
Google kota/hız sınırı hatası aldı. Canlı arama veya gerçek API'den başarılı aktarım
iddia edilmez. `.env` içindeki `GOOGLE_BOOKS_API_KEY` ve Google erişimi/kotası
düzeltilmelidir. Yerel CRUD ve ödünç işlemleri bu dış koşuldan bağımsızdır.
Otomatik test yalnız dış yanıtı taklit eder; Adapter, form, Factory ve SQLite gerçektir.

## Tekrar çalıştırma

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_integration.py tests/test_frontend.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flask --app app:create_app check-db
.\.venv\Scripts\python.exe -m pip check
```

Chrome kontrolü için [Arayüz](ARAYUZ.md) belgesindeki ayrı test sunucusunu kullanın.
Güncel sonuçlar: [TEST.md](TEST.md), [ui-test-result.json](screenshots/ui-test-result.json).
