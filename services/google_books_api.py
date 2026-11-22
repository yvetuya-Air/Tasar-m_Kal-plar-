"""Google Books HTTP istemcisi; uygulama kitap modelini bilmez."""
import re
import requests


class BookProviderError(RuntimeError):
    def __init__(self, message, kind='unavailable', retry_after=None):
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after


def retry_delay(response):
    value = getattr(response, 'headers', {}).get('Retry-After')
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 9:
        return max(60, int(value))
    return 60


class GoogleBooksAPI:
    BASE_URL = 'https://www.googleapis.com/books/v1/volumes'

    def __init__(self, api_key='', http=None):
        self.api_key = api_key
        self.http = http if http is not None else requests

    def _request(self, suffix='', params=None):
        params = dict(params or {})
        if self.api_key:
            params['key'] = self.api_key
        try:
            response = self.http.get(self.BASE_URL + suffix, params=params, timeout=(3,8), allow_redirects=False)
        except requests.Timeout:
            raise BookProviderError('Google Books isteği zaman aşımına uğradı. Lütfen tekrar deneyin.', 'timeout') from None
        except requests.RequestException:
            raise BookProviderError('Google Books bağlantısı kurulamadı. İnternet bağlantınızı kontrol edin.', 'connection') from None
        try:
            payload = response.json()
        except ValueError:
            payload = None
        api_error = payload.get('error') if isinstance(payload,dict) else None
        reasons = []
        if isinstance(api_error,dict) and isinstance(api_error.get('errors'),list):
            reasons = [item.get('reason') for item in api_error['errors'] if isinstance(item,dict)]
        exhausted = isinstance(api_error, dict) and api_error.get('status') == 'RESOURCE_EXHAUSTED'
        if response.status_code == 429 or (response.status_code == 403 and (exhausted or any(reason in ('quotaExceeded','dailyLimitExceeded','rateLimitExceeded','userRateLimitExceeded') for reason in reasons))):
            raise BookProviderError('Google Books istek kotası veya hız sınırı aşıldı. Daha sonra tekrar deneyin; gerekirse API anahtarınızın kotasını kontrol edin.', 'quota', retry_delay(response))
        if response.status_code in (401,403):
            raise BookProviderError('Google Books erişimi reddetti. API anahtarını ve Books API izinlerini kontrol edin.', 'access')
        if response.status_code == 404:
            raise BookProviderError('Seçilen Google Books kaydı artık bulunamıyor.', 'not_found')
        if response.status_code != 200:
            raise BookProviderError('Google Books şu anda yanıt veremiyor. Daha sonra tekrar deneyin.')
        if not isinstance(payload,dict) or api_error is not None:
            raise BookProviderError('Google Books geçersiz bir yanıt döndürdü.', 'invalid_response')
        return payload

    def search_volumes(self, query, *, start_index=0):
        return self._request(params={'q':query,'maxResults':12,'printType':'books','startIndex':start_index})

    def get_volume(self, volume_id):
        if not isinstance(volume_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',volume_id):
            raise BookProviderError('Geçersiz Google Books kayıt kimliği.', 'invalid_id')
        return self._request('/'+volume_id)
