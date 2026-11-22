"""Gerçek JUnit ve tarayıcı çıktısından Türkçe, vaka bazlı test raporu üretir."""
import argparse
import ast
from datetime import datetime,timedelta,timezone
from html import escape
import json
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
AREAS={
    'test_factory':'Factory Method','test_adapter':'Adapter','test_strategy':'Strategy',
    'test_observer':'Observer','test_database':'Veritabanı ve modeller','test_auth':'Kimlik doğrulama',
    'test_books':'Kitap yönetimi','test_loans':'Ödünç ve iade','test_reservations':'Rezervasyon ve bildirim',
    'test_frontend':'Arayüz ve dashboard','test_integration':'Tam entegrasyon','test_security':'Güvenlik',
    'test_app':'Uygulama başlangıcı',
}


def cell(value,limit=260):
    value=re.sub(r'\s+',' ',str(value)).strip()
    if len(value)>limit: value=value[:limit-1]+'…'
    return escape(value).replace('|','&#124;').replace('`','&#96;')


def source_details(module,function):
    path=ROOT/'tests'/(module+'.py')
    source=path.read_text(encoding='utf-8-sig')
    node=next((node for node in ast.walk(ast.parse(source)) if isinstance(node,ast.FunctionDef) and node.name==function),None)
    if node is None: raise ValueError(f'Test kaynağı bulunamadı: {module}.{function}')
    purpose=ast.get_docstring(node)
    if not purpose:
        topics=[('csrf','CSRF jetonlarının ve form güvenliğinin korunması.'),('xss','HTML girdisinin çalıştırılmadan güvenle gösterilmesi.'),
                ('injection','SQL saldırı girdisinin yalnız veri olarak işlenmesi.'),('password','Parola hash ve doğrulama kurallarının korunması.'),
                ('session','Oturum yaşam döngüsü ve yetki sınırlarının korunması.'),('concurrent','Eşzamanlı işlemlerde stok ve kayıt tutarlılığı.'),
                ('rollback','Başarısız işlemde bütün yazmaların geri alınması.'),('persistence','Verinin bağlantı/süreç değişiminden sonra korunması.'),
                ('private','Kişisel veriye yalnız sahibinin erişebilmesi.'),('role','Sunucu tarafı rol izinlerinin doğru uygulanması.')]
        purpose=next((text for key,text in topics if key in function),AREAS.get(module,module)+' davranışının kaynak testteki koşullarla doğrulanması.')
    expected=[]
    for child in ast.walk(node):
        if isinstance(child,ast.Assert): expected.append(ast.unparse(child.test))
        elif isinstance(child,ast.Call) and isinstance(child.func,ast.Attribute) and child.func.attr=='raises' and child.args:
            expected.append('Beklenen istisna: '+ast.unparse(child.args[0]))
    return purpose, ' ; '.join(expected[:3]) or 'Kaynak testin doğrulamaları hatasız tamamlanır.'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--junit',type=Path,required=True)
    parser.add_argument('--browser',type=Path,default=ROOT/'docs/screenshots/ui-test-result.json')
    args=parser.parse_args()
    tree=ET.parse(args.junit)
    records=[]
    for index,case in enumerate(tree.iter('testcase'),1):
        module=case.get('classname','').split('.')[-1]
        name=case.get('name','')
        function=name.split('[',1)[0]
        purpose,expected=source_details(module,function)
        problem=case.find('failure')
        error=case.find('error')
        skipped=case.find('skipped')
        status='Hata' if error is not None else 'Başarısız' if problem is not None else 'Atlandı' if skipped is not None else 'Başarılı'
        detail=error if error is not None else problem if problem is not None else skipped
        duration=float(case.get('time','0'))
        actual=(detail.get('message','')+' '+(detail.text or '')) if detail is not None else f'Kaynak doğrulamaları geçti ({duration:.3f} sn).'
        records.append({'id':f'T{index:03d}','module':module,'name':name,'purpose':purpose,
                        'steps':f'Bağımsız fixture verisini hazırla; pytest tests/{module}.py::{function} çalıştır. Parametre varyantı test adındadır.',
                        'expected':expected,'actual':actual,'status':status,'seconds':duration})
    if not records: raise ValueError('JUnit içinde yürütülmüş test bulunamadı.')
    summary={key:sum(record['status']==label for record in records) for key,label in [('passed','Başarılı'),('failed','Başarısız'),('errors','Hata'),('skipped','Atlandı')]}
    summary['total']=len(records)
    browser=json.loads(args.browser.read_text(encoding='utf-8')) if args.browser.exists() else {}
    browser_valid=browser.get('auditStage')==10 and browser.get('status')=='passed'
    now=datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y %H:%M')
    parts=['<!-- STAGE10-REPORT-BEGIN -->','## Aşama 10 — gerçek test raporu',f'Rapor oluşturulma zamanı: **{now} (Türkiye)**.',
           f"JUnit sonucu: **{summary['total']} vaka; {summary['passed']} başarılı, {summary['failed']} başarısız, {summary['errors']} hata, {summary['skipped']} atlandı**.",
           'Kaynak: [JUnit XML](audit/pytest-stage10.xml) ve [tam vaka JSON](audit/stage10-results.json). Önceki aşamaların aşağıdaki tarihsel sonuçları değiştirilmemiştir.',
           'Her satır yürütülmüş bir parametre varyantıdır. Beklenen sonuç sütunu kaynak testteki ilk doğrulamaları gösterir; bütün doğrulamalar test dosyasında korunur. Uzun metinlerin tamamı JSON/XML içindedir.',
           '### Otomatik Python vakaları']
    for module in dict.fromkeys(record['module'] for record in records):
        group=[record for record in records if record['module']==module]
        parts += [f'#### {AREAS.get(module,module)} — {len(group)} vaka',f'Kaynak: [tests/{module}.py](../tests/{module}.py).',
                  '| Test numarası | Test adı | Test amacı | Test adımları | Beklenen sonuç | Gerçek sonuç | Test durumu |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        parts += ['| '+' | '.join(cell(record[key]) for key in ('id','name','purpose','steps','expected','actual','status'))+' |' for record in group]
        parts.append('')
    parts += ['### Otomatik tarayıcı kontrolü',
              f"Son durum: **{cell(browser.get('status','yürütülmedi'))}**; {browser.get('checks',0)} kontrol. Bu aşama kimliği doğrulandı: **{'evet' if browser_valid else 'hayır; eski/eksik sonuç başarı sayılmaz'}**.",
              'Kaynak: [tarayıcı JSON](screenshots/ui-test-result.json). Beklenen 401/403 yanıtları açıkça kaydedilir; diğer HTTP, JavaScript ve CSP hataları testi başarısız yapar.',
              '| Test numarası | Test adı | Test amacı | Test adımları | Beklenen sonuç | Gerçek sonuç | Test durumu |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    browser_cases=[('Giriş ve hata mesajı','Yanlış ve doğru parola ile giriş yap.','Türkçe hata; doğru girişte panel.'),
                   ('Tema ve yoğunluk','Koyu temayı seç, yenile; açık temaya ve kompakt tabloya geç.','Tercihler uygulanır ve korunur.'),
                   ('Responsive gezinme','1440/768/390 pikselde sayfaları aç; menü ve Escape kullan.','Belge taşması yok; çekmece çalışır.'),
                   ('Formlar ve onay','Kitap ve üye ekle; pasifleştirmede vazgeç ve onayla.','Gerçek SQLite yazımı; vazgeçme yazmaz.'),
                   ('UML ve kalıplar','Dört diyagramı yükle; Factory ve Observer gösterimini çalıştır.','Görseller çözülür; gerçek kalıp sonucu gösterilir.'),
                   ('Ödünç ve rezervasyon','Yönetici ödünç versin; üye aynı kitabı rezerve etsin.','Stok ve bekleme listesi tutarlı.'),
                   ('İade ve özel bildirim','Kitabı iade et; üyede mesajı oku, yönetici hesabında ara.','Mesaj yalnız sahibinde; okunmamış sayaç azalır.'),
                   ('İptal ve çıkış','Rezervasyonu onayla iptal et; oturumu kapat.','Geçmişte iptal; girişe yönlendirme.'),
                   ('Tarayıcı XSS','Zararlı HTML içeren kitap ekle; katalog ve paneli aç.','HTML çalışmaz; DOM işareti oluşmaz.'),
                   ('JavaScript kapalı','JavaScript olmadan üye girişi ve menüyü dene.','Form ve gezinme kullanılabilir.')]
    for index,(name,steps,expected) in enumerate(browser_cases,1):
        parts.append('| '+' | '.join(cell(value) for value in (f'UI{index:02d}',name,'Tarayıcı davranışı ve kullanıcı güvenliği.',steps,expected,
                    'İlgili betik doğrulamaları geçti.' if browser_valid else browser.get('error','Güncel başarılı sonuç yok.'),'Başarılı' if browser_valid else 'Tamamlanmadı'))+' |')
    parts += ['','### Otomasyon ile manuel kontrolün ayrımı',
              'Chrome betiği ve HTTP istemcileriyle yapılan kontroller **otomatik** sayılır. Ekran görüntülerinin ajan tarafından okunması görsel incelemedir; insanın fiziksel telefonda kullanımı olarak sunulmaz.',
              '| Test numarası | Test adı | Test amacı | Test adımları | Beklenen sonuç | Gerçek sonuç | Test durumu |',
              '| --- | --- | --- | --- | --- | --- | --- |',
              '| V01 | Ajan görsel incelemesi | Görünür düzeni değerlendirme | Giriş hatası ve mobil panel ekran görüntülerini açıp incele. | Hata okunabilir; mobil içerik taşmaz. | Ekran görüntüleri incelendi; düzen uygun. İnsan cihaz testi değildir. | Başarılı |',
              '| G01 | Canlı Google Books | Gerçek sağlayıcı erişimini doğrulama | Anahtarsız Nutuk başlık araması yap. | Sağlayıcı kitap sonuçlarını döndürür. | Sağlayıcı kota hatası döndürdü; canlı içe aktarma doğrulanamadı. | Harici engel |',
              '| M01 | Gerçek telefonda dokunma | Fiziksel cihaz kullanımını doğrulama | Gerçek Android/iOS cihazda aynı akışı elle dene. | Form, klavye ve dokunma sorunsuz. | Bu aşamada fiziksel cihaz kullanılmadı. | Yürütülmedi |',
              '| M02 | Ekran okuyucu | Yardımcı teknoloji kullanımını doğrulama | NVDA/VoiceOver ile menü ve formları elle gez. | Odak ve etiketler anlaşılır. | Otomatik etiket/klavye kontrolleri insan ekran okuyucu testinin yerine geçmez. | Yürütülmedi |',
              '| M03 | Firefox/Safari | Farklı motorları doğrulama | Aynı senaryoyu bu tarayıcılarda elle çalıştır. | Chromium ile aynı iş davranışı. | Bu aşamada yalnız yerel Chromium motoru çalıştırıldı. | Yürütülmedi |',
              '','Başarısız veya atlanan vaka varsa yukarıda aynen korunur; rapor betiği bunları başarıya dönüştürmez. Ayrıntılar ve korunan ilk başarısız tarayıcı çıktısı: [Test auditi](AUDIT_TEST.md).',
              '<!-- STAGE10-REPORT-END -->']
    report=ROOT/'docs/TEST.md'
    previous=report.read_text(encoding='utf-8')
    previous=re.sub(r'<!-- STAGE10-REPORT-BEGIN -->.*?<!-- STAGE10-REPORT-END -->\s*','',previous,flags=re.S)
    lines=[]
    for part in parts:
        if part.startswith('|'):
            lines.append(part)
        else:
            if lines and lines[-1]!='': lines.append('')
            lines.extend((part,''))
    report.write_text('\n'.join(lines)+'\n\n'+previous,encoding='utf-8')
    (ROOT/'docs/audit/stage10-results.json').write_text(json.dumps({'summary':summary,'browser':browser,'cases':records},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary))
    return 1 if summary['failed'] or summary['errors'] or not browser_valid else 0


if __name__=='__main__':
    sys.exit(main())
