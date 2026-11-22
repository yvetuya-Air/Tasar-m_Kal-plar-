# Proje Gelişimi 1 sunum senaryosu

[Kurulum kılavuzundaki](KURULUM.md) komutlarla boş bir yerel demo veritabanı hazırlayın. Yönetici işlemleri için ilk tarayıcıyı, demo_uye / DemoUye!2026 oturumu için ayrı bir tarayıcı profili veya gizli pencere kullanın.

| Adım | Ekran ve işlem | Gösterilecek sonuç |
| --- | --- | --- |
| 1 | **Giriş Yap** ekranında demo_yonetici / DemoYonetici!2026 ile oturum açın. | Yönetici paneli açılır. |
| 2 | **Genel Bakış** ekranını açın. | Örnek kitap, üye ve işlem sayıları görünür. |
| 3 | **Kitaplar** sekmesine geçin. | Demo Fiziksel Kitap ve Demo E-Kitap listelenir. |
| 4 | **Kitap Ekle** ekranında Fiziksel Kitap türüyle Sunum Kitabı oluşturun. Yazar olarak Örnek Yazar, raf olarak S-01, adet olarak 1 girin. | Factory Method, PhysicalBookCreator ile PhysicalBook üretir ve kayıt katalogda görünür. |
| 5 | **Kitap Keşfet** ekranında 9780306406157 ISBN ile arayın. Sonuç gelirse ayrıntıda **İçe aktar** düğmesiyle form alanlarını inceleyin. | Adapter dış alanları kitap taslağına dönüştürür. Bağlantı veya kota sorunu varsa Tasarım Kalıpları → Adapter gösterimi üzerinden örnek kaynak JSON’u ve dönüştürülmüş veriyi karşılaştırın. |
| 6 | **Üyeler** ekranını açın. | Öğrenci, öğretmen ve normal üye örnekleri ile hesap durumları görünür. |
| 7 | **Ödünç Ver** ekranında Sunum Kitabı’nı Demo Normal Üye’ye verin. **Rezervasyonlar** ekranında aynı kitap için Demo Öğrenci adına rezervasyon açın. | Tek kopya ödünçteyken rezervasyon bekler. |
| 8 | **Ödünç İşlemleri** listesindeki Demo Fiziksel Kitap’ın gecikmiş öğrenci ödüncünü açın. Ceza önizlemesini gösterip iadeyi onaylayın. | Aynı gün hazırlanan demo verisinde 6 gün × 2 TL = 12 TL. Kalıp sayfasında 5 gün için 10, 5 ve 25 TL karşılaştırılır. |
| 9 | Yönetici olarak **Rezervasyonlar** listesini açın ve Sunum Kitabı’nı iade edin. Demo Öğrenci’ye bağlı demo_uye oturumunda **Bildirimler** ekranını açın. | Observer iade ile oluşan kullanılabilirlik bildirimini kaydeder. Başlangıçtaki etiketli örnek bildirimden farklı olarak yeni kayıt iadeden doğar. |
| 10 | **Tasarım Kalıpları** ekranında dört UML’yi, kod örneklerini ve çalışma senaryolarını açın. Observer için **Rezervasyon, iade ve bildirimi dene** düğmesini kullanın. | Her kalıp gerçek sınıflarla çalışır. Observer gösterimi bağımsız bellek veritabanı kullanır. |
| 11 | Terminalde pytest çalıştırın ve [test raporunu](TEST.md) açın. | Gerçek sonuçlar ve tekrar komutları görünür. |
| 12 | GitHub deposu yayınlandıysa README, kurulum, test ve kalıp belgelerini açın. Yayın öncesi yerel teslimde aynı belgeleri ZIP’ten gösterin. | Öğretim elemanı kurulumu ve dört kalıbı tek yerden inceleyebilir. |

Aynı veritabanında ikinci sunum yaparken oluşturulan kitap için yeni bir ad kullanın. İlk günkü gecikme ve rezervasyon durumlarını tekrar etmek için ZIP’i yeni bir klasöre açıp orada boş bir demo veritabanı hazırlayın.
