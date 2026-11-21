#!/usr/bin/env python3
import sys, os, io, zipfile, importlib.util
from PIL import Image, ImageDraw
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ml', os.path.join(here, 'mk_pardal_logo.py'))
src = open(os.path.join(here, 'mk_pardal_logo.py')).read().replace('\nmain()\n', '\n')
ml = {}; exec(compile(src, 'mk_pardal_logo.py', 'exec'), ml)
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
base = ml['render']()
open(os.path.join(out, 'pardal-splash.raw'), 'wb').write(base.convert('RGBA').tobytes('raw', 'BGRA'))
BX, BY, BW, SW, FPS, PER = 200, 336, 80, 24, 30, 1400
z = io.BytesIO(); zf = zipfile.ZipFile(z, 'w', zipfile.ZIP_STORED)
zf.writestr('desc.txt', '480 480 %d\nc 0 0 part0\n' % FPS)
n = FPS * PER // 1000
for i in range(n):
    ms = i * 1000 // FPS; ph = ms % PER
    pos = ph * (BW - SW) // (PER // 2) if ph < PER // 2 else (PER - ph) * (BW - SW) // (PER // 2)
    im = base.copy(); d = ImageDraw.Draw(im)
    d.rectangle((BX, BY, BX + BW - 1, BY + 3), fill=(38, 38, 38))
    d.rectangle((BX + pos, BY, BX + pos + SW - 1, BY + 3), fill=(255, 106, 26))
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True)
    zf.writestr('part0/%03d.png' % i, b.getvalue())
zf.close(); open(os.path.join(out, 'pardal-boot.zip'), 'wb').write(z.getvalue())
print('frames', n, 'zip', len(z.getvalue()))
