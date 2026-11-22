// Yalnızca scripts/ui_preview.py ile açılan, bağımsız yerel deneme sunucusu.
const { chromium } = require('../.ui-tools/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const auditStage = Number(process.env.UI_TEST_STAGE || 10);
const output = path.resolve(__dirname, '..', process.env.UI_TEST_OUTPUT || 'docs/screenshots');
const reportPath = path.join(output, 'ui-test-result.json');

(async () => {
  const base = process.env.UI_TEST_URL || 'http://127.0.0.1:5001';
  assert.equal(new URL(base).hostname, '127.0.0.1');
  assert.equal(new URL(base).port, '5001', 'Bu test üretim veritabanında çalıştırılmaz.');
  assert.ok(Number.isInteger(auditStage) && auditStage > 0);
  assert.ok(output.startsWith(path.resolve(__dirname, '..') + path.sep));
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(reportPath, JSON.stringify({ auditStage,status:'running',checks:0,startedAt:new Date().toISOString() },null,2));
  const executablePath = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(fs.existsSync);
  assert.ok(executablePath, 'Yerel Chromium tarayıcısı bulunamadı.');
  const browser = await chromium.launch({ executablePath, headless: true });
  let checks = 0;
  const failures = [];
  const expectedHttp = [];
  function observe(target) {
    const allowed = (url,status) => (new URL(url).pathname === '/uyeler' && status === 403) || (new URL(url).pathname === '/giris' && status === 401);
    target.on('pageerror', error => failures.push(error.message));
    target.on('response', response => {
      if (response.status() < 400) return;
      if (allowed(response.url(),response.status())) expectedHttp.push({ path:new URL(response.url()).pathname,status:response.status() });
      else failures.push(`Beklenmeyen HTTP ${response.status()}: ${new URL(response.url()).pathname}`);
    });
    target.on('console', message => {
      if (message.type() !== 'error') return;
      const status = /status of (\d{3})/.exec(message.text());
      const url = message.location().url;
      if (status && url && allowed(url,Number(status[1]))) return;
      failures.push(message.text());
    });
  }
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, locale: 'tr-TR', timezoneId: 'Europe/Istanbul', colorScheme: 'light' });
  const page = await context.newPage();
  observe(page);
  async function visit(route) { const result = await page.goto(base + route); assert.equal(result.status(), 200, route); checks++; }
  async function noOverflow(label) { assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Yatay taşma: ${label}`); checks++; }
  try {
    await visit('/giris');
    await page.screenshot({ path: path.join(output, 'giris.png'), fullPage: true });
    await page.getByLabel('Kullanıcı adı', { exact: true }).fill('demo_yonetici');
    await page.getByLabel('Parola', { exact: true }).fill('wrong-password');
    await page.locator('.login-form button[type=submit]').click();
    assert.ok(await page.locator('.notice.error').isVisible()); checks++;
    await page.screenshot({ path:path.join(output,'giris-hatasi.png'),fullPage:true });
    await page.getByLabel('Parola', { exact: true }).fill('DemoYonetici!2026');
    await page.locator('.login-form button[type=submit]').click();
    await page.waitForURL('**/panel');
    await page.getByRole('button', { name: 'Kenar menüsünü daralt' }).click();
    assert.equal(await page.locator('html').getAttribute('data-sidebar'), 'collapsed'); checks++;
    await page.getByRole('button', { name: 'Kenar menüsünü genişlet' }).click();
    await page.locator('#global-query').fill('Demo');
    await page.locator('#global-query').press('Enter');
    await page.waitForURL('**/kitaplar?q=Demo'); checks++;
    await visit('/panel');
    assert.equal(await page.locator('[data-stat=members]').getAttribute('data-value'), '3'); checks++;
    await noOverflow('masaüstü panel');
    await page.screenshot({ path: path.join(output, 'dashboard-acik.png'), fullPage: true });
    await page.getByRole('button', { name: 'Koyu temaya geç' }).click();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark'); checks++;
    await page.reload();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark'); checks++;
    await page.screenshot({ path: path.join(output, 'dashboard-koyu.png'), fullPage: true });
    await visit('/ayarlar');
    await page.locator('[data-theme-choice=light]').click();
    await page.locator('[data-density-choice=compact]').click();
    assert.equal(await page.locator('html').getAttribute('data-density'), 'compact'); checks++;
    await page.locator('[data-density-choice=comfortable]').click();
    const routes = ['/kitaplar','/kitaplar/ekle','/kitaplar/google','/kitap-kesfet','/uyeler','/kategoriler','/uye-tani','/odunc','/odunc/ver','/rezervasyonlar','/rezervasyonlar/ekle','/bildirimler','/tasarim-kaliplari','/ayarlar','/analitik','/raporlar','/dijital-kutuphane','/cezalar','/islem-gecmisi','/ayarlar/odunc-politikasi'];
    for (const route of routes) { await visit(route); await noOverflow(route); }
    await visit('/tasarim-kaliplari');
    assert.equal(await page.locator('.uml-scroll img').count(), 4); checks++;
    for (const image of await page.locator('.uml-scroll img').all()) {
      await image.scrollIntoViewIfNeeded();
      await image.evaluate(img => img.decode());
    }
    assert.ok(await page.locator('.uml-scroll img').evaluateAll(images => images.every(img => img.complete && img.naturalWidth > 0))); checks++;
    await page.locator('#factory select').selectOption('ebook');
    await page.locator('#factory button[type=submit]').click();
    assert.match(await page.locator('#factory .demo-result').innerText(), /EBook/); checks++;
    await page.locator('#observer .demo-form button[type=submit]').click();
    assert.match(await page.locator('#observer .demo-result').innerText(), /1 gözlemci/); checks++;
    await page.locator('#factory').screenshot({ path: path.join(output, 'tasarim-kaliplari.png') });
    // Gerçek kitap formunda türe özgü alanlar ve sunucu kaydı.
    await visit('/kitaplar/ekle');
    await page.getByLabel('Kitap türü').selectOption('ebook');
    assert.ok(await page.getByLabel('Dosya adresi').isVisible());
    assert.ok(await page.getByLabel('Raf konumu').isDisabled()); checks++;
    await page.getByLabel('Kitap adı', { exact: true }).fill('Arayüz Test Kitabı');
    await page.getByLabel('Yazar', { exact: true }).fill('Test Yazarı');
    await page.getByLabel('Dosya adresi').fill('https://example.invalid/ui.pdf');
    await page.getByRole('button', { name: 'Kitabı ekle', exact: true }).click();
    await page.waitForURL('**/kitaplar');
    assert.ok(await page.getByText('Arayüz Test Kitabı', { exact: true }).isVisible()); checks++;
    // Gerçek üye kaydı ve onay penceresinde vazgeçme/uygulama.
    await visit('/uyeler/ekle');
    await page.getByLabel('Ad soyad', { exact: true }).fill('Arayüz Test Üyesi');
    await page.getByLabel('E-posta', { exact: true }).fill('ui-test@example.invalid');
    await page.getByRole('button', { name: 'Üyeyi kaydet' }).click();
    await page.waitForURL('**/uyeler');
    const row = page.locator('tr').filter({ hasText: 'Arayüz Test Üyesi' });
    await row.getByRole('button', { name: 'Pasif yap' }).click();
    assert.ok(await page.locator('#confirm-dialog').isVisible()); checks++;
    await page.getByRole('button', { name: 'Vazgeç', exact: true }).click();
    assert.ok(await row.getByText('Aktif', { exact: true }).isVisible()); checks++;
    await row.getByRole('button', { name: 'Pasif yap' }).click();
    await page.getByRole('button', { name: 'Evet, devam et' }).click();
    await page.waitForLoadState();
    assert.ok(await page.locator('tr').filter({ hasText: 'Arayüz Test Üyesi' }).getByText('Pasif', { exact: true }).isVisible()); checks++;
    // Tablet ve telefon görünümü; yan menü ve Escape ile kapatma.
    for (const width of [768,390]) {
      await page.setViewportSize({ width, height: 844 });
      for (const route of ['/panel','/kitaplar','/uyeler','/odunc','/rezervasyonlar','/bildirimler','/tasarim-kaliplari','/ayarlar']) { await visit(route); await noOverflow(`${width}px ${route}`); }
      await page.getByRole('button', { name: 'Menüyü aç', exact: true }).click();
      assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'), 'true'); checks++;
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'), 'false'); checks++;
      if (width === 390) { await visit('/panel'); await page.screenshot({ path: path.join(output, 'dashboard-mobil.png'), fullPage: true }); }
    }
    const memberContext = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'tr-TR' });
    const member = await memberContext.newPage();
    observe(member);
    await member.goto(base+'/giris');
    await member.getByLabel('Kullanıcı adı', { exact:true }).fill('demo_uye');
    await member.getByLabel('Parola', { exact:true }).fill('DemoUye!2026');
    await member.locator('.login-form button[type=submit]').click();
    await member.waitForURL('**/panel');
    assert.equal(await member.locator('[data-stat=members]').count(), 0); checks++;
    // Aşama 9: gerçek ödünç → rezervasyon → iade → özel bildirim → iptal.
    await visit('/odunc/ver');
    const testBookId = await page.locator('#book_id option').filter({ hasText:'Arayüz Test Kitabı' }).getAttribute('value');
    const teacherId = await page.locator('#member_id option').filter({ hasText:'Demo Öğretmen' }).getAttribute('value');
    await page.locator('#book_id').selectOption(testBookId);
    await page.locator('#member_id').selectOption(teacherId);
    await page.getByRole('button', { name:'Ödünç kaydet', exact:true }).click();
    await page.waitForURL('**/odunc');
    assert.ok(await page.locator('tr').filter({ hasText:'Arayüz Test Kitabı' }).isVisible()); checks++;
    await member.goto(base+'/kitaplar');
    await member.locator('tr').filter({ hasText:'Arayüz Test Kitabı' }).getByRole('link', { name:'Rezerve et' }).click();
    await member.getByRole('button', { name:'Rezervasyonu kaydet', exact:true }).click();
    await member.waitForURL('**/rezervasyonlar');
    assert.ok(await member.locator('tr').filter({ hasText:'Arayüz Test Kitabı' }).getByText('Bekliyor', { exact:true }).isVisible()); checks++;
    await page.locator('tr').filter({ hasText:'Arayüz Test Kitabı' }).getByRole('link', { name:'İade al', exact:true }).click();
    await page.getByRole('button', { name:'İadeyi kaydet', exact:true }).click();
    await page.waitForURL('**/odunc?status=returned');
    assert.ok(await page.locator('tr').filter({ hasText:'Arayüz Test Kitabı' }).getByText('Kesin tutar', { exact:true }).isVisible()); checks++;
    await member.goto(base+'/bildirimler');
    const privateMessage = member.locator('.notification-card').filter({ hasText:'Arayüz Test Kitabı' }).filter({ hasText:'Kitap mevcut' });
    assert.ok(await privateMessage.isVisible()); checks++;
    assert.match(await privateMessage.innerText(), /48 saat ayrıldı/); checks++;
    await privateMessage.getByRole('button', { name:'Okundu işaretle', exact:true }).click();
    await member.waitForLoadState();
    assert.equal((await member.locator('.notification-count').innerText()).trim(), '1'); checks++;
    await member.getByRole('button', { name:'Tümünü okundu işaretle', exact:true }).click();
    await member.waitForLoadState();
    assert.equal((await member.locator('.notification-count').innerText()).trim(), '0'); checks++;
    await visit('/bildirimler');
    assert.equal(await page.locator('.notification-card').filter({ hasText:'Arayüz Test Kitabı' }).count(), 0); checks++;
    await member.goto(base+'/rezervasyonlar');
    await member.locator('tr').filter({ hasText:'Arayüz Test Kitabı' }).getByRole('button', { name:'Rezervasyonu iptal et', exact:true }).click();
    await member.getByRole('button', { name:'Evet, devam et', exact:true }).click();
    await member.waitForLoadState();
    await member.goto(base+'/rezervasyonlar?status=history');
    assert.ok(await member.locator('tr').filter({ hasText:'Arayüz Test Kitabı' }).getByText('İptal edildi', { exact:true }).isVisible()); checks++;
    const denied = await member.goto(base+'/uyeler');
    assert.equal(denied.status(), 403); checks++;
    await member.goto(base+'/panel');
    await member.goto(base+'/uye-kartim');
    const qrImage = member.getByAltText('Üye kartı QR kodu');
    assert.ok(await qrImage.evaluate(async element => { await element.decode(); return element.naturalWidth > 0; })); checks++;
    await member.screenshot({path:path.join(output,'uye-karti.png'),fullPage:true});
    if (auditStage >= 23) {
      const cardPng = await (await member.request.get(base+'/uye-kartim/qr')).body();
      await visit('/uye-tani');
      await page.evaluate(async encoded => {
        const buffer = Uint8Array.from(atob(encoded), character => character.charCodeAt(0));
        const image = await createImageBitmap(new Blob([buffer], {type:'image/png'}));
        const canvas = document.createElement('canvas');
        canvas.width = image.width;
        canvas.height = image.height;
        const context = canvas.getContext('2d');
        navigator.mediaDevices.getUserMedia = async () => {
          context.drawImage(image, 0, 0);
          const stream = canvas.captureStream(15);
          const timer = setInterval(() => context.drawImage(image, 0, 0), 100);
          window.addEventListener('pagehide', () => clearInterval(timer), {once:true});
          return stream;
        };
      }, cardPng.toString('base64'));
      await page.getByRole('button',{name:'Kamera ile tara'}).click();
      await page.getByRole('link',{name:'Üyeye ödünç ver'}).waitFor();
      assert.ok(await page.getByRole('link',{name:'Üyeye ödünç ver'}).isVisible()); checks++;
    }
    await member.goto(base+'/panel');
    await member.getByRole('button', { name: 'Menüyü aç', exact:true }).click();
    await member.locator('.logout-button').click();
    await member.waitForURL('**/giris'); checks++;
    // Kaydedilmiş XSS girdisi hem katalogda hem faaliyet günlüğünde çalışmamalıdır.
    await visit('/kitaplar/ekle');
    const xssPayload = '<img src=x onerror="window.__xss=1">';
    await page.getByLabel('Kitap adı', { exact:true }).fill(xssPayload);
    await page.getByLabel('Yazar', { exact:true }).fill('XSS Denetimi');
    await page.getByLabel('Raf konumu').fill('SEC-01');
    await page.getByRole('button', { name:'Kitabı ekle', exact:true }).click();
    await page.waitForURL('**/kitaplar');
    assert.ok(await page.getByText(xssPayload, { exact:true }).isVisible()); checks++;
    assert.equal(await page.evaluate(() => window.__xss), undefined); checks++;
    assert.equal(await page.locator('.catalog img').count(),0); checks++;
    await visit('/panel');
    assert.equal(await page.evaluate(() => window.__xss), undefined); checks++;
    if (auditStage >= 23) {
      await visit('/analitik');
      assert.ok(await page.locator('.analytics-bars meter').first().isVisible()); checks++;
      await page.screenshot({path:path.join(output,'analitik.png'),fullPage:true});
      await visit('/raporlar');
      const download = page.waitForEvent('download');
      await page.getByRole('link',{name:'PDF indir'}).click();
      assert.match((await download).suggestedFilename(), /\.pdf$/); checks++;
      await page.screenshot({path:path.join(output,'raporlar.png'),fullPage:true});
      const python = path.resolve(__dirname,'..','.venv','Scripts','python.exe');
      const pdf = spawnSync(python,['-c',[
        'from io import BytesIO',
        'from reportlab.pdfgen.canvas import Canvas',
        'import sys',
        'output = BytesIO()',
        'document = Canvas(output)',
        'document.drawString(60,760,"Test page 1")',
        'document.showPage()',
        'document.drawString(60,760,"Test page 2")',
        'document.save()',
        'sys.stdout.buffer.write(output.getvalue())',
      ].join('\n')],{windowsHide:true});
      assert.equal(pdf.status,0,String(pdf.stderr));
      await visit('/kitaplar/ekle');
      await page.locator('#book_type').selectOption('ebook');
      await page.locator('#title').fill('PDF okuyucu denemesi');
      await page.locator('#author').fill('Deneme yazarı');
      await page.locator('#media').setInputFiles({name:'deneme.pdf',mimeType:'application/pdf',buffer:pdf.stdout});
      await page.locator('input[name=rights]').check();
      await page.getByRole('button',{name:'Kitabı ekle',exact:true}).click();
      await page.waitForURL('**/kitaplar');
      await visit('/dijital-kutuphane');
      await page.locator('.import-card').filter({hasText:'PDF okuyucu denemesi'}).getByRole('link',{name:'Oku',exact:true}).click();
      await page.waitForURL('**/oku');
      const saved = page.waitForResponse(response => response.url().endsWith('/ilerleme') && response.status()===204 &&
        new URLSearchParams(response.request().postData()).get('position') === '2');
      await page.getByRole('button',{name:'Sonraki',exact:true}).click();
      await saved;
      await page.waitForFunction(() => document.querySelector('#pdf-page').src.includes('/sayfa/2') && document.querySelector('#pdf-page').complete);
      const marked = page.waitForResponse(response => response.url().endsWith('/ayrac') && response.status()===204);
      await page.getByRole('button',{name:'Sayfayı işaretle'}).click();
      await marked;
      await page.waitForFunction(() => document.querySelector('#bookmarks option[value="2"]'));
      await page.reload();
      await page.waitForFunction(() => document.querySelector('#page-number').value === '2');
      assert.equal(await page.locator('#reading-progress').getAttribute('value'),'100'); checks++;
      await page.screenshot({path:path.join(output,'pdf-okuyucu.png'),fullPage:true});
      const wav = spawnSync(python,['-c',[
        'from io import BytesIO',
        'import sys, wave',
        'output = BytesIO()',
        'with wave.open(output, "wb") as sound:',
        '  sound.setparams((1,2,8000,0,"NONE","not compressed"))',
        '  sound.writeframes(bytes(32000))',
        'sys.stdout.buffer.write(output.getvalue())',
      ].join('\n')],{windowsHide:true});
      assert.equal(wav.status,0,String(wav.stderr));
      await visit('/kitaplar/ekle');
      await page.locator('#book_type').selectOption('audio');
      await page.locator('#title').fill('Sesli kitap denemesi');
      await page.locator('#author').fill('Deneme yazarı');
      await page.locator('#media').setInputFiles({name:'deneme.wav',mimeType:'audio/wav',buffer:wav.stdout});
      await page.locator('input[name=rights]').check();
      await page.getByRole('button',{name:'Kitabı ekle',exact:true}).click();
      await page.waitForURL('**/kitaplar');
      await visit('/dijital-kutuphane');
      await page.locator('.import-card').filter({hasText:'Sesli kitap denemesi'}).getByRole('link',{name:'Dinle',exact:true}).click();
      await page.waitForFunction(() => document.querySelector('#audio-reader')?.readyState > 0);
      await page.locator('#speed').selectOption('1.5');
      assert.equal(await page.locator('#audio-reader').evaluate(audio=>audio.playbackRate), 1.5); checks++;
      await page.locator('#volume').evaluate(control => {
        control.value = '.5';
        control.dispatchEvent(new Event('input'));
      });
      assert.equal(await page.locator('#audio-reader').evaluate(audio=>audio.volume), .5); checks++;
      const audioSaved = page.waitForResponse(response => response.url().endsWith('/ilerleme') && response.status()===204 &&
        Number(new URLSearchParams(response.request().postData()).get('position')) === 1.5);
      await page.locator('#audio-reader').evaluate(audio => { audio.currentTime = 1.5; });
      await audioSaved;
      await page.reload();
      await page.waitForFunction(() => document.querySelector('#audio-reader')?.currentTime >= 1.49);
      await page.screenshot({path:path.join(output,'sesli-kitap.png'),fullPage:true}); checks++;
    }
    await memberContext.close();
    await context.close();
    const noJsContext = await browser.newContext({ viewport: { width: 390, height: 844 }, javaScriptEnabled: false });
    const noJsPage = await noJsContext.newPage();
    observe(noJsPage);
    await noJsPage.goto(base+'/giris');
    await noJsPage.getByLabel('Kullanıcı adı', { exact:true }).fill('demo_uye');
    await noJsPage.getByLabel('Parola', { exact:true }).fill('DemoUye!2026');
    await noJsPage.locator('.login-form button[type=submit]').click();
    await noJsPage.waitForURL('**/panel');
    assert.ok(await noJsPage.locator('#sidebar').getByRole('link',{name:'Kitaplar',exact:true}).isVisible()); checks++;
    assert.ok(await noJsPage.locator('.chart-data summary').isVisible()); checks++;
    await noJsContext.close();
    assert.deepEqual(failures, [], 'JavaScript veya CSP hatası');
    const report = { auditStage,status:'passed',checks, javascriptErrors: failures, expectedHttp, browserVersion:browser.version(), finishedAt:new Date().toISOString(), viewports: [1440,768,390], integratedWorkflow: ['borrow','reserve','return','private_notification','mark_read','cancel','stored_xss'], screenshots: fs.readdirSync(output).filter(name=>name.endsWith('.png')) };
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } catch (error) {
    fs.writeFileSync(reportPath,JSON.stringify({auditStage,status:'failed',checks,javascriptErrors:failures,expectedHttp,error:error.message,finishedAt:new Date().toISOString()},null,2));
    throw error;
  } finally { await browser.close(); }
})().catch(error => {
  const report=fs.existsSync(reportPath)?JSON.parse(fs.readFileSync(reportPath,'utf8')):{};
  fs.writeFileSync(reportPath,JSON.stringify({...report,status:'failed',error:error.message},null,2));
  console.error(error); process.exitCode = 1;
});
