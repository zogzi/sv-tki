from datetime import date
from unittest.mock import AsyncMock
import pytest
from svetki.bot import CelebrationBot
from svetki.content import curated, language

@pytest.fixture
def bot(tmp_path,monkeypatch):
    monkeypatch.setenv('GUILD_ID','123')
    monkeypatch.setenv('DEFAULT_CHANNEL_ID','456')
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'bot.sqlite'))
    return CelebrationBot()

def test_commands(bot):
    assert {c.name for c in __import__('svetki.bot',fromlist=['svetki']).svetki.commands} == {'today','next','test','config'}
    assert language('en-US')=='en'
    assert language('ru')=='en'
    assert language('de')=='en'
    assert curated(bot.holidays[0],'unknown',0) == curated(bot.holidays[0],'en',0)

class Channel:
    id=456
    def __init__(self):
        self.messages=[]
        self.send=AsyncMock(return_value=type('Message',(),{'id':999})())
    async def history(self,**kwargs):
        for message in self.messages:
            yield message

@pytest.mark.asyncio
async def test_send_once(bot):
    channel=Channel()
    bot.check_channel=AsyncMock(return_value=channel)
    bot._connection.user=type('User',(),{'id':789})()
    holiday=bot.holidays[0]
    content=holiday['content']['lv']
    await bot.deliver(date(2026,1,1),'new_year',content,'lv')
    await bot.deliver(date(2026,1,1),'new_year',content,'lv')
    assert channel.send.await_count==1

@pytest.mark.asyncio
async def test_reconcile_crash(bot):
    channel=Channel()
    bot.check_channel=AsyncMock(return_value=channel)
    bot._connection.user=type('User',(),{'id':789})()
    marker='svetki:123:2026-01-01:new_year'
    import discord
    embed=discord.Embed().set_footer(text=marker)
    channel.messages=[type('Message',(),{'id':111,'author':bot.user,'embeds':[embed]})()]
    bot.store.claim(123,'2026-01-01','new_year',456,0)
    await bot.deliver(date(2026,1,1),'new_year',bot.holidays[0]['content']['lv'],'lv')
    channel.send.assert_not_awaited()
    assert bot.store.db.execute('SELECT state,message FROM sent').fetchone()==('sent','111')

@pytest.mark.asyncio
async def test_history_failure_does_not_send(bot):
    channel=Channel()
    async def broken(**kwargs):
        raise RuntimeError('history unavailable')
        yield
    channel.history=broken
    bot.check_channel=AsyncMock(return_value=channel)
    bot.store.claim(123,'2026-01-01','new_year',456,0)
    with pytest.raises(RuntimeError):
        await bot.deliver(date(2026,1,1),'new_year',bot.holidays[0]['content']['lv'],'lv')
    channel.send.assert_not_awaited()

def test_editorial_embed(bot):
    from svetki.bot import embed_for
    item=next(h for h in bot.holidays if h['id']=='ligo')
    content=curated(item,'lv',0,2026,bot.editions)
    assert 'otrdienā' in content['context']
    assert content['headline']=='Līgo dziesma kā vēstures avots'
    embed=embed_for(content,'lv')
    assert embed.title==content['headline']
    assert len(embed.fields)==3
    assert 'ru' not in item['content']
    assert curated(item,'en',0,2027,bot.editions)['headline'] != content['headline']

@pytest.mark.asyncio
async def test_completed_post_needs_no_api_requests(bot):
    bot.store.claim(123,'2026-01-01','new_year',456,0)
    bot.store.finish(123,'2026-01-01','new_year',111)
    bot.check_channel=AsyncMock(side_effect=RuntimeError('must not be called'))
    await bot.deliver(date(2026,1,1),'new_year',bot.holidays[0]['content']['lv'],'lv')
    bot.check_channel.assert_not_awaited()

@pytest.mark.asyncio
async def test_scheduler_catchup_and_failure_isolation(bot,monkeypatch):
    import svetki.bot as module
    from datetime import datetime
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):
            return cls(2026,10,31,12,0,tzinfo=tz)
    monkeypatch.setattr(module,'datetime',Clock)
    item=next(h for h in bot.holidays if h['id']=='halloween')
    bot.holidays=[item,dict(item,id='second-event')]
    bot.deliver=AsyncMock(side_effect=[RuntimeError('one failed job'),None])
    await bot.scheduler.coro(bot)
    assert bot.deliver.await_count==2
    bot.deliver.reset_mock(side_effect=True)
    settings=bot.store.settings(bot.guild_id,bot.default_channel)
    settings['time']='13:00'
    bot.store.save_settings(bot.guild_id,settings)
    await bot.scheduler.coro(bot)
    bot.deliver.assert_not_awaited()
