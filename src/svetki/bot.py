import asyncio
from datetime import datetime, timedelta
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from .holidays import load_holidays, today, upcoming
from .storage import Store
from .content import language, curated, ai_content, namedays, load_editions

RIGA = ZoneInfo('Europe/Riga')
log = logging.getLogger('svetki')
LABELS = {'lv': ('🔎 Aiz svētku nosaukuma', '💬 Pie mūsu galda'), 'en': ('🔎 Behind the occasion', '💬 Around our table')}


def embed_for(content, lang, marker=None):
    embed = discord.Embed(title=content.get('headline', content['title']), description=content['greeting'], color=0x9E1B34)
    embed.add_field(name=content.get('fact_label', LABELS[lang][0]), value=content['fact'], inline=False)
    embed.set_author(name='Svētki • ' + content['title'])
    if content.get('prompt'):
        embed.add_field(name=content.get('prompt_label', LABELS[lang][1]), value=content['prompt'], inline=False)
    if content.get('sources'):
        embed.add_field(name='Avoti' if lang == 'lv' else 'Sources', value='\n'.join(f"[{source['title']}]({source['url']})" for source in content['sources']), inline=False)
    if content.get('context'):
        embed.add_field(name='📅 ' + ('Šogad' if lang == 'lv' else 'This year'), value=content['context'], inline=False)
    if marker:
        embed.set_footer(text=marker)
    return embed


class Translate(discord.ui.View):
    def __init__(self, bot, holiday, variant, year=None):
        super().__init__(timeout=None)
        year = year or datetime.now(RIGA).year
        button = discord.ui.Button(label='🌍 Show in my language', custom_id=f'svetki:lang:{holiday["id"]}:{variant}:{year}')
        async def click(interaction):
            try:
                lang = language(bot.store.preference(interaction.user.id)[0] or interaction.locale)
                await interaction.response.send_message(embed=embed_for(curated(holiday, lang, variant, year, bot.editions), lang), ephemeral=True)
            except Exception:
                log.exception('Translation failed')
                if not interaction.response.is_done():
                    await interaction.response.send_message('Neizdevās. Mēģini vēlreiz.', ephemeral=True)
        button.callback = click
        self.add_item(button)


class CelebrationBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents(guilds=True), proxy=os.getenv('HTTPS_PROXY') or None, allowed_mentions=discord.AllowedMentions.none())
        self.store = Store(os.getenv('DATABASE_PATH', 'runtime/svetki.sqlite'))
        self.holidays = load_holidays()
        self.names = namedays()
        self.editions = load_editions()
        self.guild_id = int(os.environ['GUILD_ID'])
        self.default_channel = int(os.environ['DEFAULT_CHANNEL_ID'])
        self.job_lock = asyncio.Lock()

    async def setup_hook(self):
        years = {datetime.now(RIGA).year}
        years.update(int(row[0][:4]) for row in self.store.db.execute('SELECT DISTINCT day FROM sent'))
        for holiday in self.holidays:
            for variant in range(max(len(c) for c in holiday['content'].values())):
                for year in years:
                    self.add_view(Translate(self, holiday, variant, year))
        self.tree.add_command(svetki)
        self.tree.add_command(valoda)
        self.tree.add_command(vardadiena)
        guild = discord.Object(id=self.guild_id)
        self.tree.copy_global_to(guild=guild)
        try:
            await self.tree.sync(guild=guild)
        except Exception:
            log.exception('Command sync failed; check application scope and GUILD_ID')
        self.scheduler.start()

    async def on_ready(self):
        log.info('Connected as %s', self.user)
        await self.check_channel()

    async def on_disconnect(self):
        log.warning('Discord disconnected; automatic reconnect enabled')

    async def on_error(self, event, *args, **kwargs):
        log.exception('Event failed: %s', event)

    async def check_channel(self, channel_id=None):
        settings = self.store.settings(self.guild_id, self.default_channel)
        channel = await self.fetch_channel(int(channel_id or settings['channel']))
        if not isinstance(channel, discord.TextChannel) or channel.guild.id != self.guild_id:
            raise ValueError('Channel must be a text channel in configured guild')
        me = channel.guild.me or await channel.guild.fetch_member(self.user.id)
        permissions = channel.permissions_for(me)
        missing = [p for p in ('view_channel', 'send_messages', 'embed_links', 'read_message_history') if not getattr(permissions, p)]
        if missing:
            raise ValueError('Missing channel permissions: ' + ', '.join(missing))
        return channel

    async def deliver(self, day, event, content, lang, view=None):
        if self.store.is_sent(self.guild_id, day.isoformat(), event):
            return
        channel = await self.check_channel()
        variant = self.store.variant(self.guild_id, event, len(content))
        fresh = self.store.claim(self.guild_id, day.isoformat(), event, channel.id, variant)
        row = self.store.db.execute('SELECT state,channel,variant FROM sent WHERE guild=? AND day=? AND event=?', (str(self.guild_id), day.isoformat(), event)).fetchone()
        if row[0] == 'sent':
            return
        if str(channel.id) != row[1]:
            channel = await self.check_channel(row[1])
        variant = row[2]
        marker = f'svetki:{self.guild_id}:{day}:{event}'
        # Only uncertain sends need history reconciliation, never a fresh reservation.
        if not fresh:
            midnight = datetime.combine(day, datetime.min.time(), RIGA)
            async for message in channel.history(limit=None, after=midnight - timedelta(seconds=1), oldest_first=False):
                if message.author.id == self.user.id and any(e.footer.text == marker for e in message.embeds):
                    self.store.finish(self.guild_id, day.isoformat(), event, message.id)
                    return
        payload = content[variant % len(content)]
        holiday = next((h for h in self.holidays if h['id'] == event), None)
        if holiday:
            payload = await ai_content(self.store, day.isoformat(), holiday, lang, payload)
            view = Translate(self, holiday, variant, day.year)
        message = await channel.send(embed=embed_for(payload, lang, marker), view=view)
        self.store.finish(self.guild_id, day.isoformat(), event, message.id)

    @tasks.loop(seconds=30, reconnect=True)
    async def scheduler(self):
        try:
            async with self.job_lock:
                now = datetime.now(RIGA)
                settings = self.store.settings(self.guild_id, self.default_channel)
                if now.strftime('%H:%M') >= settings['time']:
                    for holiday in today(now.date(), self.holidays):
                        if holiday['id'] in settings['disabled']:
                            continue
                        try:
                            lang = language(settings['language'])
                            variants = [curated(holiday, lang, i, now.year, self.editions) for i in range(len(holiday['content']['lv']))]
                            await self.deliver(now.date(), holiday['id'], variants, lang)
                        except Exception:
                            log.exception('Holiday job failed: %s', holiday['id'])
                    names = self.names.get(now.strftime('%m-%d'), [])
                    for user, name in self.store.db.execute('SELECT user,name FROM preferences WHERE name IS NOT NULL').fetchall():
                        if self.store.is_sent(self.guild_id, now.date().isoformat(), 'name-' + user):
                            continue
                        if not any(name.casefold() == n.casefold() for n in names):
                            continue
                        try:
                            # Users must still belong to this guild. No member intent needed.
                            guild = self.get_guild(self.guild_id) or await self.fetch_guild(self.guild_id)
                            member = await guild.fetch_member(int(user))
                            content = dict(title='Vārda diena', greeting=f'Sveiciens vārda dienā, {discord.utils.escape_markdown(member.display_name)}!', fact=f'Šodien vārda dienu svin: {", ".join(names)}.')
                            await self.deliver(now.date(), 'name-' + user, [content], 'lv')
                        except discord.NotFound:
                            pass
                        except Exception:
                            log.exception('Name-day job failed')
                Path('runtime').mkdir(exist_ok=True)
                if self.is_ready():
                    Path('runtime/heartbeat').write_text(str(time.time()))
        except Exception:
            log.exception('Scheduler iteration failed; retrying next tick')

    @scheduler.before_loop
    async def before_scheduler(self):
        await self.wait_until_ready()

    async def close(self):
        if self.is_closed():
            return
        self.scheduler.cancel()
        await super().close()
        self.store.db.close()


svetki = app_commands.Group(name='svetki', description='Svētku kalendārs')


@svetki.command(name='today', description='Šodienas svētki')
async def today_command(interaction: discord.Interaction):
    bot = interaction.client
    events = today(datetime.now(RIGA).date(), bot.holidays)
    lang = language(bot.store.preference(interaction.user.id)[0] or interaction.locale)
    text = '\n'.join(curated(h, lang, 0)['title'] for h in events) or {'lv':'Šodien kalendārā svētku nav.', 'en':'No celebrations today.'}[lang]
    await interaction.response.send_message(text, ephemeral=True)


@svetki.command(name='next', description='Nākamie pieci svētki')
async def next_command(interaction: discord.Interaction):
    bot = interaction.client
    lang = language(bot.store.preference(interaction.user.id)[0] or interaction.locale)
    await interaction.response.send_message('\n'.join(f'{day}: {curated(h, lang, 0)["title"]}' for day,h in upcoming(datetime.now(RIGA).date(), bot.holidays)), ephemeral=True)


@svetki.command(name='test', description='Priekšskatīt svētkus (administrators)')
@app_commands.checks.has_permissions(administrator=True)
async def test_command(interaction: discord.Interaction, holiday: str):
    bot = interaction.client
    item = next((h for h in bot.holidays if h['id'] == holiday), None)
    if not item:
        await interaction.response.send_message('ID: ' + ', '.join(h['id'] for h in bot.holidays), ephemeral=True)
        return
    lang = language(bot.store.settings(bot.guild_id, bot.default_channel)['language'])
    await interaction.response.send_message(embed=embed_for(curated(item, lang, 0, datetime.now(RIGA).year, bot.editions), lang), view=Translate(bot, item, 0), ephemeral=True)


@svetki.command(name='config', description='Mainīt servera iestatījumus (administrators)')
@app_commands.checks.has_permissions(administrator=True)
async def config_command(interaction: discord.Interaction, channel: discord.TextChannel | None = None, post_time: str | None = None, lang: str | None = None, holiday: str | None = None, enabled: bool | None = None):
    bot = interaction.client
    settings = bot.store.settings(bot.guild_id, bot.default_channel)
    if post_time:
        try:
            parsed = datetime.strptime(post_time, '%H:%M')
            if parsed.strftime('%H:%M') != post_time:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message('Laiks: HH:MM, piemēram, 09:00.', ephemeral=True)
            return
        settings['time'] = post_time
    if lang:
        if lang not in LABELS:
            await interaction.response.send_message('Valodas: lv, en.', ephemeral=True)
            return
        settings['language'] = lang
    if holiday is not None or enabled is not None:
        if holiday not in {h['id'] for h in bot.holidays} or enabled is None:
            await interaction.response.send_message('Norādi derīgu holiday ID un enabled.', ephemeral=True)
            return
        disabled = set(settings['disabled'])
        disabled.discard(holiday) if enabled else disabled.add(holiday)
        settings['disabled'] = sorted(disabled)
    await interaction.response.defer(ephemeral=True)
    if channel:
        await bot.check_channel(channel.id)
        settings['channel'] = str(channel.id)
    bot.store.save_settings(bot.guild_id, settings)
    await interaction.followup.send(json.dumps(settings, ensure_ascii=False), ephemeral=True)


@app_commands.command(name='valoda', description='Saglabāt valodu: lv, en')
async def valoda(interaction: discord.Interaction, lang: str):
    if lang not in LABELS:
        await interaction.response.send_message('lv / en', ephemeral=True)
        return
    interaction.client.store.set_preference(interaction.user.id, language=lang)
    await interaction.response.send_message('✓ ' + lang, ephemeral=True)


@app_commands.command(name='vardadiena', description='Pieteikt vai atcelt vārda dienas sveicienu')
async def vardadiena(interaction: discord.Interaction, enabled: bool, name: str | None = None):
    bot = interaction.client
    if enabled and (not name or not any(name.casefold() == n.casefold() for names in bot.names.values() for n in names)):
        await interaction.response.send_message('Šis vārds nav ielādētajā kalendārā. Administratoram jāpapildina data/namedays.json (MM-DD → vārdu saraksts).', ephemeral=True)
        return
    bot.store.set_preference(interaction.user.id, name=name.strip() if enabled else None, set_name=True)
    await interaction.response.send_message('✓ Pieteikts.' if enabled else '✓ Atcelts.', ephemeral=True)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(dict(time=self.formatTime(record), level=record.levelname, logger=record.name, message=record.getMessage(), exception=self.formatException(record.exc_info) if record.exc_info else None), ensure_ascii=False)


def main():
    load_dotenv()
    Path('runtime').mkdir(exist_ok=True)
    formatter = JsonFormatter()
    handlers = [logging.StreamHandler(), RotatingFileHandler('runtime/svetki.log', maxBytes=2_000_000, backupCount=3)]
    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=handlers)
    missing = [key for key in ('DISCORD_TOKEN', 'GUILD_ID', 'DEFAULT_CHANNEL_ID') if not os.getenv(key)]
    if missing:
        log.error('Configure required variables: %s', ', '.join(missing))
        return 2
    try:
        bot = CelebrationBot()
        async def errors(interaction, error):
            log.error('Command failed', exc_info=(type(error), error, error.__traceback__))
            text = 'Neizdevās. Pārbaudi atļaujas un ievadi; skatīt bota žurnālu.'
            if interaction.response.is_done():
                await interaction.followup.send(text, ephemeral=True)
            else:
                await interaction.response.send_message(text, ephemeral=True)
        bot.tree.on_error = errors
        async def run():
            import signal
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(bot.close()))
            try:
                await bot.start(os.environ['DISCORD_TOKEN'], reconnect=True)
            finally:
                if not bot.is_closed():
                    await bot.close()
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info('Stopped by user')
        return 0
    except discord.LoginFailure:
        log.error('Discord rejected the token; replace it securely in .env')
        return 2
    except Exception:
        log.exception('Startup failed')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
