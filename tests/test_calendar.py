from datetime import date
import pytest
from svetki.holidays import easter, occurrence, today, upcoming, load_holidays

@pytest.mark.parametrize('year,expected', [(2024,date(2024,3,31)),(2025,date(2025,4,20)),(2026,date(2026,4,5)),(2000,date(2000,4,23)),(2038,date(2038,4,25))])
def test_easter(year, expected):
    assert easter(year) == expected

@pytest.mark.parametrize('year,day',[(2024,12),(2025,11),(2026,10)])
def test_mothers_day(year,day):
    h = next(h for h in load_holidays() if h['id']=='mothers')
    assert occurrence(h,year) == date(year,5,day)

def test_relative():
    holidays = load_holidays()
    assert {h['id'] for h in today(date(2026,4,3),holidays)} == {'good_friday'}
    assert 'easter_monday' in {h['id'] for h in today(date(2026,4,6),holidays)}

def test_rollover():
    result=upcoming(date(2026,12,31),load_holidays())
    assert len(result)==5
    assert result[0][0]==date(2027,1,1)
    assert result[0][1]['id']=='new_year'

def test_content():
    holidays=load_holidays()
    assert len({h['id'] for h in holidays})==len(holidays)
    assert sum(len(h['content']['lv'])>=5 and len(h['content']['en'])>=5 for h in holidays)>=10
    for h in holidays:
        for lang in ('lv','en'):
            for entry in h['content'][lang]:
                assert all(entry.get(k) for k in ('title','greeting','fact'))
