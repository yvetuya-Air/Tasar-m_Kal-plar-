# Veritabanı ve veri modelleri — Aşama 2

## Kurulum ve doğrulama

Proje kökünde PowerShell komutları:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app init-db
.\.venv\Scripts\python.exe -m flask --app app:create_app seed-demo
.\.venv\Scripts\python.exe -m flask --app app:create_app check-db
.\.venv\Scripts\python.exe -m pytest -q
```

`init-db`, `schema.sql` dosyasını kullanarak `instance/library.sqlite3` dosyasını oluşturur.
Tekrar çalıştırıldığında kayıt silmez. Bu komut şema geçiş sistemi değildir;
gelecekte var olan tabloların yapısı değişirse ayrıca sürümlü geçiş hazırlanmalıdır.
Uygulama açılırken otomatik veri eklenmez.

`seed-demo` yalnızca boş bir veritabanını doldurur; aynı gösterim kümesi varsa tekrar eklemez.
Başka veri varsa işlemi reddeder. Ekleme tek işlemde yapılır; hata olursa geri alınır.
Gösterim verileri gerçek kullanıcı veya kütüphane istatistiği değildir.

## Gösterim kümesi

| Tablo | Kayıt sayısı | İçerik |
| --- | --- | --- |
| users | 1 | Demo yönetici, rastgele parolanın güvenli hash değeri |
| members | 3 | Öğrenci, öğretmen, normal üye |
| categories | 1 | Gösterim Koleksiyonu |
| books | 2 | Bir fiziksel kitap, iki lisanslı bir e-kitap |
| loans | 2 | Bir gecikmiş aktif ödünç, bir tamamlanmış ödünç |
| reservations | 1 | Mevcut olmayan fiziksel kitap için aktif rezervasyon |
| notifications | 1 | Açıkça gösterim olarak işaretlenmiş bildirim |
| activity_logs | 1 | Gösterim yükleme kaydı |

E-posta ve dosya adreslerinde `example.invalid` kullanılır; gerçek adres değildir.
Tarihler yükleme gününe göre oluşturulur. Yönetici parolası yayımlanmaz ve oturum açma
bu aşamada yoktur. Bildirim örneği Observer uygulandığı anlamına gelmez.

## Modeller ve sorumluluklar

`models/` altında `User`, `Member`, `Category`, `Book`, `Loan`, `Reservation`,
`Notification`, `ActivityLog` değiştirilemez veri sınıflarıdır. `from_row` SQLite satırını
tipli nesneye dönüştürür; SQL sorguları bu sınıflara gömülmez. Boolean alanlar dönüştürülür.
Parola hash değeri `User` nesnesinin metin gösteriminden çıkarılır.
Modeller veritabanına yazmaz; bütünlük kontrolü SQLite kısıtlarındadır.
`PhysicalBook`, `EBook` ve oluşturucu sınıfları dördüncü aşamada eklenmiştir.
`Book` soyut ürün olarak güncellenmiş, `Book.from_row()` uyumluluğu korunmuştur.

## İlişkiler

- Bir kullanıcı en fazla bir üyeye bağlanabilir; kullanıcı hesabı olmayan üye kaydı mümkündür.
- Bir kategori birden çok kitap içerir; kategori ataması isteğe bağlıdır.
- Bir kitap ve bir üye birden çok tarihsel ödünç/rezervasyona sahip olabilir.
- Bildirim üyeye ve isteğe bağlı rezervasyona bağlıdır.
- İşlem günlüğü isteğe bağlı kullanıcıya bağlıdır.

İlişkili geçmiş kayıtları olan kitaplar, üyeler veya kullanıcılar yabancı anahtarlarla korunur.
Aktiflik alanı silme yerine devre dışı bırakmayı destekler. Kimlik doğrulama ve yetkilendirme
üçüncü aşamaya aittir; mevcut başlangıç sayfası değişmemiştir.

## Bütünlük kararları

- Her bağlantıda `PRAGMA foreign_keys=ON`; bağlantı Flask bağlamı sonunda kapatılır.
- Parametreli SQL ile değerler sorgulardan ayrılır.
- `book_inventory` görünümü: kullanılabilir adet = toplam adet − aktif ödünç sayısı.
  E-kitaplar için de sınırlı lisans adedi varsayılmıştır.
- Stoksuz ödünç, pasif üyeye ödünç, aynı üye/kitap için çift aktif ödünç reddedilir.
- İade edilmiş ödünç kaydı tekrar değiştirilemez; ödünç geçmişi silinemez.
- Stok aktif ödünç sayısının altına indirilemez.
- Mevcut kitaba yeni aktif rezervasyon ve çift aktif rezervasyon reddedilir.
- Rezervasyon geçişleri: active → notified/cancelled/fulfilled;
  notified → cancelled/fulfilled. Sonlanmış kayıt yeniden etkinleştirilemez.
- Tarihler ISO `YYYY-MM-DD`; iade ve son teslim ödünç tarihinden önce olamaz.
- Para değerleri kayan nokta yerine negatif olmayan tamsayı kuruş olarak tutulur.

Bu belge ikinci aşamadaki SQL katmanını açıklar. Rezervasyon sırası, ceza hesabı
ve otomatik bildirimler sonraki aşamalarda uygulanmıştır; güncel iş akışları
[Mimari](MIMARI.md) ve [Tasarım Kalıpları](TASARIM_KALIPLARI.md) içindedir.

Sınıf/ilişki çizimi: [ER diyagramı](diagrams/veritabani.mmd).
