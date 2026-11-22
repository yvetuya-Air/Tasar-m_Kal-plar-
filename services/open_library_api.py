"""Open Library arama ve eser ayrıntısı için HTTP istemcisi."""
import re

import requests

from services.google_books_api import BookProviderError, retry_delay


WORK_ID = re.compile(r'OL[0-9]{1,12}W')


class OpenLibraryAPI:
    BASE_URL = 'https://openlibrary.org'
    SEARCH_FIELDS = (
        'key,title,author_name,cover_i,first_publish_year,'
        'editions,editions.title,editions.isbn,editions.publisher,'
        'editions.publish_year,editions.language,editions.cover_i'
    )

    def __init__(self, http=None):
        self.http = http if http is not None else requests

    def _request(self, path, params=None):
        try:
            response = self.http.get(self.BASE_URL + path, params=params,
                                     timeout=(3, 8), allow_redirects=False)
        except requests.Timeout:
            raise BookProviderError('Open Library isteği zaman aşımına uğradı.', 'timeout') from None
        except requests.RequestException:
            raise BookProviderError('Open Library bağlantısı kurulamadı.', 'connection') from None
        if response.status_code == 429:
            raise BookProviderError('Open Library istek sınırına ulaşıldı.', 'quota', retry_delay(response))
        if response.status_code == 404:
            raise BookProviderError('Seçilen Open Library kaydı bulunamadı.', 'not_found')
        if response.status_code != 200:
            raise BookProviderError('Open Library şu anda yanıt veremiyor.')
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            raise BookProviderError('Open Library geçersiz bir yanıt döndürdü.', 'invalid_response')
        return payload

    def search_works(self, query, *, page=1, limit=12):
        return self._request('/search.json', {
            'q': query, 'page': page, 'limit': limit, 'fields': self.SEARCH_FIELDS,
        })

    def get_work(self, work_id):
        if not WORK_ID.fullmatch(work_id):
            raise BookProviderError('Geçersiz Open Library kayıt kimliği.', 'invalid_id')
        return self._request(f'/works/{work_id}.json')
