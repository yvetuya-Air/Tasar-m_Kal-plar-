"""Harici kataloglar için süreç içi, süreli ve sınırlı önbellek."""
from collections import OrderedDict
from threading import Lock
from time import monotonic

from services.google_books_api import BookProviderError


class CatalogCache:
    def __init__(self, ttl=600, capacity=256, clock=monotonic):
        self.ttl = ttl
        self.capacity = capacity
        self.clock = clock
        self.entries = OrderedDict()
        self.lock = Lock()
        self.quota_until = 0
        self.quota_error = None

    def load(self, key, fetch):
        # Aynı sağlayıcıya eşzamanlı gelen istekler ortak sonucu kullanır.
        with self.lock:
            now = self.clock()
            cached = self.entries.get(key)
            if cached is not None:
                expires, result = cached
                if expires > now:
                    self.entries.move_to_end(key)
                    return result
                del self.entries[key]
            if self.quota_until > now:
                raise BookProviderError(self.quota_error, 'quota')
            try:
                result = fetch()
            except BookProviderError as error:
                if error.kind == 'quota':
                    self.quota_until = self.clock() + (error.retry_after or 60)
                    self.quota_error = str(error)
                raise
            self.entries[key] = (self.clock() + self.ttl, result)
            if len(self.entries) > self.capacity:
                self.entries.popitem(last=False)
            return result
