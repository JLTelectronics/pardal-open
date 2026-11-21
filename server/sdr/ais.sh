#!/bin/bash

set -uo pipefail
cd "$(dirname "$0")"
set -a; [ -f ais.env ] && . ./ais.env; set +a
DEVICE="${DEVICE:?zet DEVICE=<serienummer> in ais.env (rtl_test)}"
exec ./AIS-catcher/build/AIS-catcher -d:"$DEVICE" -N 8100 -q
