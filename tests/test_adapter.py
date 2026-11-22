"""Adapter ve HTTP hataları; tüm dış yanıtlar taklit edilir."""
from copy import deepcopy
import re
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import requests
from app import create_app
from database import get_db, init_db
from models.book import PhysicalBook, EBook
from patterns.adapter import BookDataProvider, GoogleBooksAdapter, safe_thumbnail
from services.google_books_api import GoogleBooksAPI, BookProviderError
from services import book_service
from services.demo_accounts import prepare_demo_accounts, DEMO_ADMIN_PASSWORD, DEMO_MEMBER_PASSWORD
from seed import seed_demo


def volume():
    return {'id':'test_volume-1','volumeInfo':{'title':'Dış Kaynak Kitabı', 'authors':['Yazar Bir','Yazar İki'],
            'industryIdentifiers':[{'type':'ISBN_10','identifier':'0306406152'},{'type':'ISBN_13','identifier':'9780306406157'}],
            'imageLinks':{'thumbnail':'http://books.google.com/books/content?id=test_volume-1&key=hidden-key'}}}


def response(payload, status=200):
    return SimpleNamespace(status_code=status,json=lambda:payload)


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def blocked(*args,**kwargs):
        raise AssertionError('Otomatik testte gerçek ağ isteği yasak.')
    monkeypatch.setattr(requests,'get',blocked)


def adapter_for(payload):
    api = Mock(spec=GoogleBooksAPI)
    api.search_volumes.return_value = payload
    api.get_volume.return_value = volume()
    return GoogleBooksAdapter(api)


def test_provider_is_abstract():
    with pytest.raises(TypeError):
        BookDataProvider()


def test_external_data_converted_to_internal_fields():
    item = volume()
    original = deepcopy(item)
    draft = adapter_for({}).adapt(item)
    assert draft.title == 'Dış Kaynak Kitabı'
    assert draft.author == 'Yazar Bir, Yazar İki'
    assert draft.isbn == '9780306406157'
    assert draft.thumbnail.startswith('https://books.google.com/')
    assert 'key=' not in draft.thumbnail
    assert draft.warnings == ()
    assert draft.to_form()['book_type'] == 'physical'
    assert item == original


@pytest.mark.parametrize('info',[None,{},'invalid',{'title':123,'authors':None,'industryIdentifiers':{}},
    {'title':'','authors':[None,4],'industryIdentifiers':[None,{'type':'ISBN_13','identifier':'bad'}]}])
def test_missing_and_wrong_typed_metadata(info):
    draft = adapter_for({}).adapt({'id':'test','volumeInfo':info})
    assert draft.title == '' and draft.author == '' and draft.isbn == ''
    assert len(draft.warnings) == 3 and draft.thumbnail is None


def test_isbn10_fallback():
    item=volume()
    item['volumeInfo']['industryIdentifiers'][1]['identifier']='invalid'
    assert adapter_for({}).adapt(item).isbn == '0306406152'


@pytest.mark.parametrize('url',[None,42,'javascript:alert(1)','https://evil.invalid/x','https://books.google.com.evil.invalid/x',
    'https://user:pass@books.google.com/x','https://books.google.com:443/x','https://[bad','https://books.google.com/a b'])
def test_cover_url_restrictions(url):
    assert safe_thumbnail(url) is None


def test_search_title_author_isbn_query():
    adapter = adapter_for({'items':[volume()], 'totalItems':1})
    results = adapter.search_books(title='Kitap',author='Yazar',isbn='978-0-306-40615-7')
    assert len(results)==1
    adapter.api.search_volumes.assert_called_once_with('intitle:"Kitap" inauthor:"Yazar" isbn:9780306406157')


@pytest.mark.parametrize('kwargs',[{}, {'title':'x'*201},{'isbn':'invalid'}])
def test_search_validation(kwargs):
    adapter=adapter_for({})
    with pytest.raises(ValueError):
        adapter.search_books(**kwargs)
    adapter.api.search_volumes.assert_not_called()


@pytest.mark.parametrize('payload',[{}, {'items':'bad'},{'items':None},{'totalItems':1},{'items':[None,{'id':'../bad'}]}])
def test_invalid_result_list(payload):
    with pytest.raises(BookProviderError):
        adapter_for(payload).search_books(title='test')


def test_empty_and_partially_valid_results():
    assert adapter_for({'totalItems':0}).search_books(title='test') == []
    assert len(adapter_for({'items':[None,volume(),volume()]}).search_books(title='test'))==1


def test_get_volume_identity_mismatch():
    adapter=adapter_for({})
    with pytest.raises(BookProviderError):
        adapter.get_book('other')


def test_http_parameters_timeout_and_optional_key():
    http=Mock()
    http.get.return_value=response({'totalItems':0})
    api=GoogleBooksAPI('server-only-secret', http=http)
    assert api.search_volumes('intitle:test') == {'totalItems':0}
    args,kwargs=http.get.call_args
    assert args[0]=='https://www.googleapis.com/books/v1/volumes'
    assert kwargs['params']['key']=='server-only-secret'
    assert kwargs['params']['maxResults']==12
    assert kwargs['timeout']==(3,8) and kwargs['allow_redirects'] is False
    GoogleBooksAPI(http=http).search_volumes('isbn:9780306406157')
    assert 'key' not in http.get.call_args.kwargs['params']


@pytest.mark.parametrize('exception,kind',[(requests.Timeout('secret'),'timeout'),(requests.ConnectionError('secret'),'connection')])
def test_connection_errors_do_not_expose_details(exception,kind):
    http=Mock()
    http.get.side_effect=exception
    with pytest.raises(BookProviderError) as caught:
        GoogleBooksAPI('secret',http=http).search_volumes('test')
    assert caught.value.kind==kind and 'secret' not in str(caught.value)


@pytest.mark.parametrize('status,payload,kind',[
    (429,{},'quota'),(403,{'error':{'errors':[{'reason':'dailyLimitExceeded'}]}},'quota'),
    (403,{},'access'),(401,{},'access'),(404,{},'not_found'),(503,{},'unavailable'),
    (302,{},'unavailable'),(200,[], 'invalid_response'),(200,{'error':{'message':'secret'}},'invalid_response')])
def test_http_errors(status,payload,kind):
    http=Mock()
    http.get.return_value=response(payload,status)
    with pytest.raises(BookProviderError) as caught:
        GoogleBooksAPI(http=http).search_volumes('test')
    assert caught.value.kind==kind
    assert 'secret' not in str(caught.value)


def test_non_json_response():
    http=Mock()
    http.get.return_value=Mock(status_code=200)
    http.get.return_value.json.side_effect=ValueError('invalid json')
    with pytest.raises(BookProviderError) as caught:
        GoogleBooksAPI(http=http).search_volumes('test')
    assert caught.value.kind=='invalid_response'


@pytest.mark.parametrize('source_id',['','../secret','https://evil.invalid', 'x'*101])
def test_invalid_ids_never_reach_network(source_id):
    http=Mock()
    with pytest.raises(BookProviderError):
        GoogleBooksAPI(http=http).get_volume(source_id)
    http.get.assert_not_called()


@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'adapter-test','DATABASE':str(tmp_path/'adapter.sqlite3'),
                    'GOOGLE_BOOKS_API_KEY':'server-only-secret'})
    with app.app_context():
        init_db()
        seed_demo(get_db())
        prepare_demo_accounts(get_db())
    return app


def csrf(client,path='/giris'):
    return re.search(rb'name="csrf_token" value="([^"]+)"',client.get(path).data).group(1).decode()


def login(app,role='admin'):
    client=app.test_client()
    client.post('/giris',data={'csrf_token':csrf(client),'username':'demo_yonetici' if role=='admin' else 'demo_uye',
                             'password':DEMO_ADMIN_PASSWORD if role=='admin' else DEMO_MEMBER_PASSWORD})
    return client


@pytest.fixture
def fake_http(monkeypatch):
    http=Mock()
    http.get.side_effect=lambda url,**kwargs: response({'items':[volume()],'totalItems':1} if url.endswith('/volumes') else volume())
    monkeypatch.setattr('routes.google_books.GoogleBooksAPI',lambda key: GoogleBooksAPI(key,http=http))
    return http


def test_search_preview_edit_factory_and_sqlite(app,fake_http,monkeypatch):
    client=login(app)
    result=client.post('/kitaplar/google',data={'csrf_token':csrf(client,'/kitaplar/google'),'title':'Dış'})
    assert result.status_code==200
    assert 'Dış Kaynak Kitabı'.encode() in result.data and b'<img' in result.data
    assert b'server-only-secret' not in result.data
    preview=client.post('/kitaplar/google/aktar',data={'csrf_token':csrf(client,'/kitaplar'),'source_id':'test_volume-1'})
    assert preview.status_code==200 and b'action="/kitaplar/ekle"' in preview.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM books').fetchone()[0]==2
    from patterns.factory_method import PhysicalBookCreator
    factory_calls=[]
    class TrackingCreator(PhysicalBookCreator):
        def create_book(self,**data):
            factory_calls.append(data['title'])
            return super().create_book(**data)
    monkeypatch.setitem(book_service.CREATORS,'physical',TrackingCreator)
    draft=GoogleBooksAdapter(GoogleBooksAPI()).adapt(volume()).to_form()
    draft.update(title='Düzeltilmiş Başlık',shelf_location='C-01',csrf_token=csrf(client,'/kitaplar'))
    assert client.post('/kitaplar/ekle',data=draft).status_code==302
    assert factory_calls==['Düzeltilmiş Başlık']
    with app.app_context():
        row=get_db().execute("SELECT id FROM books WHERE isbn='9780306406157'").fetchone()
        book=book_service.get_book(row['id'])
        assert isinstance(book,PhysicalBook) and book.title=='Düzeltilmiş Başlık'
    assert client.post('/kitaplar/ekle',data=draft).status_code==422


def test_import_as_ebook_and_equivalent_isbn_duplicate(app,fake_http):
    with app.app_context():
        data=GoogleBooksAdapter(GoogleBooksAPI()).adapt(volume()).to_form()
        data.update(isbn='0306406152',book_type='ebook',file_url='https://example.invalid/book.pdf')
        assert isinstance(book_service.save_book(data,1),EBook)
        data['isbn']='9780306406157'
        with pytest.raises(book_service.BookValidationError):
            book_service.save_book(data,1)


@pytest.mark.parametrize('route',['/kitaplar/google','/kitaplar/google/aktar'])
def test_permissions_and_csrf(app,fake_http,route):
    member=login(app,'member')
    assert member.post(route,data={'csrf_token':csrf(member,'/kitaplar'),'source_id':'test_volume-1','title':'test'}).status_code==403
    assert app.test_client().get('/kitaplar/google').status_code==302
    admin=login(app)
    assert admin.post(route,data={'title':'test','source_id':'test_volume-1'}).status_code==400
    fake_http.get.assert_not_called()


def test_api_failure_ui_no_database_write(app,fake_http,monkeypatch):
    fake_http.get.side_effect=requests.Timeout('server-only-secret')
    monkeypatch.setattr(requests, 'get', Mock(side_effect=requests.ConnectionError()))
    client=login(app)
    result=client.post('/kitaplar/google',data={'csrf_token':csrf(client,'/kitaplar/google'),'title':'test'})
    assert result.status_code==503 and 'zaman aşımına'.encode() in result.data
    assert b'Open Library' in result.data
    assert b'server-only-secret' not in result.data
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM books').fetchone()[0]==2


def test_missing_fields_preview_and_server_validation(app,fake_http):
    fake_http.get.side_effect=None
    fake_http.get.return_value=response({'id':'test_volume-1'})
    client=login(app)
    result=client.post('/kitaplar/google/aktar',data={'csrf_token':csrf(client,'/kitaplar'),'source_id':'test_volume-1'})
    assert result.status_code==200 and 'Başlık eksik'.encode() in result.data
    assert client.post('/kitaplar/ekle',data={'csrf_token':csrf(client,'/kitaplar'),'title':'','author':''}).status_code==422


def test_initial_search_does_not_call_api(app,fake_http):
    client=login(app)
    assert client.get('/kitaplar/google').status_code==200
    fake_http.get.assert_not_called()


def test_empty_search_and_invalid_selection_do_not_call_api(app,fake_http):
    client=login(app)
    result=client.post('/kitaplar/google',data={'csrf_token':csrf(client,'/kitaplar/google')})
    assert result.status_code==422
    result=client.post('/kitaplar/google/aktar',data={'csrf_token':csrf(client,'/kitaplar'),'source_id':'../bad'})
    assert result.status_code==422
    fake_http.get.assert_not_called()


def test_external_html_is_escaped(app,fake_http):
    item=volume()
    item['volumeInfo']['title']='<script>alert(1)</script>'
    item['volumeInfo']['imageLinks']['thumbnail']='https://evil.invalid/cover'
    fake_http.get.side_effect=None
    fake_http.get.return_value=response({'items':[item],'totalItems':1})
    client=login(app)
    result=client.post('/kitaplar/google',data={'csrf_token':csrf(client,'/kitaplar/google'),'title':'test'})
    assert result.status_code==200
    assert b'<script>alert(1)</script>' not in result.data
    assert b'&lt;script&gt;' in result.data
    assert b'https://evil.invalid' not in result.data
