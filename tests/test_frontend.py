"""Panel verisi, yeni sayfalar, üye yönetimi ve eğitim örnekleri."""
import re
import pytest
from app import create_app
from database import get_db,init_db
from seed import seed_demo
from services.demo_accounts import prepare_demo_accounts,DEMO_ADMIN_PASSWORD,DEMO_MEMBER_PASSWORD
from services.dashboard_service import dashboard_data
from services.auth_service import active_user
from services import member_service
from types import SimpleNamespace


@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'frontend-test','DATABASE':str(tmp_path/'frontend.sqlite3')})
    with app.app_context():
        init_db()
        seed_demo(get_db())
        prepare_demo_accounts(get_db())
    return app


def csrf(client,path='/giris'):
    return re.search(rb'name="csrf_token" value="([^"]+)"',client.get(path).data).group(1).decode()


def login(app,role='admin'):
    client=app.test_client()
    assert client.post('/giris',data={'csrf_token':csrf(client),'username':'demo_yonetici' if role=='admin' else 'demo_uye',
                                   'password':DEMO_ADMIN_PASSWORD if role=='admin' else DEMO_MEMBER_PASSWORD}).status_code==302
    return client


def test_admin_dashboard_matches_sqlite(app):
    with app.app_context():
        data=dashboard_data(active_user(1))
        cards={card['key']:card['value'] for card in data['cards']}
        assert cards=={'books':2,'available':1,'members':3,'active':1,'overdue':1,'reservations':1}
        assert sum(point['borrowed'] for point in data['series'])==2
        assert sum(point['returned'] for point in data['series'])==1
        assert data['type_total']==2 and data['demo_data']
        assert data['overdue_rows'][0]['title']=='Demo Fiziksel Kitap'
    page=login(app).get('/panel')
    assert page.status_code==200 and b'data-stat="members" data-value="3"' in page.data
    assert 'gösterim kayıtları'.encode() in page.data


def test_member_dashboard_scopes_statistics_and_activity(app):
    with app.app_context():
        data=dashboard_data(active_user(2))
        cards={card['key']:card['value'] for card in data['cards']}
        assert cards=={'notifications':0,'active':1,'overdue':1,'reservations':0}
        assert sum(point['borrowed'] for point in data['series'])==1
        assert sum(point['returned'] for point in data['series'])==0
        assert all(row['details']=='Demo Fiziksel Kitap' for row in data['activities'])
    page=login(app,'member').get('/panel')
    assert 'Demo Normal Üye'.encode() not in page.data
    assert 'Gösterim hesapları'.encode() not in page.data


def test_empty_database_has_zero_statistics(tmp_path):
    app=create_app({'TESTING':True,'DATABASE':str(tmp_path/'empty.sqlite3')})
    with app.app_context():
        init_db()
        data=dashboard_data(SimpleNamespace(id=1,role='admin'))
        assert all(card['value']==0 for card in data['cards'])
        assert all(point['borrowed']==point['returned']==0 for point in data['series'])
        assert data['type_total']==0 and not data['activities'] and not data['demo_data']


@pytest.mark.parametrize('path',['/panel','/kitaplar','/uyeler','/odunc','/rezervasyonlar','/bildirimler','/tasarim-kaliplari','/ayarlar'])
def test_all_admin_pages_render_with_shell(app,path):
    result=login(app).get(path)
    assert result.status_code==200
    assert b'id="sidebar"' in result.data and b'class="topbar"' in result.data
    assert b'/static/js/theme.js' in result.data
    assert b'lang="tr"' in result.data


@pytest.mark.parametrize('path',['/uyeler','/uyeler/ekle','/uyeler/1','/uyeler/1/duzenle'])
def test_member_cannot_access_directory(app,path):
    assert login(app,'member').get(path).status_code==403


@pytest.mark.parametrize('path',['/uyeler','/ayarlar','/tasarim-kaliplari'])
def test_anonymous_new_pages(app,path):
    assert app.test_client().get(path).status_code==302


def test_member_create_edit_status_history(app):
    client=login(app)
    form={'full_name':'Yeni Öğrenci','email':'new@example.invalid','member_type':'student','csrf_token':csrf(client,'/uyeler')}
    assert client.post('/uyeler/ekle',data=form).status_code==302
    with app.app_context():
        member_id=get_db().execute("SELECT id FROM members WHERE email='new@example.invalid'").fetchone()[0]
    form.update(full_name='Yeni Öğretmen',member_type='teacher')
    assert client.post(f'/uyeler/{member_id}/duzenle',data=form).status_code==302
    assert 'Yeni Öğretmen'.encode() in client.get('/uyeler?q=öğretmen').data
    assert client.get(f'/uyeler/{member_id}').status_code==200
    for value in ('0','1'):
        assert client.post(f'/uyeler/{member_id}/durum',data={'active':value,'csrf_token':csrf(client,'/uyeler')}).status_code==302
        with app.app_context():
            assert member_service.get_member(member_id)['is_active']==int(value)


@pytest.mark.parametrize('changes',[{'full_name':''},{'email':'bad'},{'member_type':'unknown'},{'email':'ogrenci@example.invalid'}])
def test_member_validation(app,changes):
    client=login(app)
    form={'full_name':'Test Üye','email':'test@example.invalid','member_type':'standard','csrf_token':csrf(client,'/uyeler'),**changes}
    assert client.post('/uyeler/ekle',data=form).status_code==422
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM members').fetchone()[0]==3


def test_member_form_csrf_and_authorization(app):
    admin=login(app)
    assert admin.post('/uyeler/ekle',data={}).status_code==400
    assert admin.post('/uyeler/1/durum',data={'active':'0'}).status_code==400
    member=login(app,'member')
    assert member.post('/uyeler/1/durum',data={'active':'0','csrf_token':csrf(member,'/panel')}).status_code==403


@pytest.mark.parametrize('pattern,fields,expected',[
    ('factory',{'book_type':'physical'},'PhysicalBook'),('factory',{'book_type':'ebook'},'EBook'),
    ('factory',{'book_type':'audio'},'AudioBook'),
    ('adapter',{},'Gösterim Yazarı'),('adapter',{'provider':'open_library'},'Uyarlanmış veri'),
    ('strategy',{'days':'5'},'25,00 TL'),
    ('observer',{'detach':'yes'},'1 gözlemci güncellendi'),('observer',{},'2 gözlemci güncellendi'),
    ('observer',{'scenario':'circulation'},'Otomatik bildirim')])
def test_pattern_demos_use_real_classes_without_db_writes(app,pattern,fields,expected):
    client=login(app,'member')
    with app.app_context():
        before={table:get_db().execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('books','loans','notifications','activity_logs')}
    result=client.post(f'/tasarim-kaliplari/{pattern}/dene',data={**fields,'csrf_token':csrf(client,'/tasarim-kaliplari')})
    assert result.status_code==200 and expected.encode() in result.data
    with app.app_context():
        after={table:get_db().execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in before}
        assert before==after


def test_demos_csrf_invalid_input_and_source_code(app):
    client=login(app)
    assert client.post('/tasarim-kaliplari/factory/dene',data={}).status_code==400
    assert client.post('/tasarim-kaliplari/strategy/dene',data={'days':'-1','csrf_token':csrf(client,'/tasarim-kaliplari')}).status_code==422
    page=client.get('/tasarim-kaliplari').data
    assert b'def prepare_book' in page and b'uml-observer.svg' in page
    assert 'Gerçek kalıp sınıfları'.encode() in page


def test_settings_do_not_expose_secrets(app):
    app.config['GOOGLE_BOOKS_API_KEY']='sensitive-test-key'
    for role in ('admin','member'):
        result=login(app,role).get('/ayarlar')
        assert result.status_code==200
        assert b'sensitive-test-key' not in result.data and b'frontend-test' not in result.data
        assert b'data-theme-choice="dark"' in result.data
