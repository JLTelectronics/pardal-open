#!/bin/bash

set -uo pipefail
cd "$(dirname "$0")"
set -a; [ -f adsb.env ] && . ./adsb.env; set +a
DEVICE="${DEVICE:?zet DEVICE=<serienummer> in adsb.env (rtl_test)}"
exec ./readsb/readsb --device-type rtlsdr --device "$DEVICE" --gain "${GAIN:-auto}" \
  --net --net-api-port 8042 --net-bind-address 0.0.0.0 --quiet ${LAT:+--lat "$LAT" --lon "$LON"}
