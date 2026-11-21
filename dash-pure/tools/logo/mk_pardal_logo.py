#!/usr/bin/env python3
import sys, struct, zlib
from PIL import Image, ImageDraw, ImageFont

def render():
    im = Image.new('RGB', (480, 480), (0, 0, 0)); d = ImageDraw.Draw(im)
    F = lambda s: ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', s, index=1)
    f = F(62)
    w = d.textlength('Pardal', font=f)
    d.text((240 - w / 2, 252), 'Pardal', font=f, fill=(245, 245, 245), anchor='ls')
    d.rounded_rectangle((165, 267, 315, 273), radius=3, fill=(255, 106, 26))
    f2 = F(19); w2 = d.textlength('dash', font=f2)
    d.text((240 - w2 / 2, 303), 'dash', font=f2, fill=(150, 150, 150), anchor='ls')
    return im

def zlib_exact(raw, target):
    for k in range(1, 60000):
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        body = c.compress(raw[:-k]) + c.flush(zlib.Z_SYNC_FLUSH)
        tail = raw[-k:]
        out = b'\x78\xda' + body + b'\x01' + struct.pack('<HH', k, k ^ 0xffff) + tail + struct.pack('>I', zlib.adler32(raw))
        if len(out) == target:
            assert zlib.decompress(out) == raw
            return out
        if len(out) > target and k > 1:
            break
    raise SystemExit('past niet in slot van %d bytes' % target)

def main():
    src, dst = sys.argv[1], sys.argv[2]
    img = bytearray(open(src, 'rb').read())
    b0 = 0x200
    cnt, bs = struct.unpack('<II', img[b0:b0 + 8])
    offs = list(struct.unpack('<%dI' % cnt, img[b0 + 8:b0 + 8 + 4 * cnt])) + [bs]
    im = render()
    if len(sys.argv) > 3: im.save(sys.argv[3])
    raw = im.convert('RGBA').tobytes('raw', 'BGRA')
    for i in (0, 16):
        a, e = offs[i], offs[i + 1]
        z = zlib_exact(raw, e - a)
        img[b0 + a:b0 + e] = z
        print('idx %d: slot %d bytes ok' % (i, e - a))
    open(dst, 'wb').write(img)

main()
