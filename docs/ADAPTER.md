# Adapter — Harici katalog entegrasyonu

Üyeler ve yöneticiler **Kitap Keşfet** ekranında başlık, yazar ve ISBN ile arama yapabilir. Alanlar birlikte uygulanır. Google Books varsayılan kaynaktır. Open Library kaynak listesinden seçilebilir. Her sayfada en fazla 12, bir aramada en fazla 100 sayfa gösterilir.

Seçilen sağlayıcı kota, bağlantı veya yanıt hatası verirse aynı sorgu diğer sağlayıcının ilk sayfasında denenir. Arayüz hatayı ve her kaydın kaynağını gösterir. İki sağlayıcı da erişilemiyorsa iki hata da gösterilir. Başarılı boş arama boş sonuç olarak gösterilir. Ayrıntı istekleri seçilen eserin sağlayıcısına bağlıdır.

## Kayıt akışı

**Ayrıntıları gör** dış kaydın bibliyografik bilgilerini ve açıklamasını açar. Google Books tam tarih sağladığında tarih, yıl sağladığında yıl gösterilir. Open Library arama verisi yayın yılı sağlar. **İçe aktar ve düzenle** ile yönetici kaydı taslağa çevirir. Başlık, yazar, ISBN, kapak adresi, açıklama, yayınevi, yıl ve dil bilgileri mevcut olduklarında doldurulur. Open Library açıklaması eser kaydından alınır. Baskı bilgileri sağlayıcının döndürdüğü alanlara bağlıdır. Kaydetme mevcut Factory Method yolundan geçer ve ISBN-10/ISBN-13 tekrar denetimini kullanır.

Kapak URL’si katalogda saklanır ve tarayıcı tarafından yüklenir. İzinli alan adları Google Books ve Open Library kapak hizmetiyle sınırlıdır. Açıklama metin olarak saklanır ve HTML kaçışından geçirilir. Arama ve ayrıntı için oturum ve CSRF denetimi uygulanır. İçe aktarma ve kaydetme yönetici yetkisi gerektirir.

## Sınıflar

| Sınıf | Sorumluluk |
| --- | --- |
| BookDataProvider | Ortak sayfalı arama ve kayıt ayrıntısı sözleşmesi |
| GoogleBooksAPI, OpenLibraryAPI | HTTP istekleri, zaman aşımı ve sağlayıcı hataları |
| GoogleBooksAdapter, OpenLibraryAdapter | Sağlayıcı JSON verisini BookImportData ve BookSearchPage biçimine dönüştürme |
| CatalogCache | Sağlayıcı başına sınırlı sonuç önbelleği ve kota bekleme süresi |
| BookImportData | Mevcut kitap formuna aktarılabilen geçici katalog kaydı |

[Adapter UML diyagramı](diagrams/adapter.mmd)

## Yapılandırma ve kota

Google Cloud projesinde Books API’yi etkinleştirin ve anahtarı proje kökündeki `.env` dosyasına ekleyin.

```dotenv
GOOGLE_BOOKS_API_KEY=buraya_kendi_anahtarinizi_yazin
```

Anahtar uygulama sunucusunda kalır. Google’ın uyguladığı kota Cloud Console’da yönetilir. Bütünleştirme, tekrarlanan arama ve ayrıntı isteklerini azaltır. Başarılı yanıtlar her sağlayıcı için 10 dakika ve en fazla 256 sonuç sayfası veya ayrıntı kaydı boyunca süreç belleğinde tutulur. Kota yanıtından sonra yeni istekler en az 60 saniye bekletilir. Daha uzun sayısal `Retry-After` değeri varsa kullanılır. Açık oturumlar aynı Flask sürecinde önbelleği paylaşır. Birden fazla sunucu süreci kendi önbelleğini kullanır. Open Library anahtar gerektirmez.

## Veritabanı geçişi

Sunucuyu durdurup SQLite yedeği aldıktan sonra `init-db` ve `check-db` çalıştırın. Geçiş mevcut kitaplara boş bırakılabilen `cover_url`, `description`, `publisher`, `publication_year` ve `language` sütunlarını ekler. Kitap kimlikleri, ödünçler ve rezervasyon ilişkileri korunur. [Kurulum ve geçiş adımları](KURULUM.md).

[Google Books API](https://developers.google.com/books/docs/v1/using) · [Open Library Search API](https://openlibrary.org/dev/docs/api/search) · [Open Library Covers API](https://openlibrary.org/dev/docs/api/covers)

## Sağlayıcı sınırları

Google Books bir arama isteğinde en fazla 40 sonuç destekler. Uygulama 12 sonuç ister. Google Cloud kotası proje ve yapılandırmaya bağlıdır. Canlı geliştirme denemesi kota yanıtı verdi.

Open Library varsayılan olarak saniyede bir isteğe izin verir. Hizmetin tanımlanmış istemciler için açıkladığı sınır saniyede üç istektir. Tanımlama için hizmet, User-Agent başlığında uygulama adı ve iletişim bilgisi ister. Open Library araması öncelikle eserleri listeler. ISBN, kapak, açıklama veya baskı bilgisi her eserde bulunmayabilir. [Open Library kullanım kuralları ve hız sınırları](https://openlibrary.org/developers/api#rate-limits)
