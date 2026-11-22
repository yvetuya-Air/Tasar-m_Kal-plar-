# Kısa Sunum Senaryosu

Sunumdan önce uygulamayı [kurulum kılavuzuna](KURULUM.md) göre başlatın.

1. **Giriş:** Yönetici hesabıyla oturum açın ve ana paneli gösterin.
2. **Factory Method:** **Kitaplar → Kitap ekle** bölümünde fiziksel kitap oluşturun. Raf konumunun kullanıldığını gösterin. Ardından elektronik kitap türündeki dosya bağlantısı alanını gösterin.
3. **Adapter:** **Tasarım Kalıpları → Adapter** bölümünde Google Books ve Open Library örneklerini çalıştırıp sonuçların aynı kitap alanlarına dönüştüğünü gösterin. İnternet uygunsa **Kitap Keşfet** aramasını da deneyin.
4. **Strategy:** Beş günlük gecikmede öğrenci, öğretmen ve normal üye için sırasıyla **10 TL, 5 TL, 25 TL** sonucunu gösterin.
5. **Observer:** **Rezervasyon, iade ve bildirimi dene** düğmesini kullanın. Rezervasyon, iade ve otomatik bildirim sırasını açıklayın.
6. **Kod ve test:** `patterns/` klasöründeki dört uygulamayı ve terminalden `python -m pytest -q` komutuyla testlerin çalıştırılabildiğini gösterin.

Observer gösterimi ayrı bellek veritabanında çalışır; gerçek kütüphane kayıtlarını değiştirmez. Canlı katalog yanıtları internet bağlantısı ve servis erişimine bağlıdır.
