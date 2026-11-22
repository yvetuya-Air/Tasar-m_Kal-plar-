"""Ödünç, ayırma ve ceza politikaları."""
from decimal import Decimal

from database import get_db
from patterns.strategy import PenaltyStrategy, validate_days

MEMBER_TYPES = {'student': 'Öğrenci', 'teacher': 'Öğretmen', 'standard': 'Normal Üye'}
EVENTS = {
    'available': 'Kitap mevcut', 'due': 'İade tarihi yaklaşıyor', 'overdue': 'Gecikmiş kitap',
    'penalty': 'Gecikme cezası', 'reserved': 'Rezervasyon onaylandı',
    'expired': 'Rezervasyon süresi doldu', 'new_book': 'Yeni kitap eklendi', 'membership': 'Üyelik bildirimi',
}
FIELDS = {
    'daily_cents': ('Günlük ceza (kuruş)', 0, 1000000),
    'max_cents': ('Maksimum ceza (kuruş)', 0, 100000000),
    'loan_days': ('Ödünç süresi (gün)', 1, 365),
    'max_books': ('Maksimum kitap sayısı', 1, 1000),
    'renewals': ('Yenileme hakkı', 0, 30),
    'grace_days': ('Gecikme toleransı (gün)', 0, 365),
}


class ConfiguredPenalty(PenaltyStrategy):
    def __init__(self, policy):
        self.policy = policy

    def calculate(self, days_late):
        validate_days(days_late)
        billable_days = max(0, days_late - self.policy['grace_days'])
        return Decimal(min(self.policy['max_cents'], billable_days * self.policy['daily_cents'])) / 100


def configured_policy(member_type):
    return get_db().execute('SELECT * FROM loan_policies WHERE member_type=?', (member_type,)).fetchone()


def display_policy(member_type):
    row = configured_policy(member_type)
    if row:
        return dict(row)
    return {'daily_cents': {'student': 200, 'teacher': 100, 'standard': 500}[member_type],
            'max_cents': 100000000, 'loan_days': 14, 'max_books': 10, 'renewals': 1, 'grace_days': 0}


def hold_hours(db):
    row = db.execute("SELECT value FROM circulation_settings WHERE key='hold_hours'").fetchone()
    return row[0] if row else 48


def update_policies(form, user_id):
    policies = []
    try:
        for member_type in MEMBER_TYPES:
            values = [int(form.get(f'{member_type}_{key}', '')) for key in FIELDS]
            if any(not minimum <= value <= maximum for value, (_, minimum, maximum) in zip(values, FIELDS.values())):
                raise ValueError
            policies.append((member_type, *values))
        hours = int(form.get('hold_hours', ''))
        if not 1 <= hours <= 720:
            raise ValueError
    except ValueError:
        raise ValueError('Politika değerleri gösterilen sınırlar içinde olmalıdır.') from None
    db = get_db()
    with db:
        db.executemany('''INSERT INTO loan_policies VALUES(?,?,?,?,?,?,?)
                          ON CONFLICT(member_type) DO UPDATE SET daily_cents=excluded.daily_cents,
                          max_cents=excluded.max_cents,loan_days=excluded.loan_days,max_books=excluded.max_books,
                          renewals=excluded.renewals,grace_days=excluded.grace_days''', policies)
        db.execute("INSERT INTO circulation_settings VALUES('hold_hours',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (hours,))
        db.execute("INSERT INTO activity_logs(user_id,action,details) VALUES(?,'settings_changed','Ödünç politikaları güncellendi')", (user_id,))
