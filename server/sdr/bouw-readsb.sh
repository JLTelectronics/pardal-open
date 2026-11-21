#!/bin/bash

set -euo pipefail
cd "$(dirname "$0")"
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH
brew list librtlsdr >/dev/null 2>&1 || brew install librtlsdr
brew list pkgconf >/dev/null 2>&1 || brew install pkgconf
brew list zstd >/dev/null 2>&1 || brew install zstd
[ -d readsb ] || git clone --depth 1 https://github.com/wiedehopf/readsb.git
cd readsb && make -j4 RTLSDR=yes && echo "klaar: $(pwd)/readsb"
