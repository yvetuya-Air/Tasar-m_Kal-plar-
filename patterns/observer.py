"""Observer: kullanılabilirlik olayı abonelere ortak arayüzle iletilir."""
from abc import ABC, abstractmethod


class Observer(ABC):
    @abstractmethod
    def update(self, book_id, title):
        """Konu değiştiğinde çağrılır."""


class Subject(ABC):
    @abstractmethod
    def attach(self, observer: Observer):
        pass

    @abstractmethod
    def detach(self, observer: Observer):
        pass

    @abstractmethod
    def notify(self):
        pass


class BookAvailabilitySubject(Subject):
    def __init__(self, book_id, title):
        self.book_id = book_id
        self.title = title
        self._observers = []

    def attach(self, observer):
        if not isinstance(observer, Observer):
            raise TypeError('Geçerli bir gözlemci gerekir.')
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self):
        # Güncelleme sırasında abonelik değişse bile mevcut yayın kararlıdır.
        return sum(bool(observer.update(self.book_id,self.title)) for observer in tuple(self._observers))


class MemberObserver(Observer):
    def __init__(self, reservation_id, notification_service):
        self.reservation_id = reservation_id
        self.notification_service = notification_service

    def update(self, book_id, title):
        return self.notification_service.notify_reserved_member(self.reservation_id,book_id,title)


class NotificationEventSubject(BookAvailabilitySubject):
    """Aynı abone yaşam döngüsünü genel bildirim olaylarına uygular."""
    def __init__(self, event_key, message):
        super().__init__(event_key, message)


class MemberEventObserver(Observer):
    def __init__(self, member_id, kind, service):
        self.member_id = member_id
        self.kind = kind
        self.service = service

    def update(self, event_key, message):
        return self.service.store_event(self.member_id, self.kind, event_key, message)
