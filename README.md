# Svētki

A Python 3.12 Discord celebration bot for a Latvian-speaking community. Scheduled posts use **Europe/Riga** time, SQLite stores delivery history and preferences, and the bot uses one process for one server. Posts are Latvian by default, with English translations. Other Discord locales fall back to English.

**This is a working foundation, not a finished editorial product or a deployed service.** The owner will write the final voice and revise the content. Existing posts are drafts. Live Discord validation, hosting selection and source-backed future-year writing remain outstanding; see [project status](docs/PROJECT_STATUS.md).

- [AI, subscriptions, costs and future-year relevance](docs/AI.md)
- [Concrete hosting candidates and deployment](DEPLOYMENT.md)
- [Existing content drafts](CONTENT_REVIEW.md)
- [Owner-editable AI writing brief](data/editorial_brief.md)

## Discord setup

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications), add a bot, and obtain its token. Keep it in `.env` or secure environment settings. Reset it if exposed.
2. Leave **privileged intents disabled**. The bot uses only the nonprivileged Guilds intent: no Message Content, Server Members or Presence intent. Name-day membership checks use individual REST requests.
3. Generate an OAuth2 invite with scopes `bot` and `applications.commands`. Permissions: **View Channels**, **Send Messages**, **Embed Links**, **Read Message History**. History access is required to reconcile uncertain sends after a crash. Do not grant the bot Administrator.
4. Invite URL, replacing `APPLICATION_ID`:
   `https://discord.com/oauth2/authorize?client_id=APPLICATION_ID&scope=bot%20applications.commands&permissions=84992`
5. Enable Developer Mode in Discord, copy the server/channel IDs, and configure `GUILD_ID` and `DEFAULT_CHANNEL_ID`. Check channel permission overrides too.

## Run locally

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
# Edit .env: DISCORD_TOKEN, GUILD_ID, DEFAULT_CHANNEL_ID.
pytest -q
python -m svetki.bot
```

Run from the repository root. Database files and rotating JSON logs live in ignored `runtime/`. Missing required configuration produces an explicit log and exit status 2. No AI key is needed for the normal workflow. Do not run another copy with the same server/token while the production bot is running.

## Commands

| Command | Purpose |
| --- | --- |
| `/svetki today` | List today's celebrations privately. |
| `/svetki next` | List the next five celebrations after today. |
| `/svetki test holiday:ligo` | Administrator-only private preview; does not mark the holiday as sent or call AI. Unknown IDs return the available IDs. |
| `/svetki config channel:#svetki post_time:09:00 lang:lv` | Administrator-only server settings; time is always Europe/Riga. |
| `/svetki config holiday:halloween enabled:false` | Enable/disable a particular holiday. With no arguments, show settings. |
| `/valoda lang:en` | Save `lv` or `en`; otherwise use the interaction locale. |
| `/vardadiena enabled:true name:Anna` | Opt in, if that name is present in the loaded dataset. Use `enabled:false` to opt out. |

The language button responds ephemerally. It shows the authored translation of the same variant/year, **not an exact translation of an AI-generated introduction**. Persistent buttons survive restarts while their content remains available.

## Content and calendar

`data/holidays.json` contains 17 celebrations/observances. Eleven have at least five variants in both languages. Gregorian Easter is calculated; Mother's Day is the second Sunday in May. This is a celebration calendar, not a legal working-day calendar.

Date rules are `fixed` (`month`, `day`), `easter` (`offset` in days), or `nth_weekday` (`month`, `weekday`, `nth`; Monday = 0). Content fields include `title`, `headline`, `greeting`, `fact`, optional section labels and sources. Keep IDs stable because they identify delivery history. Variants rotate; a finite pool eventually repeats.

`data/editions.json` can replace a holiday's content for a specified year, with both `lv` and `en` entries. It does not research that year's events. The included `calendar_context` example calculates a weekday/date only. Source links in authored files are references, not proof that the bot has fetched or verified them.

The existing text is marked `editorial_status: draft`. This is a documentation marker, **not a publication gate**. Before deployment, replace/review the drafts or disable the affected holidays. The editorial brief affects optional AI introductions; it does not automatically rewrite saved posts.

### Name days

`data/namedays.json` starts as `{}`. Supply a checked, appropriately licensed `MM-DD` → list-of-names dataset; for example, `{"07-26": ["Anna"]}` demonstrates the format. Restart after editing; rebuild the Docker image when its bundled data changes. February 29 entries occur only in leap years. The bot rejects opt-ins for names it cannot find. Name-day greetings are Latvian and do not send notification mentions.

## Optional AI

A running bot does **not** use your ChatGPT Pro or Codex session. It calls a separately configured API, or an explicitly configured local compatible server. Ending a chat/coding subscription does not by itself stop a separately hosted bot; API access, API billing and hosting still need to remain active.

AI is disabled by default. Current AI support rewrites only an introduction using the authored facts and actual post date. It does not search the web or solve future-year relevance. You can edit `data/editorial_brief.md`, `AI_BASE_URL`, `AI_MODEL` and the API key without changing the application code. Successful introductions are cached in SQLite, and failures fall back to saved content. Read [AI.md](docs/AI.md) before enabling it, especially its cost-control limitations.

## Reliability and Docker

The scheduler checks every 30 seconds. After the configured posting time, it catches up missed posts for the same Riga calendar day, including after restart. It does not backfill previous days. Individual job failures are logged and isolated.

SQLite reserves a send before calling Discord and records the message ID afterward. An uncertain send is reconciled against the bot's marker in that day's channel history before retrying. Completed posts avoid further channel API calls. If history cannot be read, the bot defers the uncertain send. Use **one replica** and retain the database. Discord and SQLite cannot share an atomic transaction; deleting an uncertain message or restoring old state can still cause a repeat.

```sh
cp .env.example .env
# Configure credentials and IDs. Review drafts before starting.
docker compose up -d --build
docker compose logs -f --tail=100
docker compose ps
```

SQLite/logs persist in `bot-data`. `docker compose down` preserves the volume; `down -v` deletes it. Docker restarts exited processes with `unless-stopped`. The healthcheck detects a stale scheduler/connection heartbeat, but Docker does **not** automatically restart an unhealthy, still-running container. Monitor health and logs. See [deployment and backups](DEPLOYMENT.md).

## Validation

`pytest -q` runs offline calendar, persistence, recovery, scheduler and AI-configuration tests. Mocked API tests are not a live provider test. A real token/server is still needed to validate Gateway connectivity, permissions, command sync and actual Discord rendering. No production hosting account or AI service has been provisioned by this repository.
