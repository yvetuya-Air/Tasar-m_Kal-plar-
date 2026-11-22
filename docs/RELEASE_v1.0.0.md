# v1.0.0 Sürüm Notları — Taslak

**Proje:** Kütüphane Yönetim Sistemi

**Ders:** EBLG443 — Tasarım Kalıpları

**Durum:** Taslak; Git etiketi veya GitHub Release yayımlanmadı.

## İçerik

- Flask/SQLite üzerinde Yönetici ve Üye kimlik doğrulaması ve sunucu yetkilendirmesi.
- Fiziksel/elektronik kitap ve üye yönetimi, arama, ISBN tekrarı denetimi.
- İşlemsel ödünç/iade, stok ve FIFO rezervasyon tutarlılığı.
- Üye türüne göre kesin ceza ve kişisel kullanılabilirlik bildirimleri.
- Gerçek panel, responsive açık/koyu arayüz ve dört kalıp eğitim sayfası.
- Gerçek Factory Method, Adapter, Strategy ve Observer uygulamaları.
- Türkçe akademik belgeler, UML/ER ve gerçek ekran görüntüleri.

## Doğrulama ve bilinen sınırlar

Son gerçek sonuçlar [12. aşama denetiminde](audit/release-stage12.json), [JUnit XML'de](audit/pytest-stage12.xml) ve [tarayıcı kaydında](screenshots/stage12/ui-test-result.json) bulunur. Taslak sürüm numarası testlerin yerine geçmez.

Canlı Google Books anahtarsız denemesi kota engeline takılmıştır; API entegrasyonu taklit dış yanıtlarla doğrulanır. Fiziksel telefon, insan ekran okuyucu ve Firefox/Safari denemeleri yapılmamıştır. Üretim yayını, ödeme, e-posta/SMS ve parola sıfırlama kapsam dışıdır.

Kararlı etiket öncesi ilk commit ve kabul ölçütleri tamamlanmalıdır. [Yayın komutları ve durum](GITHUB_YAYINLAMA.md).
