# Pardal server

Self-hostable backend for Pardal: shared reports, the live map, the online counter, official road alerts,
navigation (geocoding + routing) and remote app configuration. FastAPI + SQLite.

## Quick start
```sh
cd server
docker compose up -d --build
```

This starts two containers:
- **roadping** — the API and live map on port `8095` (bound to `${BIND}`, default `127.0.0.1`).
- **roadping-valhalla** — the [Valhalla](https://github.com/valhalla/valhalla) route planner, reachable only
  internally. On first start it builds route tiles from OpenStreetMap (Netherlands, ~3–4 GB in `./valhalla`).

Data (SQLite database and salt) is stored in `./data`. Put a reverse proxy with TLS (e.g. Caddy) in front of
port 8095. Make sure the proxy sees the real client IP address: some anti-abuse rules use it.

Then point the app to your server under **Settings → Report server**.

## Configuration
Settings are passed as environment variables, for example in a `.env` file next to `docker-compose.yml`
(not in git):

| Variable | Meaning |
|---|---|
| `BIND` | Address the API listens on (default `127.0.0.1`). |
| `ROADPING_MIN_CONFIRM` | Reports needed before a report is visible to others (default `3`). |
| `ROADPING_MIN_GONE` | "Gone" votes needed to remove a report (default `2`). |
| `ROADPING_ADSB_URL` | Your own ADS-B receiver API (optional; empty = public source). |

App behaviour (report types, features per country, banners, texts) can be changed without an app update
via `data/config.json`. See [docs/config.md](../docs/config.md).

## Folder layout
| Folder | Contents |
|---|---|
| `app/` | The FastAPI application (`main.py`) and data sources: NDW, matrix signs, cameras, weather, Europe, air traffic. |
| `app/static/` | Live map, privacy and support pages. |
| `sdr/` | Optional ADS-B / AIS receivers (RTL-SDR). |

## ADS-B / AIS receivers (optional)
Build with `sdr/bouw-readsb.sh` / `sdr/bouw-ais.sh`, set `DEVICE=<serial>` in `sdr/adsb.env`, and run
`sdr/adsb.sh` / `sdr/ais.sh`. Set `ROADPING_ADSB_URL` to the receiver's API (port 8042).

## Third-party software
The map uses [Leaflet](https://leafletjs.com) (loaded from unpkg), and bundles MapLibre GL JS and
MapLibre GL Leaflet in `app/static/vendor/` — see [`LICENSES.txt`](app/static/vendor/LICENSES.txt).

## Privacy
Device IDs are random and stored hashed, positions for the online counter are rounded to ~1 km and kept in
memory only, and IP addresses are only stored hashed with a secret salt. See
[docs/play/privacyverklaring.md](../docs/play/privacyverklaring.md).
