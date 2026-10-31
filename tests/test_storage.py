from svetki.storage import Store

def test_claim_survives_restart(tmp_path):
    path=tmp_path/'state.sqlite'
    store=Store(path)
    assert store.claim(1,'2026-01-01','new_year',2,0)
    store.db.close()
    store=Store(path)
    assert not store.claim(1,'2026-01-01','new_year',2,0)
    store.finish(1,'2026-01-01','new_year',42)
    assert store.variant(1,'new_year',5)==1
    assert store.variant(2,'new_year',5)==0

def test_preferences(tmp_path):
    store=Store(tmp_path/'db')
    store.set_preference(1,language='en')
    store.set_preference(1,name='Anna',set_name=True)
    assert store.preference(1)==('en','Anna')
    store.set_preference(1,name=None,set_name=True)
    assert store.preference(1)==('en',None)

def test_ai_budget(tmp_path):
    store=Store(tmp_path/'db')
    assert store.reserve_ai('2026-01-01',5,.01,.02)
    assert store.reserve_ai('2026-01-01',5,.01,.02)
    assert not store.reserve_ai('2026-01-01',5,.01,.02)
    assert store.reserve_ai('2026-01-02',1,.01,.02)
    assert not store.reserve_ai('2026-01-02',1,.01,.02)
