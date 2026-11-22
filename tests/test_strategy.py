"""Strategy algoritmaları, bağlam değişimi ve tarih sınırları."""
from datetime import date, datetime
from decimal import Decimal
import pytest
from patterns.strategy import PenaltyStrategy, StudentPenalty, TeacherPenalty, StandardPenalty, PenaltyCalculator


@pytest.mark.parametrize('strategy,rate',[(StudentPenalty,2),(TeacherPenalty,1),(StandardPenalty,5)])
@pytest.mark.parametrize('days',[0,1,5,365])
def test_daily_rates(strategy,rate,days):
    result=strategy().calculate(days)
    assert isinstance(result,Decimal)
    assert result==Decimal(rate)*days


def test_abstract_strategy():
    with pytest.raises(TypeError):
        PenaltyStrategy()


def test_change_strategy_on_same_calculator():
    calculator=PenaltyCalculator(StudentPenalty())
    due,returned=date(2026,11,10),date(2026,11,15)
    assert calculator.calculate(due,returned)==Decimal('10.00')
    calculator.set_strategy(TeacherPenalty())
    assert calculator.calculate(due,returned)==Decimal('5.00')
    calculator.set_strategy(StandardPenalty())
    assert calculator.calculate(due,returned)==Decimal('25.00')


@pytest.mark.parametrize('returned',[date(2026,11,9),date(2026,11,10)])
def test_no_penalty_before_or_on_due_date(returned):
    assert PenaltyCalculator(StandardPenalty()).calculate(date(2026,11,10),returned)==0


def test_calendar_days_across_leap_day():
    calculator=PenaltyCalculator(StudentPenalty())
    assert calculator.overdue_days(date(2024,2,28),date(2024,3,1))==2
    assert calculator.calculate(date(2024,2,28),date(2024,3,1))==4


@pytest.mark.parametrize('days',[-1,1.5,True,'5'])
def test_invalid_days(days):
    with pytest.raises(ValueError):
        StudentPenalty().calculate(days)


def test_invalid_strategy_and_dates():
    with pytest.raises(TypeError):
        PenaltyCalculator(object())
    with pytest.raises(TypeError):
        PenaltyCalculator(StudentPenalty()).calculate('2026-11-10',date(2026,11,15))
    with pytest.raises(TypeError):
        PenaltyCalculator(StudentPenalty()).calculate(datetime(2026,11,10),date(2026,11,15))


def test_custom_strategy_without_changing_context():
    class FreePenalty(PenaltyStrategy):
        def calculate(self,days_late):
            return Decimal('0.00')
    calculator=PenaltyCalculator(FreePenalty())
    assert calculator.calculate(date(2026,1,1),date(2026,2,1))==0
