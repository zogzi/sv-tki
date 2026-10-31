import pytest
from svetki.content import ai_content
from svetki.storage import Store

@pytest.mark.asyncio
async def test_ai_disabled_needs_no_key_or_network(tmp_path,monkeypatch):
    monkeypatch.setenv('AI_ENABLED','false')
    fallback={'greeting':'A curated story'}
    store=Store(tmp_path/'db')
    assert await ai_content(store,'2026-01-01',{'id':'new_year'},'lv',fallback)==fallback
    assert store.db.execute('SELECT count(*) FROM ai').fetchone()[0]==0

@pytest.mark.asyncio
async def test_api_failure_falls_back_and_consumes_reservation(tmp_path,monkeypatch):
    import svetki.content as module
    monkeypatch.setenv('AI_ENABLED','true')
    monkeypatch.setenv('OPENAI_API_KEY','test-only-not-a-real-key')
    monkeypatch.setenv('AI_DAILY_REQUEST_CAP','1')
    monkeypatch.setenv('AI_REQUEST_BUDGET_USD','0.01')
    monkeypatch.setenv('AI_DAILY_BUDGET_USD','0.02')
    class Offline:
        async def __aenter__(self):
            raise TimeoutError('simulated API outage')
        async def __aexit__(self,*args):
            return False
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs: Offline())
    store=Store(tmp_path/'db')
    fallback={'greeting':'Curated story','title':'Holiday'}
    assert await ai_content(store,'2026-01-01',{'id':'new_year'},'lv',fallback)==fallback
    assert await ai_content(store,'2026-01-01',{'id':'new_year'},'lv',fallback)==fallback
    assert store.db.execute('SELECT calls,reserved FROM ai').fetchone()==(1,.01)

@pytest.mark.asyncio
async def test_provider_date_context_and_persistent_cache(tmp_path, monkeypatch):
    import json
    import svetki.content as module
    monkeypatch.setenv('AI_ENABLED', 'true')
    monkeypatch.setenv('AI_API_KEY', 'test-only-not-a-real-key')
    monkeypatch.setenv('AI_BASE_URL', 'https://provider.example/v1')
    monkeypatch.setenv('AI_MODEL', 'compatible-test-model')
    monkeypatch.setenv('AI_DAILY_REQUEST_CAP', '5')
    requests = []

    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'choices': [{'message': {'content': 'A grounded editorial introduction.'}}]}

    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, endpoint, **kwargs):
            requests.append((endpoint, kwargs))
            return Response()

    monkeypatch.setattr(module.httpx, 'AsyncClient', lambda **kwargs: Client())
    path = tmp_path / 'db'
    store = Store(path)
    fallback = {'title': 'Līgo', 'greeting': 'Saved introduction', 'fact': 'Supplied historical context'}
    holiday = {'id': 'ligo', 'tone': 'reflective'}
    first = await ai_content(store, '2029-06-23', holiday, 'lv', fallback)
    store.db.close()
    store = Store(path)
    second = await ai_content(store, '2029-06-23', holiday, 'lv', fallback)
    assert first == second == dict(fallback, greeting='A grounded editorial introduction.')
    assert len(requests) == 1
    endpoint, request = requests[0]
    assert endpoint == 'https://provider.example/v1/chat/completions'
    assert request['json']['model'] == 'compatible-test-model'
    context = json.loads(request['json']['messages'][1]['content'])
    assert context['date'] == '2029-06-23'
    assert context['post']['fact'] == fallback['fact']
    assert 'no web search' in ' '.join(request['json']['messages'][0]['content'].split())
    assert store.db.execute('SELECT calls FROM ai').fetchone()[0] == 1
    # Owner edits invalidate the cache, instead of silently reusing an old version.
    changed = dict(fallback, greeting='An owner revision')
    await ai_content(store, '2029-06-23', holiday, 'lv', changed)
    assert len(requests) == 2

@pytest.mark.parametrize('endpoint', [
    'http://provider.example/v1',
    'https://user:password@provider.example/v1',
    'https://provider.example/v1?api_key=test',
    'https://provider.example/v1#fragment',
])
def test_unsafe_provider_configuration_rejected(monkeypatch, endpoint):
    from svetki.content import ai_endpoint
    monkeypatch.setenv('AI_BASE_URL', endpoint)
    with pytest.raises(ValueError):
        ai_endpoint()

@pytest.mark.asyncio
async def test_local_compatible_model_needs_no_subscription_or_key(tmp_path, monkeypatch):
    import svetki.content as module
    monkeypatch.setenv('AI_ENABLED', 'true')
    monkeypatch.setenv('AI_BASE_URL', 'http://127.0.0.1:11434/v1')
    monkeypatch.setenv('AI_MODEL', 'local-test-model')
    monkeypatch.delenv('AI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    captured = []
    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, endpoint, **kwargs):
            captured.append(kwargs['headers'])
            raise TimeoutError('local server offline')
    monkeypatch.setattr(module.httpx, 'AsyncClient', lambda **kwargs: Client())
    fallback = {'title': 'Holiday', 'greeting': 'Owner text'}
    assert await ai_content(Store(tmp_path/'db'), '2029-01-01', {'id': 'new_year'}, 'lv', fallback) == fallback
    assert captured == [{}]
