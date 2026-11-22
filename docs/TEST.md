# Testler

Testler, kitap işlemlerini ve dört tasarım kalıbının beklenen davranışlarını kontrol etmek için hazırlanmıştır.

## Testleri çalıştırma

Projenin ana klasöründe, kurulum tamamlandıktan sonra:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Yalnızca tasarım kalıpları ve entegrasyon testleri için:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_factory.py tests/test_adapter.py tests/test_strategy.py tests/test_observer.py tests/test_integration.py
```

## Kontrol edilen işlemler

| Konu | Testin amacı | İlgili dosya |
| --- | --- | --- |
| Factory Method | Farklı kitap türlerini doğru sınıflarla oluşturmak | `tests/test_factory.py` |
| Adapter | Google Books ve Open Library verilerini ortak biçime dönüştürmek | `tests/test_adapter.py` |
| Strategy | Üyelik türüne göre gecikme cezasını hesaplamak | `tests/test_strategy.py` |
| Observer | İade sonrası rezervasyon sahibine bildirim oluşturmak | `tests/test_observer.py` |
| Entegrasyon | Kitap, üye, ödünç, rezervasyon ve iade akışını denetlemek | `tests/test_integration.py` |

## Örnek kontrol sonuçları

- **Strategy:** 5 günlük gecikmede öğrenci 10 TL, öğretmen 5 TL, normal üye 25 TL.
- **Adapter:** İki farklı kaynak JSON biçimi ortak kitap verisine dönüşür.
- **Observer:** Rezervasyonlu kitabın iadesi sonucunda ilgili üyeye bildirim kaydedilir.
- **Factory Method:** Fiziksel, elektronik ve sesli kitaplar ilgili oluşturucularla hazırlanır.

Önceki proje test raporunda **410 başarılı, 0 başarısız** pytest sonucu kaydedilmiştir (20 Kasım 2026). Bu sayı önceki çalışma ortamına aittir; teslim öncesi kendi bilgisayarınızda yukarıdaki komutu yeniden çalıştırıp sonucu doğrulayın.

**Test sınırları:** Önceki doğrulamada canlı Google Books ve Open Library bağlantıları başarılı olmadı; Adapter testlerinde örnek veya taklit HTTP yanıtları kullanıldı. Yeni sanal ortamda paket indirme de o doğrulamada tamamlanamadı. Bu nedenle canlı API erişimi ayrıca test edilmelidir.
