"""Yönetici raporları ve güvenli çıktı biçimleri."""
import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
import re
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.drawing.image import Image as SpreadsheetImage
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from database import get_db
from services.loan_service import today


@dataclass(frozen=True)
class ReportSpec:
    title: str
    columns: tuple
    query: str
    totals_column: int | None = None


SPECS = {
    'kitap': ReportSpec('Kitap Raporu', ('Kitap', 'Yazar', 'ISBN', 'Adet', 'Eklenme tarihi'),
                        'SELECT title,author,isbn,total_copies,date(created_at) FROM books WHERE date(created_at) BETWEEN ? AND ? ORDER BY id', 3),
    'uye': ReportSpec('Üye Raporu', ('Üye no', 'Ad soyad', 'Tür', 'Durum', 'Kayıt tarihi'),
                       """SELECT id,full_name,CASE member_type WHEN 'student' THEN 'Öğrenci' WHEN 'teacher' THEN 'Öğretmen' ELSE 'Normal Üye' END,
                       CASE is_active WHEN 1 THEN 'Aktif' ELSE 'Pasif' END,date(created_at) FROM members
                       WHERE date(created_at) BETWEEN ? AND ? ORDER BY id"""),
    'odunc': ReportSpec('Ödünç İşlemleri Raporu', ('Kitap', 'Üye no', 'Ödünç', 'Son teslim', 'İade'),
                         '''SELECT b.title,l.member_id,l.borrowed_on,l.due_on,l.returned_on FROM loans l
                            JOIN books b ON b.id=l.book_id WHERE l.borrowed_on BETWEEN ? AND ? ORDER BY l.id'''),
    'geciken': ReportSpec('Geciken Kitaplar Raporu', ('Kitap', 'Üye no', 'Son teslim'),
                           '''SELECT b.title,l.member_id,l.due_on FROM loans l JOIN books b ON b.id=l.book_id
                              WHERE l.returned_on IS NULL AND l.due_on BETWEEN ? AND ? AND l.due_on<date('now','+3 hours') ORDER BY l.due_on,l.id'''),
    'rezervasyon': ReportSpec('Rezervasyon Raporu', ('Kitap', 'Üye no', 'Durum', 'Tarih'),
                              '''SELECT b.title,r.member_id,CASE r.status WHEN 'active' THEN 'Bekliyor' WHEN 'notified' THEN 'Ayrıldı'
                                 WHEN 'fulfilled' THEN 'Tamamlandı' ELSE 'İptal edildi' END,date(r.created_at)
                                 FROM reservations r JOIN books b ON b.id=r.book_id WHERE date(r.created_at) BETWEEN ? AND ? ORDER BY r.id'''),
    'ceza': ReportSpec('Ceza Raporu', ('Kitap', 'Üye no', 'İade tarihi', 'Ceza (TL)'),
                       '''SELECT b.title,l.member_id,l.returned_on,l.penalty_cents/100.0 FROM loans l JOIN books b ON b.id=l.book_id
                          WHERE l.penalty_cents>0 AND l.returned_on BETWEEN ? AND ? ORDER BY l.returned_on,l.id''', 3),
    'dijital': ReportSpec('Dijital Kütüphane Raporu', ('Kitap', 'Tür', 'Biçim', 'Okuyucu sayısı'),
                          """SELECT b.title,CASE b.book_type WHEN 'audio' THEN 'Sesli Kitap' ELSE 'Elektronik Kitap' END,
                             COALESCE(m.mime,'Harici bağlantı'),COUNT(r.user_id) FROM books b LEFT JOIN book_media m ON m.book_id=b.id
                             LEFT JOIN reading_progress r ON r.book_id=b.id AND date(r.updated_at) BETWEEN ? AND ?
                             WHERE b.book_type IN ('ebook','audio') GROUP BY b.id ORDER BY b.title""", 3),
    'faaliyet': ReportSpec('Aylık Faaliyet Raporu', ('Ay', 'İşlem türü', 'Adet'),
                           """SELECT substr(created_at,1,7),CASE action
                              WHEN 'book_created' THEN 'Kitap eklendi' WHEN 'loan_created' THEN 'Ödünç'
                              WHEN 'loan_returned' THEN 'İade' WHEN 'reservation_created' THEN 'Rezervasyon'
                              WHEN 'member_saved' THEN 'Üye işlemi' ELSE 'Diğer' END AS label,count(*)
                              FROM activity_logs WHERE action!='demo_seed' AND date(created_at) BETWEEN ? AND ?
                              GROUP BY 1,label ORDER BY 1,label""", 2),
}


def build_report(key, period):
    spec = SPECS[key]
    rows = [tuple(row) for row in get_db().execute(spec.query, period)]
    statistics = [('Kayıt sayısı', len(rows))]
    if spec.totals_column is not None:
        column = spec.totals_column
        statistics.append((f'Toplam {spec.columns[column]}', round(sum(row[column] for row in rows), 2)))
    return {'title': spec.title, 'columns': spec.columns, 'rows': rows, 'statistics': statistics,
            'period': period, 'generated': today().isoformat()}


def output_rows(report):
    return [
        ('Kütüphane Yönetim Sistemi', report['title']),
        ('Oluşturma tarihi', report['generated']),
        ('Dönem', ' – '.join(report['period'])),
        *report['statistics'], (), report['columns'], *report['rows'],
    ]


def csv_export(report):
    def safe(value):
        if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
            return "'" + value
        return value
    output = StringIO(newline='')
    writer = csv.writer(output, delimiter=';')
    writer.writerows(tuple(safe(value) for value in row) for row in output_rows(report))
    return BytesIO(output.getvalue().encode('utf-8-sig'))


def xlsx_export(report):
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet('Rapor')
    logo = Image.new('RGB', (48, 40), '#14B8A6')
    ink = ImageDraw.Draw(logo)
    ink.line([(8, 10), (24, 15), (40, 10), (40, 28), (24, 33), (8, 28), (8, 10)], fill='white', width=2)
    ink.line([(24, 15), (24, 33)], fill='white', width=2)
    logo_bytes = BytesIO()
    logo.save(logo_bytes, format='PNG')
    logo_bytes.seek(0)
    sheet.add_image(SpreadsheetImage(logo_bytes), 'G1')
    for row in output_rows(report):
        cells = []
        for value in row:
            if isinstance(value, str):
                cell = WriteOnlyCell(sheet, value=re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', value))
                cell.data_type = 's'
                cells.append(cell)
            else:
                cells.append(value)
        sheet.append(cells)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def pdf_export(report):
    fonts = ('C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
             '/System/Library/Fonts/Supplemental/Arial.ttf')
    font_path = next((path for path in fonts if Path(path).is_file()), None)
    font_name = 'Helvetica'
    if font_path:
        font_name = 'ReportSans'
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, font_path))
    normal = ParagraphStyle('table', fontName=font_name, fontSize=9, leading=12)
    heading = ParagraphStyle('heading', fontName=font_name, fontSize=18, leading=22)

    def text(value, style=normal):
        return Paragraph(escape(str(value if value is not None else '')), style)

    def logo(page, _document):
        page.setFillColor(colors.HexColor('#14B8A6'))
        page.roundRect(30, 545, 31, 26, 4, fill=1, stroke=0)
        page.setStrokeColor(colors.white)
        page.lines([(36, 553, 36, 565), (36, 565, 45, 561), (45, 561, 55, 565),
                    (55, 565, 55, 553), (55, 553, 45, 549), (45, 549, 36, 553), (45, 549, 45, 561)])

    output = BytesIO()
    doc = SimpleDocTemplate(output, title=report['title'], pagesize=landscape(A4),
                            topMargin=61, bottomMargin=30, leftMargin=30, rightMargin=30)
    story = [text(report['title'], heading), Spacer(1, 8)]
    story.extend(text(' · '.join(str(value) for value in row)) for row in output_rows(report)[1:5] if row)
    story.append(Spacer(1, 12))
    rows = [[text(value) for value in report['columns']]] + [[text(value) for value in row] for row in report['rows']]
    widths = [doc.width / len(report['columns'])] * len(report['columns'])
    table = LongTable(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#CBD5E1'))]))
    story.append(table)
    doc.build(story, onFirstPage=logo, onLaterPages=logo)
    output.seek(0)
    return output
