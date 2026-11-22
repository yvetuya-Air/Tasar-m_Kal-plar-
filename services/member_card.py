"""Opak QR kimliği ve kütüphane kartı çıktıları."""
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont
import qrcode

from database import get_db

TYPES = {'student': 'Öğrenci', 'teacher': 'Öğretmen', 'standard': 'Normal Üye'}
PREFIX = 'KYS:'


def card_for_user(user_id):
    return get_db().execute(
        'SELECT m.*,c.token FROM members m JOIN member_cards c ON c.member_id=m.id WHERE m.user_id=?',
        (user_id,),
    ).fetchone()


def find_card(value):
    query = value.strip()
    db = get_db()
    if re.fullmatch(r'KYS:[a-f0-9]{48}', query):
        return db.execute(
            'SELECT m.* FROM member_cards c JOIN members m ON m.id=c.member_id WHERE c.token=?',
            (query.removeprefix(PREFIX),),
        ).fetchone()
    if re.fullmatch(r'[0-9]{1,19}', query) and int(query) <= 2**63-1:
        return db.execute('SELECT * FROM members WHERE id=?', (int(query),)).fetchone()
    return None


def qr_image(card):
    return qrcode.make(PREFIX + card['token']).convert('RGB')


def card_image(card):
    image = Image.new('RGB', (1000, 560), '#0f172a')
    draw = ImageDraw.Draw(image)
    font_path = next((str(path) for file in (
        'C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
    ) if (path := Path(file)).is_file()), None)
    def font(size):
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default(size)
    draw.rounded_rectangle((55, 55, 123, 123), radius=12, fill='#14b8a6')
    draw.line([(70, 75), (89, 82), (108, 75), (108, 103), (89, 110), (70, 103), (70, 75)], fill='white', width=4)
    draw.line([(89, 82), (89, 110)], fill='white', width=4)
    draw.text((146, 72), 'Kütüphane Üye Kartı', fill='#f1f5f9', font=font(36))
    font_name = font(42)
    name = card['full_name']
    if draw.textlength(name, font=font_name) > 565:
        while name and draw.textlength(name + '…', font=font_name) > 565:
            name = name[:-1]
        name += '…'
    draw.text((55, 180), name, fill='white', font=font_name)
    for index, line in enumerate((
        f"Üye numarası: {card['id']}", f"Üye türü: {TYPES[card['member_type']]}",
        f"Kayıt tarihi: {card['created_at'][:10]}", f"Durum: {'Aktif' if card['is_active'] else 'Pasif'}",
    )):
        draw.text((55, 267 + 49 * index), line, fill='#e2e8f0', font=font(26))
    image.paste(qr_image(card).resize((280, 280), Image.Resampling.NEAREST), (666, 166))
    return image


def image_file(image, file_format):
    output = BytesIO()
    image.save(output, format=file_format)
    output.seek(0)
    return output
