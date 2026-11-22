"""Üye türüne göre değiştirilebilir gecikme cezası algoritmaları."""
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal


def validate_days(days_late):
    if type(days_late) is not int or days_late < 0:
        raise ValueError('Gecikme günü negatif olmayan bir tamsayı olmalıdır.')


class PenaltyStrategy(ABC):
    @abstractmethod
    def calculate(self, days_late: int) -> Decimal:
        """TL cinsinden, kesin ondalıklı ceza tutarı."""


class StudentPenalty(PenaltyStrategy):
    def calculate(self, days_late):
        validate_days(days_late)
        return Decimal('2.00') * days_late


class TeacherPenalty(PenaltyStrategy):
    def calculate(self, days_late):
        validate_days(days_late)
        return Decimal('1.00') * days_late


class StandardPenalty(PenaltyStrategy):
    def calculate(self, days_late):
        validate_days(days_late)
        return Decimal('5.00') * days_late


class PenaltyCalculator:
    def __init__(self, strategy: PenaltyStrategy):
        self.set_strategy(strategy)

    def set_strategy(self, strategy: PenaltyStrategy):
        if not isinstance(strategy, PenaltyStrategy):
            raise TypeError('Geçerli bir ceza stratejisi gerekir.')
        self._strategy = strategy

    @staticmethod
    def overdue_days(due_on: date, returned_on: date) -> int:
        if type(due_on) is not date or type(returned_on) is not date:
            raise TypeError('Son teslim ve iade için tarih nesnesi gerekir.')
        return max(0, (returned_on - due_on).days)

    def calculate(self, due_on: date, returned_on: date) -> Decimal:
        return self._strategy.calculate(self.overdue_days(due_on, returned_on))


PENALTY_STRATEGIES = {'student':StudentPenalty, 'teacher':TeacherPenalty, 'standard':StandardPenalty}
