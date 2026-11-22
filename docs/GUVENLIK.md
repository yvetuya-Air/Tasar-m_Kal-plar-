# Güvenlik ve Sistem Yönetimi

Oturumlar imzalı çerez, parola özeti, kullanıcıya bağlı oturum sürümü ve CSRF doğrulaması kullanır. HTTPS kurulumunda sabit ve rastgele SECRET_KEY ile SESSION_COOKIE_SECURE=true ayarlayın. API anahtarı ve .env yerel sunucuda tutulur.

Giriş denemeleri 15 dakikalık pencerede hesap başına 8, istemci adresi başına 40 denemeyle sınırlıdır. Ham ağ adresi ve parola günlükte yer almaz. Proxy kullanılıyorsa yalnız güvenilen proxy üzerinden istemci adresinin uygulamaya iletilmesi sunucu yapılandırmasının sorumluluğudur.

## Parola sıfırlama

İşletici üyenin kimliğini doğruladıktan sonra şu komutu çalıştırır:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app issue-password-reset KULLANICI_ADI
```

Kodu doğrulanmış kişiye güvenli kanaldan iletin. Kullanıcı **Parolamı sıfırla** formuna girer. Kod 30 dakika geçerlidir, bir kez kullanılabilir ve başarıdan sonra eski oturumlar iptal edilir. Veritabanı kodun özetini saklar. E-posta gönderimi uygulamaya bağlı değildir.

## Dosyalar, yedek ve geri yükleme

Yüklenmiş dijital içerik SQLite içindedir. Yedek, kayıtları ve yüklenen dosyaları birlikte içerir. Yönetici ayarlardan yedeği indirebilir. Dosyayı erişim kontrollü ve şifreli depoda saklayın.

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app backup-db instance/yedek.sqlite3
.\.venv\Scripts\python.exe -m flask --app app:create_app restore-db instance/yedek.sqlite3
```

Geri yükleme için uygulamayı durdurun, aynı şemaya sahip güvenilir bir yedek seçin ve komutun onayını verin. İşlem bütünlük ile yabancı anahtarları denetler ve mevcut veritabanının önceki bir kopyasını otomatik olarak bırakır. Geri yüklemeden sonra tüm oturumlar ve kullanılmamış sıfırlama kodları iptal edilir. Geri yükleme prova ve testleri bağımsız veritabanlarında yapılmalıdır.
