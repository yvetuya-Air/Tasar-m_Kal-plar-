"""Aşama 9: tüm rota sözleşmeleri, formlar, güvenlik ve tam iş akışı."""
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urljoin,urlsplit
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from database import get_db,init_db
from seed import seed_demo
from services.demo_accounts import prepare_demo_accounts,DEMO_ADMIN_PASSWORD,DEMO_MEMBER_PASSWORD
from services import loan_service,dashboard_service
from models.book import PhysicalBook,EBook
from services.book_service import get_book
from services.google_books_api import GoogleBooksAPI

ROOT=Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms=[]
        self.links=[]
        self.assets=[]
        self.ids=set()
        self.current=None

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get('id'): self.ids.add(attrs['id'])
        if tag=='a' and attrs.get('href'): self.links.append(attrs['href'])
        if tag in ('script','img') and attrs.get('src'): self.assets.append(attrs['src'])
        if tag=='link' and attrs.get('href'): self.assets.append(attrs['href'])
        if tag=='form':
            self.current={'action':attrs.get('action',''),'method':attrs.get('method','get').upper(),'inputs':{}}
            self.forms.append(self.current)
        if tag=='input' and self.current is not None and attrs.get('name'):
            self.current['inputs'][attrs['name']]=attrs.get('value','')

    def handle_endtag(self,tag):
        if tag=='form': self.current=None


def parsed(response):
    result=PageParser()
    result.feed(response.get_data(as_text=True))
    return result


def csrf(client,path='/giris'):
    response=client.get(path)
    match=re.search(rb'name="csrf_token" value="([^"]+)"',response.data)
    assert match, (path,response.status_code)
    return match.group(1).decode()


def login(client,name='demo_yonetici',password=DEMO_ADMIN_PASSWORD):
    response=client.post('/giris',data={'csrf_token':csrf(client),'username':name,'password':password})
    assert response.status_code==302
    return client


@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'audit-only','DATABASE':str(tmp_path/'audit.sqlite3')})
    with app.app_context():
        init_db()
        seed_demo(get_db())
        prepare_demo_accounts(get_db())
    return app


@pytest.fixture
def admin(app):
    return login(app.test_client())


def url_for_rule(rule):
    result=rule.rule
    for argument in rule.arguments:
        result=re.sub(r'<(?:[^:>]+:)?'+argument+r'>','factory' if argument=='pattern_id' else '1',result)
    return result


ADMIN_ONLY={'books.add','books.edit','books.delete','google_books.search','google_books.preview','member_cards.scan','settings.circulation','analytics.index','reports.index','system.audit','system.backup',
            'loans.borrow','loans.return_book','members.index','members.add','members.edit','members.status','members.history','dashboard.admin','categories.index'}
MEMBER_ONLY={'dashboard.account','member_portal.my_books','member_portal.shelf','member_portal.history','member_portal.profile',
             'member_cards.card','member_cards.qr','member_cards.download'}


def test_every_flask_route_permissions(app):
    anonymous=app.test_client()
    admin=login(app.test_client())
    member=login(app.test_client(),'demo_uye',DEMO_MEMBER_PASSWORD)
    for rule in app.url_map.iter_rules():
        if rule.endpoint=='static': continue
        path=url_for_rule(rule)
        if 'GET' in rule.methods:
            expected_anon=200 if rule.endpoint in ('index','auth.login','auth.reset') else 302
            assert anonymous.get(path).status_code==expected_anon,rule.endpoint
            expected_admin=302 if rule.endpoint=='auth.login' else 403 if rule.endpoint in MEMBER_ONLY else 200
            if rule.endpoint in ('digital.reader', 'digital.page_image', 'digital.audio'):
                expected_admin = 404
            assert admin.get(path).status_code==expected_admin,rule.endpoint
            expected_member=302 if rule.endpoint=='auth.login' else 403 if rule.endpoint in ADMIN_ONLY else 200
            if rule.endpoint in ('digital.reader', 'digital.page_image', 'digital.audio'):
                expected_member = 404
            if rule.endpoint == 'member_cards.download':
                expected_member = 404
            assert member.get(path).status_code==expected_member,rule.endpoint
        if 'POST' in rule.methods:
            # Güvenli token olmadan hiçbir rota veri yazmaya başlamaz.
            for client in (anonymous,admin,member):
                assert client.post(path,data={}).status_code==400,rule.endpoint
            if rule.endpoint in ADMIN_ONLY:
                assert member.post(path,data={'csrf_token':csrf(member,'/panel')}).status_code==403,rule.endpoint
                assert anonymous.post(path,data={'csrf_token':csrf(anonymous)}).status_code==302,rule.endpoint


@pytest.mark.parametrize('role',['admin','member'])
def test_rendered_forms_navigation_and_assets(app,role):
    client=login(app.test_client()) if role=='admin' else login(app.test_client(),'demo_uye',DEMO_MEMBER_PASSWORD)
    adapter=app.url_map.bind('localhost')
    for rule in app.url_map.iter_rules():
        if 'GET' not in rule.methods or rule.endpoint=='static': continue
        path=url_for_rule(rule)
        response=client.get(path)
        if response.status_code!=200 or response.mimetype!='text/html': continue
        document=parsed(response)
        for form in document.forms:
            action=urlsplit(urljoin('http://localhost'+path,form['action']))
            assert action.netloc=='localhost'
            endpoint,_=adapter.match(action.path,method=form['method'])
            assert endpoint in app.view_functions
            if form['method']=='POST': assert form['inputs'].get('csrf_token')
        for link in document.links:
            target=urlsplit(link)
            if target.netloc or target.scheme: continue
            if not target.path:
                assert not target.fragment or target.fragment in document.ids,link
            else:
                assert client.get(link).status_code in (200,302), (rule.endpoint,link)
        for asset in document.assets:
            if asset.startswith('/static/'):
                assert client.get(asset).status_code==200,asset


@pytest.mark.parametrize('token',['ı','🔒','a'*1000])
def test_malformed_csrf_is_rejected_not_500(admin,token):
    assert admin.post('/cikis',data={'csrf_token':token}).status_code==400
    assert admin.get('/panel').status_code==200


@pytest.mark.parametrize('path',['/uyeler/0/duzenle','/kitaplar/0/duzenle','/odunc/0/iade',
    '/uyeler/'+('9'*30),'/kitaplar/'+('9'*30)+'/duzenle','/uyeler/'+('9'*5000)])
def test_url_identifiers_outside_sqlite_range(admin,path):
    assert admin.get(path).status_code==404


def test_invalid_notification_identifier_with_correct_http_method(admin):
    assert admin.post('/bildirimler/'+('9'*30)+'/oku',data={'csrf_token':csrf(admin,'/panel')}).status_code==404


@pytest.mark.parametrize('path,data',[
    ('/kitaplar/ekle',{'title':'Test','author':'Test','book_type':'physical','total_copies':'1','shelf_location':'A','category_id':'9'*30}),
    ('/odunc/ver',{'book_id':'9'*30,'member_id':'1','due_on':'2099-01-01'}),
    ('/odunc/ver',{'book_id':'2','member_id':'9'*30,'due_on':'2099-01-01'}),
    ('/rezervasyonlar/ekle',{'book_id':'9'*30,'member_id':'3'}),
    ('/rezervasyonlar/ekle',{'book_id':'1','member_id':'9'*30}),
])
def test_form_identifiers_outside_sqlite_range(admin,path,data):
    assert admin.post(path,data={**data,'csrf_token':csrf(admin,'/panel')}).status_code==422


def test_google_preview_error_search_targets_correct_route(admin):
    result=admin.post('/kitaplar/google/aktar',data={'csrf_token':csrf(admin,'/panel'),'source_id':'../bad'})
    assert result.status_code==422
    form=next(form for form in parsed(result).forms if 'title' in form['inputs'])
    assert form['action']=='/kitaplar/google'


def test_large_request_and_database_failure_have_turkish_errors(app,admin,monkeypatch):
    app.config['MAX_CONTENT_LENGTH']=100
    response=admin.post('/kitaplar/ekle',data={'title':'x'*200})
    assert response.status_code==413
    assert 'İstek çok büyük'.encode() in response.data
    app.config['MAX_CONTENT_LENGTH']=1024*1024
    def unavailable(*args,**kwargs):
        raise sqlite3.OperationalError('private SQL details')
    monkeypatch.setattr('routes.books.book_service.search_books',unavailable)
    response=admin.get('/kitaplar')
    assert response.status_code==503
    assert 'Veritabanı geçici'.encode() in response.data
    assert b'private SQL details' not in response.data


def test_static_files_remain_available_when_database_is_down(app,admin,monkeypatch):
    def unavailable(): raise sqlite3.OperationalError('offline')
    monkeypatch.setattr('services.auth_service.get_db',unavailable)
    assert admin.get('/static/css/style.css').status_code==200


def test_member_zero_update_missing_and_history_preservation(app,admin):
    token=csrf(admin,'/uyeler')
    assert admin.post('/uyeler/999/duzenle',data={'csrf_token':token,'full_name':'Missing','email':'missing@example.invalid','member_type':'standard'}).status_code==404
    assert admin.post('/uyeler/1/durum',data={'csrf_token':token,'active':'unknown'}).status_code==400
    assert admin.post('/uyeler/1/durum',data={'csrf_token':token,'active':'0'}).status_code==302
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM loans WHERE member_id=1').fetchone()[0]==1
    assert 'Demo Fiziksel Kitap'.encode() in admin.get('/uyeler/1').data
    member=app.test_client()
    assert member.post('/giris',data={'csrf_token':csrf(member),'username':'demo_uye','password':DEMO_MEMBER_PASSWORD}).status_code==401


def test_optional_member_account_hash_role_and_deactivation(app,admin):
    from werkzeug.security import check_password_hash
    password='NewMember!2026'
    payload={'full_name':'Hesaplı Üye','email':'account@example.invalid','member_type':'teacher',
             'account_username':'linked_member','account_password':password,'role':'admin','csrf_token':csrf(admin,'/uyeler')}
    assert admin.post('/uyeler/ekle',data=payload).status_code==302
    with app.app_context():
        row=get_db().execute("SELECT m.id,u.role,u.password_hash FROM members m JOIN users u ON u.id=m.user_id WHERE u.username='linked_member'").fetchone()
        member_id=row['id']
        assert row['role']=='member' and row['password_hash']!=password
        assert check_password_hash(row['password_hash'],password)
    member=login(app.test_client(),'linked_member',password)
    assert member.get('/uyeler').status_code==403
    assert 'Hesaplı Üye'.encode() in member.get('/hesabim').data
    assert admin.post(f'/uyeler/{member_id}/durum',data={'active':'0','csrf_token':csrf(admin,'/uyeler')}).status_code==302
    assert member.get('/panel').status_code==302
    assert admin.post(f'/uyeler/{member_id}/durum',data={'active':'1','csrf_token':csrf(admin,'/uyeler')}).status_code==302
    assert login(app.test_client(),'linked_member',password).get('/panel').status_code==200


@pytest.mark.parametrize('account,password', [('ab','ValidPassword1'),('bad name','ValidPassword1'),('valid_name','short'),('valid_name',''),('','ValidPassword1')])
def test_invalid_member_account_is_atomic_and_password_not_echoed(app,admin,account,password):
    result=admin.post('/uyeler/ekle',data={'csrf_token':csrf(admin,'/uyeler'),'full_name':'Test','email':'valid@example.invalid',
                                        'member_type':'student','account_username':account,'account_password':password})
    assert result.status_code==422
    if password: assert password.encode() not in result.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM users').fetchone()[0]==2
        assert get_db().execute('SELECT COUNT(*) FROM members').fetchone()[0]==3


def test_duplicate_account_and_existing_account_edit_are_rejected(app,admin):
    data={'csrf_token':csrf(admin,'/uyeler'),'full_name':'Test','email':'duplicate@example.invalid','member_type':'student',
          'account_username':'demo_yonetici','account_password':'NeverEcho!2026'}
    assert admin.post('/uyeler/ekle',data=data).status_code==422
    data.update(email='ogrenci@example.invalid',account_username='rename_member')
    assert admin.post('/uyeler/1/duzenle',data=data).status_code==422
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM members').fetchone()[0]==3
        assert get_db().execute('SELECT username FROM users WHERE id=2').fetchone()[0]=='demo_uye'


def test_link_account_to_member_without_changing_history(app,admin):
    payload={'csrf_token':csrf(admin,'/uyeler'),'full_name':'Demo Öğretmen','email':'ogretmen@example.invalid','member_type':'teacher',
             'account_username':'teacher_account','account_password':'TeacherAccount!2026'}
    assert admin.post('/uyeler/2/duzenle',data=payload).status_code==302
    client=login(app.test_client(),'teacher_account','TeacherAccount!2026')
    assert 'Gösterim bildirimi'.encode() in client.get('/bildirimler').data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM reservations WHERE member_id=2').fetchone()[0]==1


def test_member_and_account_creation_roll_back_together(app,admin):
    with app.app_context():
        with get_db() as db:
            db.execute("CREATE TRIGGER fail_member_log BEFORE INSERT ON activity_logs WHEN NEW.action='member_saved' BEGIN SELECT RAISE(ABORT,'test failure'); END")
    payload={'csrf_token':csrf(admin,'/uyeler'),'full_name':'Rollback','email':'rollback@example.invalid','member_type':'standard',
             'account_username':'rollback_account','account_password':'RollbackAccount!2026'}
    assert admin.post('/uyeler/ekle',data=payload).status_code==422
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM users').fetchone()[0]==2
        assert get_db().execute('SELECT COUNT(*) FROM members').fetchone()[0]==3


def test_complete_factory_adapter_strategy_observer_workflow_and_restart(tmp_path,monkeypatch):
    database=tmp_path/'complete.sqlite3'
    app=create_app({'TESTING':True,'SECRET_KEY':'full-flow','DATABASE':str(database)})
    with app.app_context():
        init_db()
        with get_db() as db:
            db.execute("INSERT INTO users(username,password_hash,role) VALUES('flow_admin',?,'admin')",(generate_password_hash('FlowAdmin!2026'),))
    clock={'date':date(2026,11,1)}
    monkeypatch.setattr(loan_service,'today',lambda:clock['date'])
    monkeypatch.setattr(dashboard_service,'today',lambda:clock['date'])
    client=login(app.test_client(),'flow_admin','FlowAdmin!2026')
    def post(path,data):
        return client.post(path,data={**data,'csrf_token':csrf(client,'/panel')})
    # 1–2: Gerçek giriş ve Factory Method üzerinden fiziksel kitap.
    assert post('/kitaplar/ekle',{'title':'Entegrasyon Kitabı','author':'İş Akışı Yazarı','isbn':'9780306406157',
                                'book_type':'physical','total_copies':'1','shelf_location':'E-01'}).status_code==302
    with app.app_context():
        book_id=get_db().execute('SELECT id FROM books').fetchone()[0]
        assert isinstance(get_book(book_id),PhysicalBook)
    # 3: Yalnızca dış HTTP cevabı taklit edilir; gerçek Adapter ve kayıt fabrikası çalışır.
    volume={'id':'integration_volume','volumeInfo':{'title':'Taklit API Kitabı','authors':['Dış Yanıt Yazarı'],
             'industryIdentifiers':[{'type':'ISBN_13','identifier':'9780132350884'}]}}
    http=Mock()
    http.get.side_effect=lambda url,**kwargs:SimpleNamespace(status_code=200,json=lambda:{'items':[volume],'totalItems':1} if url.endswith('/volumes') else volume)
    monkeypatch.setattr('routes.google_books.GoogleBooksAPI',lambda key:GoogleBooksAPI(key,http=http))
    result=post('/kitaplar/google',{'title':'Taklit API Kitabı'})
    assert result.status_code==200 and 'Taklit API Kitabı'.encode() in result.data
    preview=post('/kitaplar/google/aktar',{'source_id':'integration_volume'})
    form=next(form for form in parsed(preview).forms if 'title' in form['inputs'])
    assert form['action']=='/kitaplar/ekle'
    imported={**form['inputs'],'title':'Düzenlenmiş API Kitabı','book_type':'ebook','total_copies':'1','category_id':'','shelf_location':'','file_url':'https://example.invalid/flow.pdf'}
    assert post(form['action'],imported).status_code==302
    with app.app_context():
        imported_id=get_db().execute("SELECT id FROM books WHERE isbn='9780132350884'").fetchone()[0]
        assert isinstance(get_book(imported_id),EBook)
    assert post(form['action'],imported).status_code==422
    # 4: İki gerçek üye formdan oluşturulur.
    for name,email,kind,account in [('İlk Üye','first@example.invalid','student','flow_first'),('Bekleyen Üye','waiting@example.invalid','teacher','flow_waiting')]:
        assert post('/uyeler/ekle',{'full_name':name,'email':email,'member_type':kind,'account_username':account,'account_password':'FlowMember!2026','role':'admin'}).status_code==302
    with app.app_context():
        db=get_db()
        first=db.execute("SELECT id FROM members WHERE email='first@example.invalid'").fetchone()[0]
        waiting=db.execute("SELECT id FROM members WHERE email='waiting@example.invalid'").fetchone()[0]
        assert db.execute("SELECT COUNT(*) FROM users WHERE role='member'").fetchone()[0]==2
    # 5–6: Ödünç ve aynı kitabın ikinci üyeye rezervasyonu.
    assert post('/odunc/ver',{'book_id':book_id,'member_id':first,'due_on':'2026-11-08'}).status_code==302
    with app.app_context(): loan_id=get_db().execute('SELECT id FROM loans').fetchone()[0]
    assert post('/rezervasyonlar/ekle',{'book_id':book_id,'member_id':waiting}).status_code==302
    assert post('/odunc/ver',{'book_id':book_id,'member_id':waiting,'due_on':'2026-11-08'}).status_code==422
    # 7–9: Saat yalnızca testte ilerletilir; istemci cezayı veya iade tarihini seçemez.
    clock['date']=date(2026,11,11)
    before=client.get('/panel')
    assert b'data-stat="overdue" data-value="1"' in before.data
    assert post(f'/odunc/{loan_id}/iade',{'penalty_cents':'0','member_type':'teacher','returned_on':'2026-11-01'}).status_code==302
    assert post(f'/odunc/{loan_id}/iade',{}).status_code==409
    with app.app_context():
        db=get_db()
        row=db.execute('SELECT * FROM loans WHERE id=?',(loan_id,)).fetchone()
        assert row['penalty_cents']==600 and row['returned_on']=='2026-11-11'
        reservation=db.execute('SELECT * FROM reservations').fetchone()
        assert reservation['status']=='notified'
        notification=db.execute('SELECT * FROM notifications WHERE reservation_id=?',(reservation['id'],)).fetchone()
        assert notification['member_id']==waiting
        notification_id=notification['id']
    waiter=login(app.test_client(),'flow_waiting','FlowMember!2026')
    owner=login(app.test_client(),'flow_first','FlowMember!2026')
    assert 'sizin için 48 saat ayrıldı'.encode() in waiter.get('/bildirimler').data
    assert 'sizin için 48 saat ayrıldı'.encode() not in owner.get('/bildirimler').data
    assert owner.post(f'/bildirimler/{notification_id}/oku',data={'csrf_token':csrf(owner,'/panel')}).status_code==404
    assert owner.post(f'/rezervasyonlar/{reservation["id"]}/iptal',data={'csrf_token':csrf(owner,'/panel')}).status_code==404
    assert waiter.post(f'/bildirimler/{notification_id}/oku',data={'csrf_token':csrf(waiter,'/panel')}).status_code==302
    assert '6,00 TL'.encode() in client.get('/uyeler/'+str(first)).data
    # 10: Tamamlanan akışın paneli doğrudan aynı veritabanını gösterir.
    with app.app_context():
        cards={card['key']:card['value'] for card in dashboard_service.dashboard_data(SimpleNamespace(id=1,role='admin'))['cards']}
        assert cards=={'books':2,'available':2,'members':2,'active':0,'overdue':0,'reservations':1}
        assert not get_db().execute('PRAGMA foreign_key_check').fetchall()
    for key,value in cards.items():
        assert f'data-stat="{key}" data-value="{value}"'.encode() in client.get('/panel').data
    # Yeni Python süreci + yeni Flask uygulaması: hafızadan bağımsız kalıcılık.
    code='''
import json,re,sys
from app import create_app
from database import get_db
app=create_app({'TESTING':True,'DATABASE':sys.argv[1],'SECRET_KEY':'restart-flow'})
with app.app_context():
    db=get_db()
    result={'books':db.execute('SELECT COUNT(*) FROM books').fetchone()[0],
            'members':db.execute('SELECT COUNT(*) FROM members').fetchone()[0],
            'penalty_cents':db.execute('SELECT penalty_cents FROM loans').fetchone()[0],
            'returned_on':db.execute('SELECT returned_on FROM loans').fetchone()[0],
            'reservation':db.execute('SELECT status FROM reservations').fetchone()[0],
            'is_read':db.execute('SELECT is_read FROM notifications WHERE reservation_id IS NOT NULL').fetchone()[0]}
client=app.test_client()
token=re.search(rb'name="csrf_token" value="([^"]+)"',client.get('/giris').data).group(1).decode()
assert client.post('/giris',data={'csrf_token':token,'username':'flow_waiting','password':'FlowMember!2026'}).status_code==302
assert client.get('/bildirimler').status_code==200
print(json.dumps(result))
'''
    process=subprocess.run([sys.executable,'-c',code,str(database)],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert process.returncode==0,process.stderr
    assert json.loads(process.stdout)=={'books':2,'members':2,'penalty_cents':600,'returned_on':'2026-11-11','reservation':'notified','is_read':1}
