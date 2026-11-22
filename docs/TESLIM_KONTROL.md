# Proje Gelişimi 1 son kontrol raporu

**EBLG443 — Tasarım Kalıpları · Hedef teslim 23 Kasım 2026**

## Sürüm ve kapsam

Teslim, yerel develop dalındaki f81a939 temel alınarak 20 Kasım 2026 tarihinde hazırlandı. V2 geliştirme tabanında mevcut özellikler korundu. Değişiklikler Türkçe Tasarım Kalıpları ekranına, kaynakla eşlenen UML’ye ve akademik teslim belgelerine odaklandı. Çalışma öncesi main ve develop geçmişinin tam Git yedeği alınıp doğrulandı.

| Kontrol | Sonuç |
| --- | --- |
| Yönetici ve üye doğrulaması | Giriş, çıkış, rol izinleri ve kayıt sahipliği pytest ile doğrulandı. |
| Temel kütüphane işlemleri | Kitap ve üye yönetimi, ödünç, iade, rezervasyon ve uygulama içi bildirim çalıştırıldı. |
| Dört kalıp | Fabrika ürünü, dış veri uyarlaması, ceza stratejisi ve Observer iade bildirimi gerçek kodla doğrulandı. |
| SQLite | Yeni veritabanı kurulumu, tekrarlanabilir demo komutları, bütünlük, yabancı anahtarlar ve mevcut veri geçişi test edildi. |
| Otomatik testler | 410 ge?ti, 0 ba?ar?s?z, 0 hata, 0 atland? (172,51 saniye). |
| Chromium | 137 kontrol başarılı, beklenmeyen JavaScript hatası yok. Ayrı eğitim gösteriminde dört sonuç görüldü. |
| UML ve belgeler | Dört sınıf diyagramı ile üç mimari çizim Mermaid’de oluşturuldu. Kaynak eşleme kontrolü ve depo içi bağlantı kontrolü tamamlandı. |
| ZIP | Dosya bütünlüğü, zorunlu teslim içeriği, hassas dosya ve değer kontrolü, arşivden çıkartılan kaynakta demo kurulumu ve giriş doğrulandı. |
| GitHub | Yerel depo hazır. Uzak depo tanımlı değildi ve yayın doğrulanmadı. |

## Sınırlar

- Canlı Google Books ve Open Library aramasında bağlantı kurulamadı. Adapter dönüşümü ve kayıt akışı taklit cevaplarla sınandı.
- Temiz kaynak kopyası kurulu Python bağımlılıkları ile doğrulandı. Yeni sanal ortamda paket kaynağından Flask indirilemedi.
- Linux/macOS, fiziksel telefon ve uzak GitHub klonu denenmedi. Gösterim için Türkçe senaryo ve gerçek ekran görüntüleri hazırlandı.

[Kurulum](KURULUM.md) · [Test raporu](TEST.md) · [Tasarım kalıpları](TASARIM_KALIPLARI.md) · [Sunum senaryosu](DEMO.md) · [GitHub yayınlama](GITHUB_YAYINLAMA.md)
