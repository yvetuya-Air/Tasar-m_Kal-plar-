"""ISBN doğrulama ve eşdeğer baskı tanımlayıcıları."""
def normalize_isbn(value):
    return value.replace('-', '').replace(' ', '').upper()


def valid_isbn(value):
    if len(value) == 13 and value.isascii() and value.isdigit():
        return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(value)) % 10 == 0
    if len(value) == 10 and value[:9].isascii() and value[:9].isdigit() and (value[-1].isdigit() and value[-1].isascii() or value[-1] == 'X'):
        return sum((10-i) * (10 if c == 'X' else int(c)) for i,c in enumerate(value)) % 11 == 0
    return False


def isbn_variants(value):
    if not value:
        return ()
    if len(value) == 10:
        prefix = '978' + value[:9]
        check = (-sum(int(c)*(1 if i%2==0 else 3) for i,c in enumerate(prefix))) % 10
        return (value, prefix+str(check))
    if value.startswith('978'):
        prefix = value[3:12]
        check = (-sum((10-i)*int(c) for i,c in enumerate(prefix))) % 11
        return (value, prefix+('X' if check==10 else str(check)))
    return (value,)
