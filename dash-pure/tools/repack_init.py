#!/usr/bin/env python3
import sys, struct, gzip, hashlib
src, newinit, dst = sys.argv[1:4]
img = open(src, 'rb').read()
assert img[:8] == b'ANDROID!'
ks, ka, rs, ra, ss, sa, ta, page, hv = struct.unpack_from('<9I', img, 8)
def rup(x): return (x + page - 1) // page * page
koff = page; roff = koff + rup(ks); soff = roff + rup(rs)
kernel = img[koff:koff+ks]; rd = img[roff:roff+rs]; second = img[soff:soff+ss]
off = soff + rup(ss)
extra = b''
dtbo_size = dtb_size = 0
if hv >= 1:
    dtbo_size = struct.unpack_from('<I', img, 1632)[0]
if hv >= 2:
    dtb_size = struct.unpack_from('<I', img, 1648)[0]
dtbo = img[off:off+dtbo_size]; off += rup(dtbo_size)
dtb = img[off:off+dtb_size]
cpio = gzip.decompress(rd)
out = bytearray(); i = 0; replaced = False
while True:
    h = cpio[i:i+110]; assert h[:6] == b'070701', 'geen newc'
    f = [int(h[6+8*k:14+8*k], 16) for k in range(13)]
    fsize, nsize = f[6], f[11]
    name = cpio[i+110:i+110+nsize-1].decode()
    dstart = (i + 110 + nsize + 3) // 4 * 4
    data = cpio[dstart:dstart+fsize]
    nxt = (dstart + fsize + 3) // 4 * 4
    if name == 'init':
        data = open(newinit, 'rb').read(); f[6] = len(data); replaced = True
        hdr = b'070701' + b''.join(b'%08X' % x for x in f)
        nb = name.encode() + b'\0'
        out += hdr + nb + b'\0' * ((-(110 + len(nb))) % 4) + data + b'\0' * ((-len(data)) % 4)
    else:
        out += cpio[i:nxt]
    i = nxt
    if name == 'TRAILER!!!': break
assert replaced, 'init niet gevonden'
newrd = gzip.compress(bytes(out), 9)
hdr = bytearray(img[:page])
struct.pack_into('<I', hdr, 16, len(newrd))
sha = hashlib.sha1()
for blob in (kernel, newrd, second) + ((dtbo,) if hv >= 1 else ()) + ((dtb,) if hv >= 2 else ()):
    sha.update(blob); sha.update(struct.pack('<I', len(blob)))
hdr[576:608] = sha.digest().ljust(32, b'\0')
def pad(b): return b + b'\0' * (rup(len(b)) - len(b))
res = bytes(hdr) + pad(kernel) + pad(newrd) + pad(second)
if hv >= 1: res += pad(dtbo)
if hv >= 2: res += pad(dtb)
open(dst, 'wb').write(res)
print(f'hv={hv} page={page} kernel={ks} ramdisk {rs}->{len(newrd)} dtb={dtb_size} out={len(res)}')
