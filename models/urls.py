"""Kitap adresleri için ortak HTTP/HTTPS biçim doğrulaması."""
from urllib.parse import urlsplit


def http_url_parts(value, max_length=2000):
    if not isinstance(value,str) or not value or len(value)>max_length:
        return None
    if '\\' in value or any(c.isspace() or ord(c)<32 or ord(c)==127 for c in value):
        return None
    try:
        parts=urlsplit(value)
        if parts.scheme not in ('http','https') or not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None
        if parts.port is not None and not 1<=parts.port<=65535:
            return None
        return parts
    except ValueError:
        return None
