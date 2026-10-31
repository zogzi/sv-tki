# Hosting and deployment

The bot needs a **persistent process**, an outbound Discord Gateway WebSocket, HTTPS and durable SQLite storage. It does not need a public website or inbound HTTP port. A separately hosted Python/Docker process does not depend on keeping a Codex session or ChatGPT subscription open.

## Concrete candidates

Research status: **31 October 2026**. The environment's proxy rejected access to the official Hetzner site with HTTP 403 at the CONNECT stage. Current offer pages, prices and free-tier terms could not be verified here. The table is an actionable shortlist with official references, **not a set of verified current price quotes**. Required research domains were saved in the environment settings draft; that save does not apply network access by itself.

| Candidate | Why investigate it for this bot | Official offer/terms to check | Before choosing |
| --- | --- | --- | --- |
| **Hetzner Cloud** | First paid candidate: compare a small Linux VM in a European location, running one Docker service and SQLite. | [Cloud offers](https://www.hetzner.com/cloud/), [cloud documentation](https://docs.hetzner.com/cloud/) | Smallest suitable x86/ARM plan, actual monthly total, VAT, public IP charges, region availability and backup cost. |
| **Netcup VPS** | Alternative paid VM to compare against Hetzner, especially if the total offer is better for your location. | [Official Netcup site](https://www.netcup.com/) | RAM/disk, setup charges, minimum contract period, renewal price, cancellation terms and backup options. |
| **OVHcloud VPS** | A further paid option when its available location, support and total cost suit you better. | [VPS offers](https://www.ovhcloud.com/en/vps/) | Price including tax, initial versus renewal price, commitment period, region, storage and backups. |
| **Oracle Cloud Always Free** | Free VM route to investigate if currently eligible capacity is available and the terms suit the workload. | [Free offer](https://www.oracle.com/cloud/free/), [Free Tier documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm) | Always Free versus time-limited trial, account/card requirements, eligible shape/region/storage, capacity and any idle-resource reclamation rules. |
| **Existing home machine** | Avoid renting another machine if you already have suitable hardware and can keep it running. | Your hardware, electricity and ISP terms | Power/network outages, sleep settings, disk backups and ongoing electricity cost. |

**Practical recommendation:** compare the smallest suitable paid European VPS first if predictable availability matters more than a zero hosting bill. Investigate Oracle if the budget must be zero, but do not build a reliability promise around unverified free-tier eligibility or capacity. Choose a provider only after seeing its actual order total. No VM or billing account has been created.

For planning, a shared vCPU and roughly 1–2 GB RAM are a reasonable starting target for this small bot process, **not a measured provider-specific minimum**. Leave room for OS updates, Docker builds and logs. This does not include running a local language model. Check the actual working set after deployment rather than buying a large VM speculatively.

### Compare the complete cost

Record the date and total from the provider's checkout before purchasing:

- Monthly recurring price, including applicable tax.
- Public IPv4 or other IP charges, if needed. Confirm outbound Discord connectivity on the chosen networking setup.
- Disk, snapshots/backups and any setup fee.
- Minimum term, cancellation window and renewal price; do not compare an introductory price with another provider's normal rate.
- Transfer limits/overage and the selected region's availability.
- **Separate AI API use**, if enabled. A hosting bill is not an AI subscription; see [AI.md](docs/AI.md).

No exact euro amount is recorded until it can be read from a current official offer. “A few euros a month” is a target budget, not a quotation.

## Why sleeping platforms are unsuitable

A sleeping process cannot maintain the Discord Gateway connection or execute its schedule. A web-service health endpoint and occasional artificial pings do not establish reliable persistent-worker hosting. Before using any managed service, explicitly check its **background worker** pricing, idle/sleep policy, restart behaviour, WebSocket support and persistent disk.

Old Replit/Glitch/free-web-service tutorials are not evidence of a current free always-on bot offering. Products change or close. Serverless functions may be useful for other architectures, but the current discord.py Gateway bot is a long-running process.

## Option 1: Oracle Cloud VM

1. Read the current [free offer](https://www.oracle.com/cloud/free/) and [terms documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm). Confirm the selected resource is eligible for ongoing Always Free use, rather than consuming trial credit. Check all disks/networking too. Configure billing alerts, understanding that an alert is not necessarily a hard spending stop.
2. Create an eligible Ubuntu LTS Compute VM in an available region. Verify Docker/Python support for its architecture. Do not add paid resources without checking their price.
3. Generate an SSH key locally. In OCI networking/security rules, allow inbound SSH (TCP 22) **from your own IP**. The bot does not need inbound ports 80 or 443. Retain outbound access needed for DNS, HTTPS, Discord WebSocket and your optional AI provider.
4. Connect with `ssh ubuntu@VM_IP`, then follow the shared Linux/Docker instructions below.
5. Check the actual free-tier conditions periodically. Keep backups independent of the VM so that losing the instance does not mean losing delivery history.

## Option 2: paid VPS

1. Compare Hetzner Cloud, Netcup and OVHcloud using the current total cost checklist above. Choose a persistent Linux VM with adequate disk/RAM, not an idle-sleeping web plan.
2. Create Ubuntu LTS with a non-root SSH user and key-based access. Restrict inbound SSH to your IP; permit the required outbound connections. Confirm recovery-console access before changing firewall/SSH settings.
3. Follow the same installation steps below. Configure provider billing notifications and an update/backup schedule.

## Shared Linux/Docker installation

1. Update the OS with `sudo apt-get update` and `sudo apt-get upgrade`. Reboot if required. Allow SSH before enabling the host firewall to avoid locking yourself out.
2. Install Docker Engine and the Compose plugin using the current [official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/). Use the signed repository and keep GPG/TLS verification enabled. Verify `sudo docker version` and `sudo docker compose version`.
3. Enable startup with `sudo systemctl enable --now docker`. Docker-group membership grants effectively root access; either accept that deliberately or use `sudo` with Docker commands below.
4. Install Git and clone the repository:

   ```sh
   sudo apt-get install git
   git clone https://github.com/zogzi/sv-tki.git
   cd sv-tki
   ```

   A private repository needs an appropriate read-only deploy key or other secure Git authentication. The development environment's injected authentication does not automatically exist on your VPS. Do not embed tokens in clone URLs.
5. Create local configuration without overwriting an existing `.env`:

   ```sh
   cp .env.example .env
   chmod 600 .env
   ```

   Edit it with a text editor. Configure the Discord token, server ID and channel ID; leave AI off until you have chosen its provider/billing. Never put real secrets into Git. **Review/replace the content drafts before starting**, or use a private test server and disable unreviewed holidays.
6. Build/start and inspect the result:

   ```sh
   docker compose up -d --build
   docker compose logs --tail=100
   docker compose ps
   ```

   Expect a connection log and no command-sync/permission errors. In the configured test server, exercise `/svetki today`, `/svetki test holiday:ligo` and its language button. Check actual rendering rather than assuming a successful build establishes Discord readiness.
7. For a controlled scheduled-post test, use a private test channel and a celebration occurring that day, then set a posting time before the current Riga time. The next scheduler cycle may post immediately. Restore the intended 09:00 configuration afterward; do not erase delivery history to keep retesting in production.
8. Reboot the VM and confirm Docker/bot recovery. `restart: unless-stopped` will not restart a service you intentionally stopped; use `docker compose up -d` to start it again.

On the managed Codex cloud environment, builds behind its proxy require the provided CA bundle as BuildKit secret `proxy_ca`. This is environment-specific, not a public certificate to commit to the image. Normal VPS builds do not need that session CA.

## Updates and operation

From the checkout, obtain the intended reviewed revision and run `docker compose up -d --build`. Dependency intervals in `pyproject.toml` do not constitute an immutable lock; validate dependency updates before production use.

Changing environment variables requires recreating the container (`docker compose up -d --force-recreate bot`); changing bundled data or the writing brief requires a rebuild. Do not run a local instance alongside production with the same guild/token.

The healthcheck uses `runtime/heartbeat`, refreshed while the scheduler is running and Discord reports ready. It is not a complete end-to-end permissions check. Docker marks a running service `unhealthy` but does **not** restart it for that reason alone. Monitor the status and logs; investigate token, DNS/network or scheduler failures before restarting. An external outage notification/monitor has not been configured.

The bot reconnects through discord.py, isolates individual jobs and logs failures to stdout and rotating files. Docker's log driver is also rotated. Monitor disk use, OS security updates and API-model availability. A long-running bot needs maintenance even if you stop using Codex.

## Run locally

From the repository root, create a Python 3.12 virtual environment, `pip install -e '.[test]'`, configure `.env`, run `pytest -q`, then `python -m svetki.bot`. The machine must remain awake and the process must remain running. Closing a development session is not permanent hosting.

## SQLite backup and restore

The database holds sent history, settings, user preferences and cached AI introductions. Do not copy only the main file of a live WAL database. Use SQLite's online backup API:

```sh
docker compose exec -T bot python - <<'PY'
import sqlite3
source = sqlite3.connect('/app/runtime/svetki.sqlite')
target = sqlite3.connect('/app/runtime/backup.sqlite')
source.backup(target)
target.close()
source.close()
PY
docker compose cp bot:/app/runtime/backup.sqlite ./backup.sqlite
```

Keep dated copies outside the VM, with encryption/access controls. Securely back up `.env` separately, along with the owner's content/brief changes. The Docker named volume persists across `docker compose down`; **`down -v` deletes it**.

For restoration, stop the bot, preserve the existing volume contents, validate the backup with `PRAGMA integrity_check`, and replace the database. Only after stopping the old database remove its obsolete `-wal`/`-shm` companion files. Restore container ownership to UID 10001 and restart. A stale backup can cause re-posting for dates not recorded in it. Test restoration separately before relying on the backup routine.

## Troubleshooting

- Missing configuration: edit `.env`, then recreate the container.
- Rejected Discord token: reset it in the Developer Portal and replace it securely.
- Missing commands: check `GUILD_ID`, `applications.commands` scope and synchronization logs.
- Channel failures: check all four permissions in README, including channel overrides and message-history access.
- AI unavailable: check the selected provider's API account/billing/model, not the status of a ChatGPT Pro subscription. Saved content remains the fallback.
- Unhealthy container: inspect logs, connection state and heartbeat before restarting; this status alone does not trigger Docker restart.
