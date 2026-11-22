# Kitap yönetimi — Aşama 4

## Kullanım

Sunucuyu proje kökünden çalıştırın:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app run
```

Kod değişikliğinden önce sunucu açıksa `Ctrl+C` ile durdurup tekrar başlatın.
`/giris` adresinden oturum açtıktan sonra menüde **Kitaplar** bağlantısını seçin.
Adres: http://127.0.0.1:5000/kitaplar

Üye ve yönetici kitap adı/yazar/ISBN ile arama yapabilir. Türkçe I/ı ve İ/i eşleşmesi
desteklenir. `%` ve `_` joker yerine normal karakter olarak aranır. Sonuçlar 20 kayıtlık
sayfalara ayrılır. Google Books aktarımı beşinci aşamada eklenmiştir:
[Adapter kullanımı](ADAPTER.md).

Yönetici **Kitap ekle**, **Düzenle**, **Sil** işlemlerini yapabilir. Üye bu işlemlerin
URL adresine doğrudan ulaşsa bile sunucu 403 döndürür. Silme önce onay sayfası gösterir;
GET isteği kayıt silmez. Tüm değişiklikler POST ve CSRF doğrulaması gerektirir.

## Rotalar

| Yol | Yöntem | Erişim |
| --- | --- | --- |
| /kitaplar | GET | Aktif oturum; arama ve sayfalama |
| /kitaplar/ekle | GET, POST | Yönetici |
| /kitaplar/ID/duzenle | GET, POST | Yönetici |
| /kitaplar/ID/sil | GET, POST | Yönetici; POST siler |

## Sunucu doğrulamaları

- Kitap adı 1–200, yazar 1–160 karakter. Baştaki/sondaki boşluklar temizlenir.
- ISBN isteğe bağlı; varsa geçerli kontrol basamaklı ISBN-10/ISBN-13 gerekir.
  Boşluk/tire kaldırılır, X büyük harfe çevrilir. Aynı normalize ISBN tekrar eklenemez.
- Kategori isteğe bağlıdır; seçildiyse var olan kategori olmalıdır.
- Adet/lisans sayısı tamsayı ve 1–10000 aralığında olmalıdır.
- Fiziksel kitap raf konumu ister (en fazla 80 karakter); dosya adresi boş olmalıdır.
- Elektronik kitap HTTP/HTTPS dosya adresi ister (en fazla 2000 karakter);
  kullanıcı/parola içeren URL ve boşluklar reddedilir. Raf boş olmalıdır.
- Dosya sunucudan indirilmez; bu aşama dosya yükleme veya barındırma sağlamaz.
- Bilinmeyen tür ve geçersiz alanlar 422 ile Türkçe form hatası döndürür;
  girilen değerler korunur. Olmayan kitap 404 döndürür.
- Aktif ödünç sayısından düşük stok SQLite tarafından reddedilir.
- Ödünç veya rezervasyon geçmişi olan kitap silinemez (409) ve türü değiştirilemez.
  Bu kural tamamlanmış veya iptal edilmiş tarihsel kayıtları da kapsar.
- Başarısız kayıtlar işlem günlüğü veya kısmi değişiklik bırakmaz. Başarılı ekleme,
  düzenleme ve silme `activity_logs` tablosuna aynı işlem içinde yazılır.

HTML/JavaScript doğrulaması yalnızca kullanım kolaylığı içindir. Sunucu kontrolleri
bağımsızdır; JavaScript kapalıysa iki tür alanından kullanılmayanı boş bırakın.
Kullanılabilir adet önceki `book_inventory` görünümünden hesaplanmaya devam eder.
Şema değişikliği veya mevcut kayıtların silinmesi gerekmez.

## Dosya görevleri

`models/book.py`: soyut/somut ürünler. `patterns/factory_method.py`: soyut/somut oluşturucular.
`services/book_service.py`: alan doğrulama, arama ve işlemsel SQL.
`routes/books.py`: Blueprint, rol denetimi ve HTTP yanıtları.
`templates/books.html`, `book_form.html`, `book_delete.html`: Türkçe görünümler.
`static/js/books.js`: tür seçimine göre alanları açma/kapama.

## Elle test

1. Yönetici hesabıyla türü Fiziksel Kitap olan, ISBN'siz ve rafı B-12 olan bir kitap ekleyin.
2. Kitap adıyla arayın, yazarını değiştirin ve kaydın güncellendiğini kontrol edin.
3. Elektronik Kitap türünde `https://example.invalid/demo.pdf` örnek adresiyle ikinci
   gösterim kaydı oluşturun. Bu adres gerçek dosya değildir.
4. Bir kayda yanlış ISBN girin: Türkçe hata görünmeli, kayıt değişmemelidir.
5. Yeni ve geçmişsiz kitabı onay sayfasından silin.
6. Önceki gösterim kitaplarından birini silmeyi deneyin: tarihçe nedeniyle reddedilmelidir.
7. Üye hesabıyla kataloğu açın; ekleme/düzenleme/silme URL adreslerini deneyin: 403 olmalıdır.

Kalıp açıklaması ve UML: [Tasarım kalıpları](TASARIM_KALIPLARI.md).
