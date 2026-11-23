# Pardal — features in detail

A custom Android app (no Gradle, no Flitsmeister code/APIs) for the round
480×480 screen of the Flitsmeister DASH01.

## Theme
Light, dark or automatic (follows the device), under Settings → Screen → Theme.
Alert colours stay the same in both modes.

## Languages
Nederlands, English, Deutsch, Español, Português and Frysk — interface, alert labels,
compass and spoken warnings (the device's TTS voice; Frysk uses a
Dutch voice if no Frisian one is available). The system language by default, changeable in
Settings → Language.

## Controls while driving
- Large buttons: settings · REPORT · sound; a report screen with six large buttons and
  a wide BACK button.
- Go back with a swipe (report screen: sideways or down; settings: sideways).
- The report and settings screens return on their own after 20 s without a touch.

## What it does
- Large speedometer (GPS, km/h) with a max-speed sign. The road is chosen by
  distance *and* direction of travel (no wrong sign at junctions/parallel roads), with
  brief hysteresis so the sign doesn't flicker.
- Too-fast warning: the sign pulses red and a single beep at limit + max(4, 8%)
  (can be turned off in the menu).
- Speed cameras from **OpenStreetMap**, live via **Overpass** (5 km around the current position):
  `highway=speed_camera`, `enforcement=maxspeed|average_speed`, ANPR/ALPR cameras.
- Current road alerts via **NDW / Rijkswaterstaat** (`actueel_beeld.xml.gz`):
  traffic jam, accident, roadworks, closure, obstacle, speed restriction,
  diversion, weather and bridge. NDW is refreshed every 5 min (driving) or 12 min (stationary),
  and after moving >2 km.
- Warning (beep + vibration + coloured ring) on approach: 500 m / 300 m /
  120 m, only if it is ahead of you (unless you are driving slowly). Colour and label
  differ per alert type.
- Report it yourself on the 480×480 screen: police, ambulance, traffic jam, accident,
  roadworks, obstacle. Your own reports are stored locally (SharedPreferences),
  after 120 s also used as a warning and automatically cleared over time.
- Roads with a max speed are fetched separately around a point ahead of the car
  (900 m in town, up to 3 km on the motorway) and only refreshed once you are ~55% of the way
  through that area; speed cameras every 15 min or after 2 km. On failure a
  backup Overpass server is tried automatically, with backoff.
- Cache in `filesDir/cameras.json` → speed cameras and max speed work offline after one
  successful fetch; NDW alerts are always live.
- Three buttons at the bottom: settings · REPORT · sound on/off (warnings
  stay visible even without sound). Long press = settings.
- The meter colour follows your speed: green = within the limit, orange = just over,
  red = too fast (margin adjustable), blue = limit unknown.
- Look-ahead: if something is within 2 km on your route, the km counter slides
  up and the next object appears large below it (icon, type,
  decreasing distance) plus a "road ahead" bar with up to 3 upcoming objects.
- Warning as a round panel in the centre of the meter: icon, type, large distance,
  approach ring and your speed in the zone colour; the km counter slides into it.
- Custom, hand-drawn icons for each alert type.
- Map in the meter (optional, 2D or 3D): fully offline, drawn from the
  RWS road dataset (wkd.bin) as vector lines — no data usage on the road. Direction of travel up,
  zoom follows the speed, position/rotation smooth between GPS fixes. In map mode
  everything is *in* the map: alerts as pins at their location, a narrow label at the top,
  speed at the bottom, a warning as a glow along the edge.
- Average-speed (section) control: after passing the start camera, how many km you are still in it,
  progress and your average speed (green/orange/red); a voice at the start and end.
- Lane layout for red crosses (lane closures) and "lane ends" (MSI, per lane).
- Open bridge + nearby traffic jam: one combined alert.
- Sound per alert type (settings): choose what you hear; seeing it always stays.
- Too fast: the sign stays round, with "+N km/h" below the speed in orange/red.
- Spoken warnings (the device's Dutch TTS voice, offline):
  "Speed camera in 500 metres", "300 metres to go", "Too fast. Maximum 70";
  music is lowered while speaking. Without a Dutch voice: beeps.
- Demo ride (settings): a showcase of ~3 min past all speed cameras (fixed, mobile,
  section, ANPR), arrow trailer, roadworks, traffic jam, red cross, wrong-way driver, police and
  bridge, with all limit sources (RWS, matrix, temporary, sign, OSM) and green/orange/red.
- Smooth: speed, meter arc, distance-to-hazard, sign and warnings
  animate between the GPS fixes; at rest the app draws ~5x per second.
- Settings screen (round, scrollable): sound, volume, vibration,
  warning distance, too-fast beep + margin, ANPR cameras, NDW alerts,
  meter scale, dim at night, refresh, Overpass server, clear own reports.

## Shared reports (server)

Reports (police, traffic jam, accident, works, obstacle, emergency service) go to the Pardal server
(`server/`, default `https://roadping.jltamp.nl`, adjustable under Settings → Report server).

- **Only visible after 3 reports**: reports of the same type within 250 m (traffic jam 700 m) and
  the same direction of travel are merged. Others only see it once 3 different devices have
  reported it. You see your own report immediately; the confirmation screen shows
  "shared · 1 of 3 reports".
- **Voting**: if you drive past a shared report, the app asks (on screen and by voice)
  "Still there?" with large **YES** / **GONE** buttons. YES extends the report, 2× GONE
  (since the last confirmation) removes it.
- **Online**: the app syncs every minute; the pill at the top shows how many
  Pardal users are online nearby (15 km). Live map in the browser: `/`.
- **Against fake reports**: a device only counts (reporting, YES, GONE) once it has been
  known for at least a quarter of an hour, has driven at some point (≥ 15 km/h) and was within ~3 km
  of the report in the last 15 minutes. Making up new IDs or confirming from a distance therefore does not count; such a
  report is kept but not counted ("counts once you've driven for your first quarter of an hour").
  In addition the device must really have driven (≥ 5 syncs above 15 km/h, over ≥ 10 min) and
  only one reporter counts per known internet address. The online counter counts at most 5 devices
  per internet address.
  A private address (e.g. if the proxy runs behind Docker NAT) is treated as "unknown": then
  the per-internet-address rules lapse and protection relies on the driving/proximity rules.
  So run the reverse proxy where it sees the real client address (not behind a NAT that hides it).
- **Privacy**: a random device ID (stored hashed), the position for the online counter
  rounded to ~1 km and kept in memory only (online 3 min, proximity check 15 min). Can be turned off with "Share reports".

Europe: besides NDW (NL) also open data without an account from Germany (Autobahn GmbH, all
Autobahns, every 10 min), Spain (DGT DATEX II 3.7, every 5 min) and Finland (Digitraffic,
every 5 min), France (Bison Futé, DATEX II v2, national roads without toll roads, every 5 min) and
Portugal (city of Porto only: unplanned restrictions + planned roadworks; there is no
nationwide open feed) and Belgium (Brussels: Mobility Brussels; Flanders: GIPOD, serious
planned disruption to car traffic) — `server/app/europe.py`. Flemish accidents/jams
(Verkeerscentrum) use only Alert-C codes from a non-public location table;
Wallonia requires an account. The page queries per map view (`/v1/official?bbox=…`),
and the app receives them abroad via the sync. Not yet: Flanders (Alert-C codes only),
countries that require an account (UK, Norway, Sweden, Austria, Poland, Czechia).

Live page (`/`): reports from drivers plus a layer of official NDW alerts
(accidents, traffic jams, obstacles, open bridges, closed roads; roadworks can be enabled separately),
place names via PDOK, today's statistics and filters per type.

Running the server: `cd server && docker compose up -d --build` (FastAPI + SQLite in `./data`,
port 8095 on `${BIND}`). Testing locally with the emulator: `adb reverse tcp:8095 tcp:8095` and
set `http://localhost:8095` as the server (only localhost may be unencrypted).

## Speed limit: sources and priority
The displayed limit comes from the first source that knows something (the label below the
sign shows which):

| # | Source | Label | How |
|---|------|-------|-----|
| 1 | NDW temporary maximum speeds | TIJDELIJK | road section + direction of travel, every 10 min |
| 2 | NDW matrix signs (MSI) | MATRIX | the last gantry passed in your direction; live every 2 min, only on the motorway |
| 3 | NDW traffic signs (A1) | BORD | sign passed in its direction of travel; valid until you turn off / 3 km; cached per municipality (PDOK) for 30 days |
| 4 | Rijkswaterstaat WKD | RWS | official limit per road section incl. direction and time window (e.g. 100 from 6-19 h, otherwise 130); offline |
| 5 | OpenStreetMap | OSM | maxspeed via Overpass |

Red crosses on matrix signs become alerts ("LANE CLOSED" / "ROAD CLOSED").

## Navigation

Button next to REPORT (phone) or Settings > Navigate (DASH01): search for an address, street,
place or point (station, shop). Also from other apps via `geo:` and
`google.navigation:` links. While navigating: a route line on the map, a turn card
at the top (arrow, distance, street, arrival time, cross = stop), spoken directions
("In 300 metres turn left, Domstraat") in all six languages, and automatically a new route
if you deviate from it.

Server: `GET /v1/geocode?q=` (PDOK + Photon/OSM, Netherlands only, via the server so that the
services do not see the user's IP) and `POST /v1/route` (a custom
[Valhalla](https://github.com/valhalla/valhalla) container `roadping-valhalla`, reachable only
internally). The routing engine runs on the self-hostable server.

## In the car: CarPlay and Android Auto

iPhone: CarPlay (navigation app). Android (from 2.9.0): Android Auto through the Car App
Library, navigation category. The car display shows the same Pardal map as the phone, with
cameras and alerts in the map, the warning at the top, speed and limit bottom left. The car
itself draws the turn card, arrival time and the buttons: **Search** (typing only while
parked; recent destinations), **Report** (the same types as the REPORT screen), sound on/off
and zoom. Stop navigating with the cross in the arrival card. The next turn is also sent to
the instrument cluster when the car supports it. Spoken warnings play through the phone
(also while another app is on screen).

## Data sources
- Speed cameras and maxspeed: © OpenStreetMap contributors, ODbL — via the public
  Overpass API. Default endpoint: `https://overpass-api.de/api/interpreter`
  (adjustable in the menu).
- Road alerts: NDW / Rijkswaterstaat open data (https://opendata.ndw.nu/):
  - `actueel_beeld.xml.gz` — traffic jams, accidents, roadworks, closures, weather (5/12 min)
  - `veiligheidsgerelateerde_informatie_srti.xml.gz` — arrow trailers, crash cushions,
    breakdowns, wrong-way drivers; with direction of travel, only your side of the road (2 min)
  - `tijdelijke_verkeersmaatregelen_maximum_snelheden.xml.gz` — temporary limits;
    take priority over the OSM maxspeed if you are driving on that road section in that direction (10 min)
  - `planningsfeed_brugopeningen.xml.gz` — bridge open now or within 10 min (10 min)
  - `Matrixsignaalinformatie.xml.gz` + `ndw_msi_shapefiles_latest.zip` — matrix signs
- Traffic signs: NDW traffic-signs API v4 (RVV A1), municipality via PDOK Locatieserver.
- Official limits: Rijkswaterstaat Wegkenmerkendatabase (WKD), Maximum Speeds.
- No data, code or endpoints from Flitsmeister or other commercial providers are used.
