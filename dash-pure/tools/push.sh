#!/bin/bash

N="$1"; shift; ARGS="$*"
PROJ="$(cd "$(dirname "$0")/.." && pwd)"
IFC=$(networksetup -listallhardwareports 2>/dev/null | awk '/DASH-PURE-NET/{getline;print $2}')
[ -n "$IFC" ] && sudo ifconfig "$IFC" 10.0.0.2 netmask 255.255.255.0 up 2>/dev/null
printf "killall %s 2>/dev/null; nc -lp 5005 > /tmp/%s; chmod +x /tmp/%s; echo RECV=\$(wc -c </tmp/%s)\n" "$N" "$N" "$N" "$N" | nc -w 20 10.0.0.1 2323 &
sleep 2
cat "$PROJ/build/$N" | nc -w 8 10.0.0.1 5005
sleep 1
printf "killall ui 2>/dev/null; /tmp/%s %s 2>&1 &\n" "$N" "$ARGS" | nc -w 4 10.0.0.1 2323
echo "gepusht + gestart: $N $ARGS"
