# Pastāvīga izvietošana

Discord botam vajadzīgs ilgstošs izejošs Gateway WebSocket savienojums un HTTPS piekļuve Discord. Inbound publisks HTTP ports nav vajadzīgs. Bezmaksas platformas, kas iemidzina neaktīvus procesus, šim uzdevumam nav piemērotas: miegā bots nesaņem notikumus un neizpilda grafiku. Replit, Glitch un bezmaksas tīmekļa pakalpojumu pieejamība un ierobežojumi mainās; pārbaudi pašreizējo piedāvājumu, nepaļaujies uz agrākām pamācībām.

## 1. Oracle Cloud Always Free VM

Pirms konta/VM izveides pārbaudi https://www.oracle.com/cloud/free/ un https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm : aktuālos nosacījumus, pieejamo kapacitāti, idle resursu atgūšanas politiku, disku/tīkla ierobežojumus un to, vai izvēlētais resurss tiešām ir Always Free. Šeit nav solījuma par cenu vai bezmaksas resursu pieejamību. Ieslēdz budžeta paziņojumus; brīdinājums pats par sevi ne vienmēr aptur izmaksas.

1. Izveido kontu, reģionu un Compute VM ar aktuālajam bezmaksas piedāvājumam atbilstošu formu un Ubuntu LTS. Gan x86_64, gan arm64 gadījumā pārbaudi Docker un Python attēla atbalstu. Neliec klāt maksas diskus vai citus resursus, neapskatot cenu.
2. Izveido SSH atslēgu lokāli. OCI VCN/security list vai NSG atļauj inbound TCP 22 **tikai no sava IP**. Atstāj vajadzīgo izejošo HTTPS/DNS piekļuvi. Botam nav jāatver ne 80, ne 443 inbound.
3. Pieslēdzies: `ssh ubuntu@VM_IP`. Atjaunini sistēmu: `sudo apt-get update` un `sudo apt-get upgrade`; restartē, ja nepieciešams. Atļauj SSH lokālajā firewall pirms tā ieslēgšanas, lai neizslēgtu sevi.
4. Instalē Docker Engine un Compose plugin pēc https://docs.docker.com/engine/install/ubuntu/ aktuālās apt pamācības. Izmanto oficiālo parakstīto repozitoriju un saglabā GPG/TLS pārbaudes. Pārbaudi `sudo docker version` un `sudo docker compose version`.
5. Ieslēdz auto-start: `sudo systemctl enable --now docker`. Ja pievieno lietotāju `docker` grupai, apzinies, ka tā dod praktiski root tiesības; citādi turpmākajām Docker komandām lieto sudo.
6. Instalē Git (`sudo apt-get install git`), noklonē savu `zogzi/sv-tki` repozitoriju ar atļautu piekļuvi un ieej tajā. Privātam repo izmanto read-only deploy key vai citu drošu Git autentifikāciju; neliec tokenu komandrindas URL. Mākoņa izstrādes vides Git autentifikācija nav automātiski pieejama VPS.
7. `cp .env.example .env`, `chmod 600 .env`; redaktorā aizpildi Discord tokenu un ID. Neliec īstas vērtības shell vēsturē. Pārbaudi kanāla atļaujas pēc README.
8. `docker compose up -d --build`, tad `docker compose logs --tail=100` un `docker compose ps`. Sagaidi “Connected”, pārbaudi, ka nav atļauju/sync kļūdu. Discord izpildi `/svetki today`, `/svetki test holiday:halloween` un nospied valodas pogu. Administrators var testa kanālā uzstādīt šodienas laiku; pēc pārbaudes atjauno 09:00.
9. Pārstartē VM un pārbaudi, ka Docker un bots atgriežas. `restart: unless-stopped` neatjaunos konteineru, kuru apzināti apturēji; tad lieto `docker compose up -d`.

## 2. Neliels maksas VPS

Izvēlies mazu pastāvīgi ieslēgtu Linux VPS pie uzticama pakalpojuma sniedzēja. Bots ir neliels, bet Docker būvēšanai un OS jāatstāj pietiekama RAM/diska rezerve. Salīdzini pašreizējās cenas, nodokļus, IPv4 maksu, datu pārraidi un rezerves kopijas sniedzēju vietnēs; “daži eiro mēnesī” ir budžeta mērķis, ne garantēta cena.

Izveido Ubuntu LTS VM, ne-root SSH lietotāju un atslēgu autentifikāciju, atļauj tikai SSH no sava IP un izejošos savienojumus. Turpini ar Oracle sadaļas 3.–9. soli. Ieslēdz OS drošības atjauninājumus atbilstoši savam uzturēšanas plānam un regulāri atjaunini Docker attēlu/atkarības. Uzraugi disku, žurnālus, konteinera veselību un Gateway atvienojumus.

## Lokāla palaišana

Vajag Python 3.12: `python3.12 -m venv .venv`, aktivizē vidi, `pip install -e '.[test]'`, izveido `.env`, `pytest -q`, `python -m svetki.bot` no projekta saknes. Datoram jāpaliek ieslēgtam; aizverot procesu, plānotājs apstājas. To pašu tokenu vienlaikus nedarbini lokāli un VPS.

## SQLite rezerves kopijas

Datubāze satur nosūtīšanas vēsturi, servera iestatījumus un lietotāju izvēles. Nekopē tikai dzīvas WAL datubāzes galveno failu. Drošs tiešsaistes backup ar SQLite backup API:

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

Glabā kopiju šifrēti ārpus VM, ar datumu un piekļuves ierobežojumu. Atsevišķi droši saglabā `.env` un savas kalendāra izmaiņas. Atjaunošanai apturi botu, saglabā pašreizējā sējuma kopiju, aizvieto SQLite ar pārbaudīto backup un izņem tikai apturētās vecās datubāzes `-wal`/`-shm` blakusfailus. Nodrošini faila īpašnieku UID 10001 konteinerā un palaid botu. Pārbaudi `PRAGMA integrity_check` pirms atjaunošanas.

Veca backup atjaunošana var atkārtot sūtījumus pēc kopijas datuma. Pārbaudi šīs dienas vēsturi un nemaini svētku ID. Periodiski pārbaudi atjaunošanu atsevišķā datubāzē, nevis tikai kopijas esamību.

## Problēmu diagnostika

- `Configure required variables`: aizpildi `.env` un izveido konteineru atkārtoti.
- Tokena noraidījums: atiestati to Developer Portal un droši nomaini `.env`.
- Atļauju kļūda: pārbaudi četras README atļaujas kanālā, ne tikai lomu serverī.
- `unhealthy`: apskati `docker compose logs`, tīklu, tokenu un plānotāja žurnālus. Docker veselības statuss pats nepārstartē procesu; pēc cēloņa novēršanas `docker compose restart bot`.
- Botam nav slash komandu: pārbaudi GUILD_ID, `applications.commands` scope un komandu sinhronizācijas žurnālus.
