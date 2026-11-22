# Teknik Belgeleme ve Doğrulama Kaydı

**Ders:** EBLG443 — Tasarım Kalıpları

**Proje adı:** Kütüphane Yönetim Sistemi

**Aşama:** 11 — Teknik Dokümantasyon

**Tarih:** 18 Kasım 2026, Türkiye

## 1. Kapsam ve yöntem

Uygulama fabrikası, yapılandırma, güvenlik modülü, SQL şeması, tüm alan modelleri, dört kalıp, HTTP rotaları ve hizmetler kaynak üzerinden incelenmiştir. Jinja şablonları, CSS/JavaScript davranışları, yardımcı betikler, test kaynakları ve saklanan JUnit/tarayıcı kanıtları birlikte değerlendirilmiştir. Veri akışı ve izinler mevcut koda göre açıklanır; geliştirilmemiş özellikler başarı gibi gösterilmez.

[Kaynak inceleme kaydı](audit/source-review-stage11.json) dosya özetlerini, Python sınıf/işlev envanterini, Jinja ayrıştırmasını ve canlı salt okunur HTTP sonuçlarını tutar. Uygulama dosyaları yalıtılmış kurulum kopyasıyla karşılaştırılmıştır. Bu kayıt insanın her olası davranışı denediği veya satır kapsamı ölçüldüğü anlamına gelmez.

README, kurulum, mimari, kalıp incelemesi, test raporu ve kullanım kılavuzu bütünleşik bir belge dizisi olarak hazırlanmıştır. Önceki aşama belgeleri ayrıntı/tarihçe olarak korunur; güncel teknik temel bu altı belgedir. Uygulamanın işlevsel kaynak kodu değiştirilmemiştir. Eklenen Python araçları yalnız belge üretimi ve doğrulaması içindir.

## 2. Kaynakla eşleşen diyagram ve kod

`scripts/sync_doc_sources.py`, Python AST'sinden gerçek sınıf/metotları ve kalıtımı çıkarır. Kullanım ilişkileri kaynakta gözlenen alan/çağrılara göre tanımlıdır; bu bir otomatik çalışma zamanı izleme aracı değildir. Kod örnekleri gerçek sınıf/metot kaynak satırlarından alınır. ER diyagramı schema.sql'nin geçici bellek veritabanına uygulanması ve SQLite PRAGMA verileriyle oluşur. Rota tablosu Flask url_map üzerinden alınır. Soyut sınıflar ayrıca işaretlenir; ORM tablosu gibi sunulmaz.

```powershell
.\.venv\Scripts\python.exe scripts/sync_doc_sources.py
.\.venv\Scripts\python.exe scripts/sync_doc_sources.py --check
```

İkinci komut dosya değiştirmez; kaynakla belge bloğu uyuşmuyorsa başarısız çıkar. [Dört UML ve ER kaynakları](diagrams) GitHub uyumlu Mermaid biçimindedir. Uygulamadaki SVG'ler değiştirilmemiştir.

Beş UML/ER kaynağı ile mimarinin iki akış çizimi yerel Mermaid ve Chromium içinde gerçek SVG'ye dönüştürülerek doğrulanır. [Çizim sonuçları](audit/diagrams-stage11.json) saklanır. İlk denetimde araç yalnız SVG text düğümlerini saydığı için HTML etiketlerini kaçırmıştır; araç foreignObject etiketlerini de sayacak biçimde düzeltilmiştir. Ardından işlem sırası diyagramındaki noktalı virgül Mermaid ayrıştırma hatası üretmiş, açıklama metni düzeltilmiştir. [İlk araç çıktısı](audit/diagrams-stage11-initial-check.json) ve [gerçek sözdizimi hatası](audit/diagrams-stage11-sequence-failure.json) silinmemiştir.

İsteğe bağlı yeniden çizim kontrolü Windows, Node.js ve yerel Chrome/Edge gerektirir:

```powershell
npm.cmd install --prefix .ui-tools --no-save --package-lock=false playwright
npm.cmd install --prefix .test-tmp/docs11-diagrams --no-save --package-lock=false mermaid
node scripts/check_doc_diagrams.cjs
```

Bu paketler uygulamanın çalışma bağımlılığı değildir; yerel doğrulama klasörleri Git'e alınmaz.

## 3. Ekran görüntülerinin kökeni

[Tarayıcı sonuç JSON'u](screenshots/ui-test-result.json) altı PNG'nin adını ve çekim çalışmasını kayıtlı tutar. Bitiş zamanı 17 Kasım 2026 21:12 UTC, Türkiye'de **18 Kasım 2026 00:12**'dir. Bunlar gerçek Flask sayfalarının ayrı gösterim veritabanıyla alınmış görüntüleridir; yapay arayüz çizimi değildir. README gerçek dosyalara göreli bağlantı verir. Tasarım kalıpları görüntüsü sayfanın Factory Method bölümünü kapsar; bütün dört bölümü tek görüntüde gösterdiği iddia edilmez.

Görüntülerde demo hesap adları ve example.invalid gösterim kayıtları vardır; gerçek üye bilgisi veya anahtar yoktur. Bu aşamada açık panel ve eğitim bölümü tekrar görsel olarak incelenmiştir. Önceki 100 tarayıcı doğrulaması yeniden koşulmuş gibi sunulmamıştır.

## 4. Komut doğrulaması ve sınırlar

| Denetim | Yöntem ve gerçek sonuç kaynağı |
| --- | --- |
| Python ve Git varlığı | py --version: 3.13.2; git --version: 2.52.0.windows.1 |
| Yeni sanal ortam | py -m venv ile .test-tmp altında ayrı ortam oluşturuldu |
| Bağımlılık kurulumu | İlk ağ kısıtlı deneme WinError 10013 ile engellendi; izinli tekrar yeni ortamda requirements.txt paketlerini başarıyla kurdu |
| CLI ve demo sıralaması | Temiz kaynak kopyası ve ayrı SQLite içinde init-db → seed-demo → demo-accounts → check-db; tekrar çalıştırma ve giriş/sayfa denetimi: [setup-stage11.json](audit/setup-stage11.json) |
| Bağımlılık uyumu | Yeni ortamda pip check; sonucu aynı setup kaydında |
| Yeni ortamda başlangıç testleri | test_app.py: 3 başarılı, 1,61 saniye; [JUnit kanıtı](audit/pytest-stage11-smoke.xml) |
| Canlı yerel sunucu | Mevcut sunucuda /giris ve favicon için salt okunur HTTP kontrolü; ana veriye kayıt eklenmez |
| Kaynak/belge eşleşmesi | sync_doc_sources.py --check; güncel bloklar ve diyagramlar |
| Markdown bağlantıları | check_docs.py yerel hedef/başlıkları; --online seçeneği harici belge bağlantılarını denetler: [bağlantı raporu](audit/documentation-links-stage11.json) |

Windows kurulum sırası temiz kopyada sınanır; ana .env veya veritabanı değiştirilmez. Python/Git grafik kurucuları yeniden çalıştırılmamıştır; gerçek uzak GitHub URL'si olmadığından clone yapılmamıştır. Linux/macOS komutları belgelenmiş yol karşılıklarıdır, bu makinelerde denenmemiştir. run --help seçenekleri sınanır; geliştirme sunucusunun internete açık üretim kurulumu doğrulanmış sayılmaz.

Son bağlantı denetimi 16 Markdown dosyasındaki tüm bulunan bağlantılarda yerel hedef/başlık hatası olmadığını ve altı harici bağlantının HTTP 200 döndürdüğünü kaydetmiştir. Gizli değer eşleşmesi taraması Markdown yanında yayınlanabilir JSON/XML/Mermaid/SVG metinlerini de kapsar; sonuçta eşleşme bulunmamıştır. Tam bağlantı sayısı makine raporundadır.

## 5. Test sonuçlarının doğruluğu

374 başarılı pytest vakası ve 100 tarayıcı doğrulaması önceki gerçek yürütmenin ham dosyalarına bağlıdır. Tarih, süre ve başarısız/atlanan sayılar değiştirilmez. [TEST.md](TEST.md) test amaçlarını, ortamı, türleri, tam senaryoyu ve her varyantın beklenen/gerçek sonucunu içerir. [AUDIT_TEST.md](AUDIT_TEST.md) ilk başarısız tarayıcı çıktısını ve düzeltmeleri korur.

Canlı Google Books kota engeli, fiziksel telefon/ekran okuyucu/diğer motor testlerinin yürütülmemesi açıkça belirtilmiştir. Belgeleme yardımcılarının doğrulaması işlevsel test toplamına eklenmez. Satır kapsam yüzdesi veya güvenlik sertifikası iddia edilmez.

## 6. GitHub için hazırlık ve hassas veriler

Göreli dosya bağlantıları, UTF-8 Türkçe metin, alt metinli gerçek PNG'ler ve Mermaid kullanılmıştır. Uydurma uzak depo URL'si, kişi/öğrenci bilgisi veya lisans eklenmemiştir. Yalnız kaynakta bulunan açık yerel demo hesapları belgelenmiştir. `.env`, `instance`, SQLite dosyaları/yedekleri, `.venv`, `.ui-tools` ve `.test-tmp` Git dışında tutulur. Gerçek anahtar/parolalar belgeye kopyalanmaz; bağlantı denetimi yerel gizli değerlerle eşleşmeyi değeri yazdırmadan kontrol eder.

Bu kontrol kapsamlı bir gizli veri tarama ürünü değildir; belgeler, metin kanıtları ve gösterilen örnekler için doğrulamadır. Bu belge 11. aşamanın kaydını korur. Kullanıcının sonraki onayıyla yapılan 12. aşama yerel Git/yayın hazırlığı [son teslim raporundadır](GITHUB_YAYINLAMA.md); uzak yayın yapılmış sayılmaz.

[README](../README.md) · [Kurulum](KURULUM.md) · [Mimari](MIMARI.md) · [Kalıplar](TASARIM_KALIPLARI.md) · [Kullanım](KULLANIM_KILAVUZU.md) · [Test](TEST.md)
