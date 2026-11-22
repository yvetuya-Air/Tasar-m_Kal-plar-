# Tasarım Kalıpları

Kütüphane Yönetim Sistemi'nde dört GoF tasarım kalıbı kullanılmıştır. Her kalıp, uygulamadaki belirli bir sorunu çözmek için seçilmiştir.

## 1. Factory Method — Yaratımsal

**Amaç:** Farklı kitap türlerini ortak bir oluşturma süreciyle hazırlamak.

Kullanıcı kitap eklerken fiziksel, elektronik veya sesli kitap türü seçer. `BookCreator` ortak oluşturma adımlarını tanımlar; `PhysicalBookCreator`, `EBookCreator` ve `AudioBookCreator` uygun nesneyi üretir.

- Kaynak kod: [patterns/factory_method.py](../patterns/factory_method.py)
- UML: [factory_method.mmd](diagrams/factory_method.mmd)
- Örnek: Yönetici, raf konumu olan fiziksel kitap veya dosya bağlantısı olan e-kitap ekler.

**Avantaj:** Kitap türlerine ait oluşturma kuralları ayrı sınıflarda bulunur.

## 2. Adapter — Yapısal

**Amaç:** Farklı kitap kataloglarından gelen bilgileri ortak bir biçimde kullanmak.

Google Books ve Open Library farklı JSON alanları döndürür. `GoogleBooksAdapter` ve `OpenLibraryAdapter` bu bilgileri `BookImportData` biçimine dönüştürür. Böylece uygulama iki sağlayıcıyı benzer şekilde kullanabilir.

- Kaynak kod: [Google Books](../patterns/adapter.py), [Open Library](../patterns/open_library_adapter.py)
- UML: [adapter.mmd](diagrams/adapter.mmd)
- Örnek: Bir kaynaktaki `volumeInfo.title`, diğerindeki `title` alanı uygulamada aynı `title` alanına dönüşür.

**Avantaj:** Dış servislere ait JSON ayrıntıları uygulamanın diğer bölümlerine yayılmaz.

## 3. Strategy — Davranışsal

**Amaç:** Gecikme ücretini üyelik türüne göre hesaplamak.

`PenaltyCalculator`, bir `PenaltyStrategy` kullanır. `StudentPenalty`, `TeacherPenalty` ve `StandardPenalty` farklı tarifeler uygular. `set_strategy()` ile aynı hesaplayıcıda strateji değiştirilebilir.

| Üye türü | Günlük ücret | 5 gün |
| --- | ---: | ---: |
| Öğrenci | 2 TL | 10 TL |
| Öğretmen | 1 TL | 5 TL |
| Normal üye | 5 TL | 25 TL |

- Kaynak kod: [patterns/strategy.py](../patterns/strategy.py)
- UML: [strategy.mmd](diagrams/strategy.mmd)

**Avantaj:** Ceza hesaplama kuralları ayrı sınıflarda tutulur.

## 4. Observer — Davranışsal

**Amaç:** Rezervasyon yapan üyeye kitap uygun olduğunda bildirim göndermek.

`BookAvailabilitySubject` gözlemcileri yönetir. Bir kitap iade edilince `notify()` çalışır; `MemberObserver`, bildirim hizmeti üzerinden ilgili üyeye mesaj kaydeder.

- Kaynak kod: [patterns/observer.py](../patterns/observer.py)
- UML: [observer.mmd](diagrams/observer.mmd)
- Örnek: Rezervasyon bekleyen üye, kitap iade edildiğinde otomatik bildirim alır.

**Avantaj:** İade işlemi ile üye bildirim mantığı doğrudan birbirine bağlanmaz.

## Uygulamada gösterim

Yönetici hesabıyla **Tasarım Kalıpları** sayfası açılır. Her kalıbın UML diyagramı, kod örneği ve çalışma senaryosu gösterilir. Adapter, Strategy ve Observer örnekleri ana kütüphane verisini değiştirmeden denenebilir.

Sunum adımları için [DEMO.md](DEMO.md) dosyasına bakın.
