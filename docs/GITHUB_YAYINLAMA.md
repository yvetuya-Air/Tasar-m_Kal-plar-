# GitHub yayınlama

20 Kasım 2026 denetiminde yerel main ve develop dalları vardı. Uzak depo tanımlı değildi. Bu teslim için GitHub yayını doğrulanmadı.

GitHub hesabınızda **Kutuphane-Yonetim-Sistemi-Proje-Gelisimi-1** adlı boş bir depo oluşturun. GitHub üzerinde README, lisans veya .gitignore oluşturma seçeneklerini boş bırakın. Erişim ayarını öğretim elemanının depoyu açabileceği şekilde belirleyin.

Teslim ZIP’ini yeni bir klasöre açın. PowerShell’de app.py bulunan klasöre geçin. Aşağıdaki komutlar teslimin bağımsız main dalını oluşturur ve mevcut V1/V2 çalışma klasörüne dokunmaz.

```powershell
git init -b main
git add --all
git status --short
git diff --cached --stat
git ls-files -ci --exclude-standard
git commit -m "EBLG443 Proje Gelişimi 1 teslimi"
$repoUrl = Read-Host 'GitHub Code bölümündeki HTTPS depo adresi'
git remote add origin $repoUrl
git push -u origin main
git ls-remote --heads origin main
git rev-parse HEAD
```

Git kimliği tanımlı değilse commit öncesi bu depoda git config user.name ve git config user.email ayarlarını doldurun. Commit öncesi git ls-files -ci --exclude-standard çıktısının boş olduğunu ve hazırlanan dosyaların yalnız teslim içeriği olduğunu kontrol edin. Gerçek .env, API anahtarı, SQLite dosyası, kişisel veri, sanal ortam ve önbellekleri Git’e eklemeyin.

Son iki komuttaki commit kimlikleri eşleşince GitHub’da main dalını açın. README görsellerini ve kurulum, test, kalıp bağlantılarını kontrol edin. Öğretim elemanıyla doğrulanmış depo bağlantısını paylaşın.
