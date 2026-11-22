"""Paylaşılan sayfalama, SQL araması ve kayıt kimliği doğrulamaları."""
MAX_RECORD_ID = 2**63 - 1


def record_id(value, label='Kayıt'):
    try:
        text = str(value).strip()
        if not text.isascii() or not text.isdecimal() or len(text)>19:
            raise ValueError
        result = int(text)
        if not 1 <= result <= MAX_RECORD_ID:
            raise ValueError
        return result
    except (ValueError,TypeError):
        raise ValueError(f'{label} kimliği geçersiz.') from None


def requested_page(value):
    try:
        return max(1,int(value))
    except (ValueError,TypeError):
        return 1


def escaped_like(value):
    return '%'+value.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
