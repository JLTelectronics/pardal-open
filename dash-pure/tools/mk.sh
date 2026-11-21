#!/bin/bash
set -e
N="$1"; [ -z "$N" ] && { echo "usage: mk.sh <name>"; exit 1; }
PROJ="$(cd "$(dirname "$0")/.." && pwd)"
CC="${CC:-aarch64-linux-musl-gcc}"
STRIP="${STRIP:-${CC%gcc}strip}"
mkdir -p "$PROJ/build"
"$CC" -Os -static -I"$PROJ/src" "$PROJ/src/$N.c" -o "$PROJ/build/$N"
"$STRIP" "$PROJ/build/$N" 2>/dev/null || true
chmod +x "$PROJ/build/$N"
echo "build/$N: $(ls -l "$PROJ/build/$N" | awk '{print $5}') bytes"
