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


def ai_endpoint():
    """Support compatible providers without coupling runtime to a chat subscription."""
    from urllib.parse import urlsplit
    base = os.getenv('AI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    parsed = urlsplit(base)
    local = parsed.hostname in {'localhost', '127.0.0.1', '::1'}
    if (parsed.scheme != 'https' and not (parsed.scheme == 'http' and local)) or not parsed.hostname:
        raise ValueError('AI_BASE_URL requires HTTPS, or HTTP on loopback for a local model')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('AI_BASE_URL cannot contain credentials, query parameters or fragments')
    return base + '/chat/completions', local


async def ai_content(store, day, holiday, lang, fallback):
    if os.getenv('AI_ENABLED', 'false').lower() != 'true':
        return fallback
    try:
        import hashlib
        endpoint, local = ai_endpoint()
        key = os.getenv('AI_API_KEY') or os.getenv('OPENAI_API_KEY')
        if not key and not local:
            log.warning('AI enabled without an API key; using saved content')
            return fallback
        model = os.getenv('AI_MODEL', 'gpt-4o-mini')
        brief = (DATA / 'editorial_brief.md').read_text(encoding='utf-8')
        # Include the complete authored context: the model must not invent supporting facts.
        context = dict(date=day, timezone='Europe/Riga', language=lang,
                       holiday=holiday['id'], tone=holiday.get('tone', 'warm'), post=fallback)
        user_prompt = json.dumps(context, ensure_ascii=False, sort_keys=True)
        instructions = (brief + '\nReturn only the editorial introduction as plain text, '
                        'under 1500 characters. Do not include mentions or URLs. '
                        'Do not add factual claims beyond the supplied context.')
        fingerprint = hashlib.sha256(json.dumps(
            [endpoint, model, instructions, context], ensure_ascii=False, sort_keys=True,
        ).encode()).hexdigest()
        cached = store.ai_text(day, holiday['id'], lang, fingerprint)
        if cached is not None:
            return dict(fallback, greeting=cached)
        if not store.reserve_ai(day, int(os.getenv('AI_DAILY_REQUEST_CAP', '2')),
                                float(os.getenv('AI_REQUEST_BUDGET_USD', '.01')),
                                float(os.getenv('AI_DAILY_BUDGET_USD', '.02'))):
            return fallback
        headers = {'Authorization': 'Bearer ' + key} if key else {}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(endpoint, headers=headers, json={
                'model': model, 'max_tokens': 350,
                'messages': [{'role': 'system', 'content': instructions},
                             {'role': 'user', 'content': user_prompt}],
            })
            response.raise_for_status()
            greeting = response.json()['choices'][0]['message']['content']
            if not isinstance(greeting, str):
                return fallback
            greeting = greeting.strip()
            if not greeting or len(greeting) > 1500 or '@' in greeting or 'http' in greeting.lower():
                log.warning('Rejected AI introduction; using saved content')
                return fallback
            store.save_ai_text(day, holiday['id'], lang, fingerprint, greeting)
            return dict(fallback, greeting=greeting)
    except Exception:
        log.warning('AI unavailable; using saved content', exc_info=True)
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
