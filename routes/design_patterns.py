"""Gerçek sınıfları açıklayan, eğitim örnekleri açıkça etiketli kalıp sayfası."""
from datetime import timedelta
from dataclasses import asdict
import inspect
import sqlite3
from flask import Blueprint,render_template,request,abort,current_app,g
from security import login_required
from database import get_db, init_db
from services.loan_service import today, return_loan
from services.reservation_service import create_reservation
from patterns.factory_method import BookCreator,CREATORS
from patterns.adapter import GoogleBooksAdapter,GoogleBooksAPI
from patterns.open_library_adapter import OpenLibraryAdapter
from services.open_library_api import OpenLibraryAPI
from patterns.strategy import PenaltyCalculator,StudentPenalty,TeacherPenalty,StandardPenalty
from patterns.observer import Observer,BookAvailabilitySubject

bp=Blueprint('design_patterns',__name__)

PATTERNS=[
    {'id':'factory','name':'Factory Method','category':'Yaratımsal','icon':'book',
     'definition':'Bir ürünün oluşturulmasını soyut bir metotla tanımlar; somut ürünü alt sınıflar seçer.',
     'purpose':'Kitap türüne özgü üretim ve doğrulama kurallarını ortak kayıt akışından ayırmak.',
     'scenario':'Elektronik Kitap seçin. EBookCreator tarafından üretilen EBook nesnesini sonuçta görün.',
     'problem':'Fiziksel kitap raf konumu, elektronik ve sesli kitap ise uygun dijital kaynak ister. Ürünlerin doğrulama kuralları farklıdır.',
     'solution':'BookCreator.prepare_book(), alt sınıfın create_book() metodunu çağırır; dönen Book kendi türe özgü alanlarını doğrular.',
     'usage':'Kitap ekleme ve düzenlemede hizmet bir oluşturucu seçer; ürün doğrulanıp aynı işlemde SQLite’a yazılır.',
     'advantages':['Tür oluşturma mantığı HTTP ve SQL’den ayrılır.','Yeni oluşturucu ortak hazırlama akışını değiştirmez.'],
     'disadvantages':['Her yeni tür bir ürün ve oluşturucu sınıfı gerektirir.','SQL kısıtları ve arayüz seçenekleri de genişletilir.'],
     'classes':'Book · PhysicalBook · EBook · AudioBook · BookCreator · PhysicalBookCreator · EBookCreator · AudioBookCreator',
     'file':'patterns/factory_method.py','source':BookCreator,'diagram':'uml-factory.svg'},
    {'id':'adapter','name':'Adapter','category':'Yapısal','icon':'loans',
     'definition':'Uyumsuz bir dış arayüzü, istemcinin beklediği ortak sözleşmeye dönüştürür.',
     'purpose':'İki katalog sağlayıcısının verisini tek kitap formunda kullanabilmek.',
     'scenario':'Bir sağlayıcı seçin. Örnek kaynak JSON’daki başlık ve yazarın uyarlanmış verideki title ve author alanlarına aktarımını izleyin.',
     'problem':'Google Books cilt verisi, Open Library eser ve baskı verisi döndürür. Uygulama ortak kitap alanlarını bekler.',
     'solution':'GoogleBooksAdapter ve OpenLibraryAdapter, BookDataProvider sözleşmesine uyar ve kendi HTTP istemcisinin verisini BookImportData biçimine dönüştürür.',
     'usage':'Kitap Keşfet araması ve kitap ayrıntısı adaptörlerden geçer. İçe aktarma formu Factory Method ile kaydedilir.',
     'advantages':['Dış JSON biçimi uygulamaya yayılmaz.','Eksik alan ve güvenli kapak dönüşümü tek yerde yönetilir.'],
     'disadvantages':['Dış API şeması değişince adaptör güncellenir.','Google erişimi ve kota uygulamanın kontrolünde değildir.'],
     'classes':'BookDataProvider · GoogleBooksAPI · GoogleBooksAdapter · OpenLibraryAPI · OpenLibraryAdapter · BookImportData',
     'file':'patterns/adapter.py','source':GoogleBooksAdapter.adapt,'diagram':'uml-adapter.svg'},
    {'id':'strategy','name':'Strategy','category':'Davranışsal','icon':'chart',
     'definition':'Değiştirilebilir algoritmaları ortak arayüz arkasında toplar; bağlam çalışma sırasında strateji değiştirebilir.',
     'purpose':'Üye türüne göre gecikme tarifesini aynı hesaplayıcı üzerinde değiştirmek.',
     'scenario':'Beş gün girin. Başlangıç tarifeleriyle Öğrenci 10 TL, Öğretmen 5 TL, Normal Üye 25 TL öder.',
     'problem':'Üyelik türüne göre farklı gecikme ücretleri tek bir büyük koşul bloğuna dönüşebilir.',
     'solution':'PenaltyCalculator, ücrete PenaltyStrategy üzerinden erişir; StudentPenalty, TeacherPenalty ve StandardPenalty farklı algoritmaları uygular.',
     'usage':'İade anında üyelik türü SQLite’tan okunur. Kesin tutar hesaplanıp kuruş olarak iadeyle aynı işlemde kaydedilir.',
     'advantages':['Algoritma ve tarih hesabı ayrıdır.','Aynı hesaplayıcıda set_strategy() ile değişim yapılır.'],
     'disadvantages':['Yeni üyelik türünün strateji eşlemesi gerekir.','Tarife sürümleme ve tahsilat ayrı sorumluluklardır.'],
     'classes':'PenaltyStrategy · StudentPenalty · TeacherPenalty · StandardPenalty · PenaltyCalculator',
     'file':'patterns/strategy.py','source':PenaltyCalculator,'diagram':'uml-strategy.svg'},
    {'id':'observer','name':'Observer','category':'Davranışsal','icon':'bell',
     'definition':'Bir konudaki değişimi, abone olmuş gözlemcilere ortak bir güncelleme arayüzüyle bildirir.',
     'purpose':'Kitap kullanılabilir olduğunda rezervasyon sahibine otomatik bildirim göndermek.',
     'scenario':'Rezervasyon, iade ve bildirimi dene düğmesine basın. Bekleyen üyeye iadenin ardından kaydedilen bildirimi görün.',
     'problem':'İade hizmetinin her rezervasyon sahibinin bildirim mantığını bilmesi sorumlulukları birbirine bağlar.',
     'solution':'BookAvailabilitySubject abone listesini yönetir; MemberObserver.update() NotificationService üzerinden mesaj kaydeder.',
     'usage':'İade veya stok artışında aboneler SQLite’tan kronolojik yüklenir. Bildirim ve iade aynı işlemde kesinleşir; rezervasyon başına tek mesaj vardır.',
     'advantages':['Konu ve gözlemciler gevşek bağlıdır.','Abonelikler veritabanından yeniden yüklenebilir.'],
     'disadvantages':['Senkron yayın işlem süresini uzatır.','Bir gözlemci hatası bütün işlemi geri alır.'],
     'classes':'Observer · Subject · BookAvailabilitySubject · MemberObserver · NotificationService',
     'file':'patterns/observer.py','source':BookAvailabilitySubject,'diagram':'uml-observer.svg'},
]


def page(result=None,error=None):
    patterns=[{**pattern,'code':inspect.getsource(pattern['source'])} for pattern in PATTERNS]
    return render_template('design_patterns.html',patterns=patterns,result=result,error=error)


def isolated_circulation_demo():
    with current_app.app_context():
        g.db = sqlite3.connect(':memory:')
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
        init_db()
        db = get_db()
        with db:
            db.execute("INSERT INTO members(full_name,email,member_type) VALUES('Okuyucu','okur@example.test','student')")
            db.execute("INSERT INTO members(full_name,email,member_type) VALUES('Bekleyen','bekleyen@example.test','teacher')")
            db.execute("INSERT INTO books(title,author,book_type,shelf_location) VALUES('Eğitim kitabı','Örnek','physical','E-01')")
            now = today().isoformat()
            db.execute('INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(1,1,?,?)', (now, now))
        reservation = create_reservation(1, 2, None)
        return_loan(1, None)
        message = db.execute('SELECT message FROM notifications WHERE reservation_id=?', (reservation,)).fetchone()['message']
        return [
            f'Rezervasyon #{reservation} bekleme sırasına eklendi.',
            'İade alındı. Konu: BookAvailabilitySubject, gözlemci: MemberObserver.',
            f'Otomatik bildirim: {message}',
            'İşlemler yalıtılmış bellek veritabanında gerçekleşti.',
        ]


@bp.get('/tasarim-kaliplari')
@login_required
def index():
    return page()


@bp.post('/tasarim-kaliplari/<pattern_id>/dene')
@login_required
def demo(pattern_id):
    result=None
    error=None
    try:
        if pattern_id=='factory':
            kind=request.form.get('book_type','physical')
            if kind not in CREATORS:
                raise ValueError('Geçerli kitap türü seçin.')
            book=CREATORS[kind]().prepare_book(
                id=None, title='Eğitim kitabı', author='Örnek yazar', isbn=None, category_id=None,
                total_copies=1, created_at='', shelf_location='E-01' if kind=='physical' else None,
                file_url=None, managed_media=kind!='physical',
            )
            result={'id':pattern_id,'lines':[f'Oluşturucu: {CREATORS[kind].__name__}',f'Ürün: {type(book).__name__}',f'Tür: {book.type_label}','Ürüne özgü doğrulama başarılı; yeni kayıt oluşturulmadı.']}
        elif pattern_id=='adapter':
            row=get_db().execute('SELECT * FROM books ORDER BY id LIMIT 1').fetchone()
            if row is None:
                row={'id':1,'title':'Eğitim kitabı','author':'Örnek yazar','isbn':None}
            provider = request.form.get('provider', 'google')
            identifiers=[{'type':'ISBN_13' if len(row['isbn'])==13 else 'ISBN_10','identifier':row['isbn']}] if row['isbn'] else []
            if provider == 'open_library':
                external={'key':'/works/OL1W','title':row['title'],'author_name':[row['author']]}
                draft=OpenLibraryAdapter(OpenLibraryAPI()).adapt('OL1W', external)
            elif provider == 'google':
                external={'id':str(row['id']),'volumeInfo':{'title':row['title'],'authors':[row['author']],'industryIdentifiers':identifiers}}
                draft=GoogleBooksAdapter(GoogleBooksAPI()).adapt(external)
            else:
                raise ValueError('Geçerli bir sağlayıcı seçin.')
            result={'id':pattern_id,'lines':['Eğitim JSON verisi gerçek adaptörle dönüştürüldü.',
                                            f'Yazar: {draft.author or "Belirtilmemiş"}'],
                    'external':external,'adapted':asdict(draft)}
        elif pattern_id=='strategy':
            try:
                days=int(request.form.get('days','5'))
            except ValueError:
                raise ValueError('Geçerli gecikme günü girin.') from None
            if not 0<=days<=3650:
                raise ValueError('Gecikme günü 0–3650 aralığında olmalıdır.')
            calculator=PenaltyCalculator(StudentPenalty())
            strategies={'student':(StudentPenalty(),'Öğrenci'),'teacher':(TeacherPenalty(),'Öğretmen'),'standard':(StandardPenalty(),'Normal Üye')}
            selected=request.form.get('member_type','student')
            if selected not in strategies:
                raise ValueError('Geçerli üye türü seçin.')
            lines=[]
            order=[selected, *[kind for kind in strategies if kind!=selected]]
            for kind in order:
                strategy,label=strategies[kind]
                calculator.set_strategy(strategy)
                lines.append(f'{label}: {calculator.calculate(today(),today()+timedelta(days=days)):.2f} TL'.replace('.',','))
            result={'id':pattern_id,'lines':lines+['Aynı PenaltyCalculator nesnesinde strateji değiştirildi.']}
        elif pattern_id=='observer':
            if request.form.get('scenario') == 'circulation':
                return page({'id':pattern_id, 'lines':isolated_circulation_demo()})
            events=[]
            class DemoObserver(Observer):
                def __init__(self,label): self.label=label
                def update(self,book_id,title):
                    events.append(f'{self.label}: update({book_id}, {title}) çağrıldı.')
                    return True
            row=get_db().execute('SELECT id,title FROM books ORDER BY id LIMIT 1').fetchone()
            if row is None:
                raise ValueError('Katalogda kitap yok; önce gerçek bir kayıt ekleyin.')
            subject=BookAvailabilitySubject(row['id'],row['title'])
            first,second=DemoObserver('Gözlemci A'),DemoObserver('Gözlemci B')
            subject.attach(first)
            subject.attach(second)
            if request.form.get('detach')=='yes': subject.detach(second)
            count=subject.notify()
            result={'id':pattern_id,'lines':events+[f'{count} gözlemci güncellendi. Gerçek üye bildirimi oluşturulmadı.']}
        else:
            abort(404)
    except ValueError as problem:
        error=str(problem)
    return page(result,error),422 if error else 200
