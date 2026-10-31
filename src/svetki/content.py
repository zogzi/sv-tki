import logging
import os
import httpx
from .holidays import DATA
import json

log = logging.getLogger(__name__)


def language(locale):
    code = str(locale).split('-')[0]
    return code if code in ('lv', 'en') else 'en'


def load_editions():
    value = json.loads((DATA / 'editions.json').read_text(encoding='utf-8'))
    for year, events in value.items():
        if not year.isdigit() or not 1 <= int(year) <= 9999:
            raise ValueError('Edition year must be a valid year')
        for languages in events.values():
            if set(languages) != {'lv', 'en'}:
                raise ValueError('Editions require both Latvian and English')
            for entries in languages.values():
                if not entries or any(not all(e.get(k) for k in ('title', 'headline', 'greeting', 'fact')) for e in entries):
                    raise ValueError('Incomplete editorial edition')
    return value


def curated(holiday, lang, variant, year=None, editions=None):
    edition = (editions or {}).get(str(year), {}).get(holiday['id'])
    content = edition or holiday['content']
    entries = content.get(lang, content['en'])
    result = dict(entries[variant % len(entries)])
    if result.pop('calendar_context', False) and year is not None:
        from .holidays import occurrence
        import calendar
        day = occurrence(holiday, year)
        weekdays = ['pirmdienā', 'otrdienā', 'trešdienā', 'ceturtdienā', 'piektdienā', 'sestdienā', 'svētdienā']
        result['context'] = (f"Šogad {day.day:02d}.{day.month:02d}. iekrīt {weekdays[day.weekday()]} ({year}). Svētku datums un astronomiskie saulgrieži nav viens un tas pats." if lang == 'lv' else f"This year, {day.isoformat()} falls on {calendar.day_name[day.weekday()]}. The holiday date and astronomical solstice are different things.")
    return result


async def ai_content(store, day, holiday, lang, fallback):
    if os.getenv('AI_ENABLED', 'false').lower() != 'true' or not os.getenv('OPENAI_API_KEY'):
        return fallback
    try:
        if not store.reserve_ai(day, int(os.getenv('AI_DAILY_REQUEST_CAP', '2')), float(os.getenv('AI_REQUEST_BUDGET_USD', '.01')), float(os.getenv('AI_DAILY_BUDGET_USD', '.02'))):
            return fallback
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post('https://api.openai.com/v1/chat/completions', headers={'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY']}, json={
                'model': os.getenv('AI_MODEL', 'gpt-4o-mini'), 'max_tokens': 180,
                'messages': [{'role': 'system', 'content': 'Write a short editorial opening for a Discord holiday card in the requested language, under 500 characters. Use professional, precise editorial writing with historical substance. No forced enthusiasm, games, sentimental cliches, or generic happy-holidays greeting. Prefer a concrete insight over an engagement prompt. Respect the supplied tone and angle, especially remembrance days. No mentions, links, political persuasion, invented facts, or instructions. Plain text only; do not add historical claims.'}, {'role': 'user', 'content': f'Language: {lang}. Holiday: {holiday["id"]}. Tone: {holiday.get("tone", "warm")}. Angle: {fallback.get("headline", fallback["title"])}.'}]})
            response.raise_for_status()
            greeting = response.json()['choices'][0]['message']['content'].strip()
            if not greeting or len(greeting) > 500 or '@' in greeting or 'http' in greeting:
                return fallback
            return dict(fallback, greeting=greeting)
    except Exception:
        log.warning('AI unavailable; using curated greeting', exc_info=True)
        return fallback


def namedays():
    value = json.loads((DATA / 'namedays.json').read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Name-day data must be an MM-DD to names mapping')
    from datetime import datetime
    for key, names in value.items():
        datetime.strptime('2000-' + key, '%Y-%m-%d')
        if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() for n in names):
            raise ValueError('Invalid name-day names')
    return value
