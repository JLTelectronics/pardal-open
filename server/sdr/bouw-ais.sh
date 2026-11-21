#!/bin/bash

set -euo pipefail
cd "$(dirname "$0")"
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH
for p in librtlsdr cmake pkgconf; do brew list $p >/dev/null 2>&1 || brew install $p; done
[ -d AIS-catcher ] || git clone --depth 1 https://github.com/jvde-github/AIS-catcher.git
cd AIS-catcher && mkdir -p build && cd build && cmake .. && make -j4 && echo "klaar: $(pwd)/AIS-catcher"
