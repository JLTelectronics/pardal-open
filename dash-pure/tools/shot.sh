#!/bin/bash

B="${1:-ui2}"; SEL="$2"
PROJ="$(cd "$(dirname "$0")/.." && pwd)"
IFC=$(networksetup -listallhardwareports 2>/dev/null | awk '/DASH-PURE-NET/{getline;print $2}')
sudo ifconfig "$IFC" 10.0.0.2 netmask 255.255.255.0 up 2>/dev/null
printf 'nc -lp 5007 > /tmp/n; killall ui 2>/dev/null; sleep 1; mv /bin/ui /bin/ui_b 2>/dev/null; cp /tmp/n /bin/ui; chmod 755 /bin/ui; rm -f /bin/ui_b; killall ui 2>/dev/null; sleep 2; echo UP=$(pidof ui); sleep 1; dd if=/dev/fb0 bs=4096 count=225 2>/dev/null|gzip -9>/tmp/fb.gz; (nc -lp 5008 < /tmp/fb.gz &); echo SERVE\n' | nc -w 25 10.0.0.1 2323 > /tmp/sh.out 2>/dev/null &
sleep 3
cat "$PROJ/build/$B" | nc -w 8 10.0.0.1 5007 2>/dev/null
for i in $(seq 1 18); do grep -q SERVE /tmp/sh.out 2>/dev/null && break; sleep 1; done
sleep 1; nc -w 8 10.0.0.1 5008 > /tmp/fb.gz 2>/dev/null
gunzip -c /tmp/fb.gz > /tmp/fb.raw 2>/dev/null
python3 -c "d=open('/tmp/fb.raw','rb').read();open('/tmp/fb.ppm','wb').write(b'P6\n480 480\n255\n'+b''.join(bytes(d[i:i+3]) for i in range(0,921600,4)))" 2>/dev/null
sips -s format png /tmp/fb.ppm --out "$PROJ/build/screenshot.png" 2>/dev/null >/dev/null
echo "$(cat /tmp/sh.out|grep UP) PNG=$(ls -l "$PROJ/build/screenshot.png" 2>/dev/null|awk '{print $5}')b"
