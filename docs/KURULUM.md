# Kurulum Kılavuzu

Bu belge, Kütüphane Yönetim Sistemi'nin Windows üzerinde yerel olarak çalıştırılmasını açıklar.

## Gereksinimler

- Python 3.11 veya üzeri
- İnternet bağlantısı (ilk paket kurulumu için)
- Güncel bir web tarayıcısı

## Kurulum

ZIP dosyasını açın veya GitHub deposunu indirin. Terminali `app.py` ve `requirements.txt` dosyalarının bulunduğu ana klasörde açın.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` dosyasındaki `SECRET_KEY` değerini kendi bilgisayarınızda oluşturun:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Üretilen değeri `.env` içindeki `SECRET_KEY=` satırına yazın. Bu dosyayı GitHub'a yüklemeyin.

## İlk çalıştırma

Yalnızca **yeni ve boş bir gösterim kurulumu** için:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app init-db
.\.venv\Scripts\python.exe -m flask --app app:create_app seed-demo
.\.venv\Scripts\python.exe -m flask --app app:create_app demo-accounts
.\.venv\Scripts\python.exe -m flask --app app:create_app check-db
```

Daha önce kullanılan bir veritabanınız varsa `seed-demo` komutunu yeniden çalıştırmayın. Mevcut verileri silmeyin.

## Uygulamayı açma

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app run
```

Tarayıcıda [http://127.0.0.1:5000/giris](http://127.0.0.1:5000/giris) adresini açın. Sunucu çalışırken terminal açık kalmalıdır. Durdurmak için `Ctrl + C` kullanın.

Yalnızca yerel gösterim hesabı:

| Rol | Kullanıcı adı | Parola |
| --- | --- | --- |
| Yönetici | `demo_yonetici` | `DemoYonetici!2026` |
| Üye | `demo_uye` | `DemoUye!2026` |

Bu hesaplar gerçek kullanıcı verileri için kullanılmamalıdır. Flask'ın geliştirme sunucusu yerel test içindir.

## Sorun yaşanırsa

- `requirements.txt` bulunamıyorsa terminalin doğru klasörde olduğunu kontrol edin: `Test-Path .\requirements.txt`.
- `python.exe` bulunamıyorsa `.venv` klasörünün oluşturulduğunu kontrol edin.
- Tarayıcıda bağlantı reddediliyorsa Flask sunucusunu başlatıp terminali açık bırakın.
- Paket kurulumu başarısızsa terminaldeki hata mesajını inceleyin.
