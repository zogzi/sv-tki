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
