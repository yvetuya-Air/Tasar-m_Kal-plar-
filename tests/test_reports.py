"""Gerçek rapor verisi, dışa aktarma ve erişim denetimi."""
from io import BytesIO

from openpyxl import load_workbook

from database import get_db
from test_adapter import app, login


def test_report_outputs_and_unsafe_excel_cells(app):
    admin = login(app)
    with app.app_context(), get_db() as db:
        db.execute("UPDATE books SET title='=1+1' WHERE id=1")
    page = admin.get('/raporlar?report=kitap')
    assert page.status_code == 200 and b'=1+1' in page.data
    report = admin.get('/raporlar?report=kitap&format=pdf')
    assert report.status_code == 200 and report.data.startswith(b'%PDF-')
    workbook = load_workbook(BytesIO(admin.get('/raporlar?report=kitap&format=xlsx').data))
    assert any(cell.value == '=1+1' and cell.data_type == 's' for row in workbook.active.iter_rows() for cell in row)
    assert b"'=1+1" in admin.get('/raporlar?report=kitap&format=csv').data
    assert login(app, 'member').get('/raporlar?format=pdf').status_code == 403


def test_report_queries_all_render(app):
    admin = login(app)
    for kind in ('kitap', 'uye', 'odunc', 'geciken', 'rezervasyon', 'ceza', 'dijital', 'faaliyet'):
        assert admin.get('/raporlar', query_string={'report': kind}).status_code == 200
