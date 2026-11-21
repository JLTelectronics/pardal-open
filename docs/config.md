# Customising Pardal via the server (`/v1/config`)

Without a new app version you can adjust report types, features per country, messages to users
and texts. The server has a built-in default (`server/app/config.py`, `DEFAULT`)
that describes exactly how the apps behave; your own file overrides it:

    server/data/config.json      (inside the container: /data/config.json)

- Saving = live. The server re-reads the file as soon as it changes; no restart needed.
- A broken file (JSON error, wrong colour): the server keeps the previous good version and
  reports it in the log (`docker logs roadping | grep config`). Always check with
  `curl https://<your-server>/v1/config`.
- On every sync (every 1–3 min) the apps request the hash; if it differs, they fetch the new
  config and store it. Without internet they use the last stored one, and without anything the
  built-in default: so the app always works.
- Merging: objects are deeply merged; `types` per `id` (only the fields you
  mention change; `{"id": 9, "remove": true}` removes a type); other lists
  (`messages`, `report_areas`) you replace in their entirety.

## Report types (`types`)

| field | meaning |
|---|---|
| `id` | 1–99. 1–12 are the existing types (see DEFAULT); new types from 13 onwards |
| `key` | label key, Dutch in capitals (`"POLITIE"`); translations via `texts` |
| `name` | name on the server / live map |
| `color` | `#RRGGBB` |
| `icon` | built-in name (`police`, `ambulance`, `file`, `accident`, `works`, `obstacle`, `closure`, `speed`, `reroute`, `weather`, `bridge`, `cam_fixed`, `cam_mobile`, `cam_average`, `cam_anpr`, `wrongway`, `arrowboard`, `lane_closed`, …; = `icons/<naam>.svg`) or `"svg:<padData>"` (custom icon, viewBox 0 0 24 24, one colour, evenodd) |
| `life_min` | lifetime of your own report in the app (minutes) |
| `ttl_min` | lifetime of a shared report on the server |
| `merge_m` | reports of this type within this many metres are merged (server) |
| `report` | position in the REPORT screen (1, 2, …); `0` = not reportable |
| `report_key` | shorter key for the button in the REPORT screen (e.g. `"WERK"`) |
| `alert` | warn when you are driving towards it |
| `quiet` | spoken only, without a beep |
| `planned` | stricter "is it on my road" filter (works, closure) |
| `sound` | sound category (Settings > Sound per type): `POLITIE`, `HULPDIENST`, `FILE`, `ONGEVAL`, `WERKZAAMHEDEN`, `OBSTAKEL`, `AFSLUITING`, `SNELHEID`, `WEER`, `BRUG`, `FLITSPAAL`, `MOBIELE CONTROLE`, `TRAJECTCONTROLE`, `ANPR-CAMERA`, `SPOOKRIJDER` |

Special behaviour that is code stays attached to the existing ids: traffic jam (3) with length and line,
speed (8) as a temporary limit, bridge (11) + traffic jam merging. New types behave
like an ordinary point report.

Example — a new type "mobile radar" that you can report in Brazil and the Netherlands:

```json
{
  "report_areas": [[50.6, 3.2, 53.7, 7.3], [-34.0, -74.0, 6.0, -34.0]],
  "types": [
    {"id": 13, "key": "MOBIELE RADAR", "name": "Mobiele radar", "color": "#FF4A3D",
     "icon": "cam_mobile", "life_min": 60, "ttl_min": 60, "merge_m": 250, "report": 7,
     "report_key": "RADAR", "alert": true, "sound": "MOBIELE CONTROLE"}
  ],
  "texts": {
    "nl": {"MOBIELE RADAR": "Mobiele radar", "RADAR": "Radar"},
    "en": {"MOBIELE RADAR": "Mobile radar", "RADAR": "Radar"},
    "pt": {"MOBIELE RADAR": "Radar móvel", "RADAR": "Radar"}
  }
}
```

## Features (`flags`) and countries (`countries`)

`flags` turns features on/off on top of the user's setting (off = off even if the
user has it on): `community`, `report`, `ndw`, `msi`, `signs`, `buildings`, `nav`.
Overridable per country (ISO code): `"countries": {"BR": {"flags": {"nav": false}}}`.
The country is the country of the road map you are driving on at that moment (otherwise the device's region).

`report_areas`: rectangles `[min_lat, min_lon, max_lat, max_lon]` within which shared reports
may be created (server). The Netherlands only by default.

## Messages (`messages`)

A banner at the top of the app; tapping it away = gone for that message (per `id`).

```json
"messages": [
  {"id": "storing-20261120", "level": "warn",
   "title": {"nl": "Storing", "en": "Outage"},
   "text": {"nl": "Meldingen van anderen komen vertraagd binnen.", "en": "Reports from others are delayed."},
   "url": "https://example.org/status",
   "from": "2026-11-20T08:00:00Z", "until": "2026-11-20T20:00:00Z",
   "countries": ["NL", "BE"], "platforms": ["android", "ios", "dash"],
   "min_version": "2.9.0", "max_version": ""}
]
```

Everything except `id` and `text` is optional. `level`: `info` (blue), `warn` (orange), `alert` (red).
Language: `<language>-<region>` (e.g. `pt-BR`), then `<language>`, then `en`, then `nl`, then the first.
`platforms`: `android` = phone, `dash` = DASH01, `ios`. Versions compared like 2.9.0.

## Texts (`texts`)

Per language code a list of key → text; overrides the built-in text. The keys are the
app keys (`I18n.java`: `t("SLEUTEL", ...)`) and the label keys of reports (`"POLITIE"`,
`"FILE"`, new `key`s). Language codes: `nl`, `en`, `de`, `es`, `pt`, `fy`, plus regional variants
such as `pt-BR` (used when the app language is Portuguese and the device is set to Brazil).
