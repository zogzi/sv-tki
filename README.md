# Svētki

Latvisks Discord svētku bots ar Python 3.12, discord.py, SQLite un Europe/Riga kalendāru. Plānots vienam serverim un **vienam vienlaicīgam bota procesam**. Ziņām nav vajadzīgi lietotāji tiešsaistē. Krievu tulkojumu nav; citām Discord lokalizācijām izmanto angļu valodu.

Iekļauti 17 svētki/atzīmējamās dienas; 11 no tām ir pieci satura varianti katrā no divām valodām (lv/en). Lieldienas aprēķina Gregora kalendārā; Mātes diena ir maija otrajā svētdienā. Šis ir apsveikumu kalendārs, nevis juridisks darba dienu kalendārs.

## Discord iestatīšana

1. Atver https://discord.com/developers/applications un izveido aplikāciju “Svētki”. Sadaļā Bot izveido botu un iegūsti tokenu. Glabā to tikai `.env`; ja tokens noplūst, nekavējoties atiestati to portālā.
2. **Neieslēdz privileged intents.** Bots izmanto `Intents(guilds=True)` (tikai neprivileģētais Guilds intent): nevajag Message Content, Server Members vai Presence. Dalību serverī vārda dienai pārbauda ar atsevišķu REST pieprasījumu.
3. OAuth2 → URL Generator: scopes `bot`, `applications.commands`; bot permissions **View Channels**, **Send Messages**, **Embed Links**, **Read Message History**. Vēsture vajadzīga avāriju atkopšanai. Administratora atļauju botam nedod.
4. Piemēra uzaicinājums (aizvieto APPLICATION_ID):
   `https://discord.com/oauth2/authorize?client_id=APPLICATION_ID&scope=bot%20applications.commands&permissions=84992`
5. Discord lietotāja iestatījumos ieslēdz Developer Mode. Nokopē servera un teksta kanāla ID; ieraksti `.env` laukos `GUILD_ID` un `DEFAULT_CHANNEL_ID`. Pārbaudi arī kanāla atļauju pārrakstījumus.

## Lokāli

```sh
cd sv-tki
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
# Rediģē .env un ievadi tokenu un abus ID.
pytest -q
python -m svetki.bot
```

Vienmēr palaid no repozitorija saknes. SQLite un rotējošie JSON žurnāli atrodas `runtime/`. Atkarību precīzās pārbaudītās versijas var fiksēt savā izvietošanas procesā; pyproject izmanto savietojamības intervālus. Bez tokena programma paziņo trūkstošos laukus un atgriež statusu 2.

## Komandas

- `/svetki today` — šodienas svētki; `/svetki next` — nākamie pieci pēc šodienas.
- `/svetki test holiday:halloween` — privāts priekšskatījums, tikai administratoram; nemaina nosūtīšanas žurnālu. Nezināms ID parāda pieejamos ID.
- `/svetki config channel:#svetki post_time:09:00 lang:lv` — tikai administratoram. Laiks vienmēr Europe/Riga, arī pēc vasaras laika maiņas.
- `/svetki config holiday:halloween enabled:false` — izslēdz konkrētus svētkus. Bez argumentiem parāda iestatījumus.
- `/valoda lang:en` — saglabā lietotāja izvēli (`lv`, `en`). Pretējā gadījumā privātajām atbildēm izmanto interaction.locale, nezināmai valodai angļu.
- `/vardadiena enabled:true name:Anna` un `enabled:false` — pieteikt/atcelt sveicienu.

Plānotie apsveikumi ir servera valodā (sākumā lv). Poga “🌍 Show in my language” atbild privāti izvēlētajā valodā. Tā rāda attiecīgā varianta redakcionālo tulkojumu, arī ja sākotnējais sveiciens radīts ar AI. Pogas saglabā darbību pēc restarta.

## Kalendāra paplašināšana

`data/holidays.json`: unikāls `id`, `rule` un `content` ar `title`, `headline`, `greeting`, `fact` un izvēles `prompt`, `fact_label`, `prompt_label`. `fixed` izmanto `month/day`; `easter` izmanto dienu `offset`; `nth_weekday` izmanto `month/weekday/nth`, kur pirmdiena ir 0. Rediģējot saglabā esošo ID, jo tas identificē nosūtīšanas vēsturi. Varianti rotē secīgi; pēc pieciem gadiem piecu variantu kopums sākas no jauna. Pievieno jaunus variantus, lai ciklu pagarinātu.

Vārda dienu pilns licencēts kalendārs nav pievienots. Ielādes vieta ir `data/namedays.json`, sākumā `{}`. Ievieto pārbaudītu datu kopu ar atbilstošu lietošanas licenci, piemēram, struktūrā `{"07-26": ["Anna"]}`. Atslēgas ir `MM-DD`, vērtības — precīzu vārdu saraksti; 29. februāris tiek svinēts tikai garajā gadā. Pēc izmaiņām restartē botu (Docker gadījumā pārbūvē attēlu). Neielādēta vārda pieteikšanu bots noraida ar paskaidrojumu. Vārda dienu sveicieni ir latviski un neizmanto paziņojošu @pieminējumu.

## Izmēģinām saturu kā atsevišķus stāstus

Svētki nenosaka vienu obligātu formātu. Satura virziens: vēsturiska precizitāte, izziņa, kvalitāte un atbildīga rīcība. Līgo var aplūkot caur folkloras avotu izpēti vai konkrētas tradīcijas izcelsmi. Lāčplēša dienai ir mierīgāks tonis. Sadaļu nosaukumus var pielāgot konkrētajam tekstam. Iesaistes jautājumi nav obligāti, un sākotnējos tekstos tie ir izņemti. Teksti ir redakcionāli melnraksti (`editorial_status: draft`), kurus īpašnieks pārskata pirms izvietošanas; šis marķieris nav tehnisks publicēšanas bloķētājs.

`data/editions.json` ļauj konkrētam gadam un svētkiem aizstāt parasto saturu: `"2026" → "ligo" → {"lv": [...], "en": [...]}`. Iekļauts izmēģinājuma Līgo teksts par tautasdziesmu kā vēstures avotu ar saiti uz Dainu skapi. `calendar_context: true` tam pievieno aprēķinātu šī gada datumu un nedēļas dienu. Nākamais gads bez īpašas redakcijas izmanto parasto variantu kopumu. Pogas tulkojums saglabā sākotnējā ieraksta gadu arī pēc restarta.

Aktualitātes netiek izgudrotas vai automātiski ņemtas no interneta. Ja gribi sasaisti ar attiecīgā gada notikumu, pievieno pārbaudītu redakciju abās valodās un norādi avotu tekstā. AI režīms maina tikai īso ievadu; tas nerada ziņas vai jaunus vēstures faktus.

## Uzticamība

Ik pēc 30 sekundēm bots pārbauda šodienas svētkus. Pēc plānotā laika arī restartēts bots nosūta nokavēto šīs dienas ziņu; iepriekšējās dienas neatjauno. Atsevišķas kļūdas tiek žurnalētas, un pārējie darbi turpinās. Mainot laiku uz agrāku, apsveikums var tikt nosūtīts nākamajā ciklā.

SQLite glabā rezervētu sūtījumu pirms Discord izsaukuma un ziņas ID pēc tā. Ja process apstājas pa vidu, pirms atkārtotas sūtīšanas bots meklē savu unikālo marķieri šīs dienas kanāla vēsturē. Ja vēsturi nevar nolasīt, tas nesūta un mēģina nākamajā ciklā. Neizdzēs marķierus vai datubāzi un nedarbini vairākas replikas. Discord sūtīšana un SQLite nav kopīga transakcija: absolūtu “exactly once” garantiju ārējais API nepiedāvā; administratora izdzēsta nenofiksēta ziņa var tikt nosūtīta atkal.

Healthcheck izmanto plānotāja sirdspukstu, kas atjaunojas tikai ar gatavu Discord savienojumu. Tas nav pilna kanāla atļauju pārbaude; pārbaudi arī žurnālus. Docker pats nepārstartē `unhealthy` konteineru — `restart: unless-stopped` pārstartē beigušos procesu. Uzraugi unhealthy stāvokli un novērs tā cēloni.

## Izvēles AI

Sākumā **izslēgts**, un bots pilnībā strādā bez AI atslēgas. Lai ieslēgtu, `.env` norādi `AI_ENABLED=true`, `OPENAI_API_KEY`, modeli un budžeta parametrus. Izmanto OpenAI HTTPS API, 15 sekunžu timeout un ne vairāk kā 180 atbildes tokenus. AI rada tikai īsu sveicienu; fakti paliek no vietējā kalendāra, lai mazinātu izdomātu apgalvojumu risku. Kļūdas vai sasniegts limits pārslēdz uz vietējo saturu.

SQLite dienā rezervē `AI_REQUEST_BUDGET_USD` katram mēģinājumam, arī neveiksmīgam, un ierobežo rezervāciju summu ar `AI_DAILY_BUDGET_USD`, papildus `AI_DAILY_REQUEST_CAP`. Dienas robeža ir Rīgas pusnakts. Pārbaudi modeļa aktuālo cenu pie pakalpojuma sniedzēja un iestati rezervāciju vismaz pilna pieprasījuma maksimālajām izmaksām. Tas ir konservatīvas rezervācijas limits, nevis pakalpojuma sniedzēja rēķina mērījums; arī pie sniedzēja iestati izdevumu kontroli. Atslēgas nekad neliec Discord komandās vai repozitorijā.

## Docker

```sh
cp .env.example .env
# Aizpildi .env.
docker compose up -d --build
docker compose logs -f --tail=100
docker compose ps
```

Dati paliek `bot-data` sējumā. `docker compose down` tos saglabā; **neizmanto `down -v`**, ja gribi paturēt vēsturi. Pēc koda/datu maiņas: `docker compose up -d --build`. Izvietošanu un rezerves kopijas skatīt [DEPLOYMENT.md](DEPLOYMENT.md).

## Pieņēmumi un pārbaudes

Viens serveris, viens process, viens kopīgs apsveikumu kanāls; pilns vārda dienu kalendārs ir lietotāja ielādējams. AI ir izvēles OpenAI integrācija. Tests bez tīkla pārbauda datumu loģiku, SQLite, satura apjomu, nosūtīšanu un avārijas atkopšanu. `pytest -q` neprasa Discord tokenu. Īstais savienojums un slash komandu reģistrācija jāpārbauda savā testa serverī ar derīgu tokenu.
