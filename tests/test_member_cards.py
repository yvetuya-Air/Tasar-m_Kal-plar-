"""QR kartı, dosya çıktıları ve yetkili üye tanıma."""
from database import get_db
from test_adapter import app, csrf, login


def test_card_download_and_private_opaque_lookup(app):
    member = login(app, 'member')
    admin = login(app)
    with app.app_context():
        row = get_db().execute('SELECT m.full_name,m.id,c.token FROM members m JOIN member_cards c ON c.member_id=m.id WHERE m.user_id IS NOT NULL').fetchone()
    assert row['token'].encode() not in member.get('/uye-kartim').data
    assert member.get('/uye-kartim/qr').data.startswith(b'\x89PNG')
    assert member.get('/uye-kartim/indir/png').data.startswith(b'\x89PNG')
    assert member.get('/uye-kartim/indir/pdf').data.startswith(b'%PDF-')
    assert admin.get('/uye-kartim/indir/png').status_code == 403
    token = csrf(admin, '/uye-tani')
    for value in ('KYS:' + row['token'], str(row['id'])):
        result = admin.post('/uye-tani', data={'csrf_token': token, 'identifier': value})
        assert result.status_code == 200
        assert row['full_name'].encode() in result.data
        assert f"member_id={row['id']}".encode() in result.data
    assert member.post('/uye-tani', data={'csrf_token': csrf(member, '/uye-kartim'),
                                         'identifier': str(row['id'])}).status_code == 403
