import os, struct, gzip, json, io
PROJ="$DASHPURE"
R=f"{PROJ}/initramfs/root"

def cpio_newc(root):
    out=bytearray(); ino=[300]
    def ent(name, mode, data=b"", nlink=1):
        ino[0]+=1
        name_b=name.encode()+b"\x00"
        hdr=b"070701"+ b"".join(b"%08X"%x for x in [
            ino[0], mode, 0,0, nlink, 0, len(data), 0,0,0,0, len(name_b), 0])
        out.extend(hdr); out.extend(name_b)
        out.extend(b"\x00"*((-len(hdr)-len(name_b))%4))
        out.extend(data); out.extend(b"\x00"*((-len(data))%4))
    entries=[]
    for dp,dn,fn in os.walk(root):
        rel=os.path.relpath(dp,root)
        if rel!=".":
            entries.append((rel, "dir", None))
        for f in sorted(fn+dn):
            full=os.path.join(dp,f); r=os.path.relpath(full,root)
            if os.path.islink(full):
                entries.append((r,"link",os.readlink(full)))
            elif os.path.isfile(full):
                entries.append((r,"file",full))
    seen=set()
    dirs=sorted([e for e in entries if e[1]=="dir"], key=lambda e:e[0].count("/"))
    for name,_,_ in dirs:
        ent(name, 0o040755, b"")
    for name,typ,val in entries:
        if typ=="file":
            data=open(val,"rb").read()
            mode=0o100755 if (name=="init" or name.startswith("bin/") or name.startswith("sbin/")) else 0o100644
            ent(name, mode, data)
        elif typ=="link":
            ent(name, 0o120777, val.encode())
    ent("TRAILER!!!", 0, b"")
    return bytes(out)

cpio=cpio_newc(R)
rd=gzip.compress(cpio,9)
open(f"{PROJ}/build/initramfs.cpio.gz","wb").write(rd)
print("initramfs.cpio.gz:", len(rd), "(cpio raw", len(cpio),")")

cfg=json.load(open(f"{PROJ}/kernel/bootparams.json"))
page=cfg["page_size"]
kernel=open(f"{PROJ}/kernel/kernel","rb").read()
dtb=open(f"{PROJ}/kernel/dtb","rb").read()
cmdline=(cfg["cmdline"]+" androidboot.selinux=permissive").encode()
assert len(cmdline)<512
def rup(x,p): return (x+p-1)//p*p
def pad(b): return b+b"\x00"*(rup(len(b),page)-len(b))
h=bytearray(page)
h[0:8]=b"ANDROID!"
struct.pack_into("<I",h,8,len(kernel)); struct.pack_into("<I",h,12,int(cfg["kernel_addr"],16))
struct.pack_into("<I",h,16,len(rd));     struct.pack_into("<I",h,20,int(cfg["ramdisk_addr"],16))
struct.pack_into("<I",h,24,0);           struct.pack_into("<I",h,28,int(cfg["second_addr"],16))
struct.pack_into("<I",h,32,int(cfg["tags_addr"],16))
struct.pack_into("<I",h,36,page)
struct.pack_into("<I",h,40,2)
struct.pack_into("<I",h,44,cfg["os_version"])
h[64:64+len(cmdline)]=cmdline
struct.pack_into("<I",h,1632,0)
struct.pack_into("<Q",h,1636,0)
struct.pack_into("<I",h,1644,1660)
struct.pack_into("<I",h,1648,len(dtb))
struct.pack_into("<Q",h,1652,int(cfg["dtb_addr"],16))
boot=bytes(h)+pad(kernel)+pad(rd)+pad(dtb)
open(f"{PROJ}/build/boot-pure.img","wb").write(boot)
print("boot-pure.img:", len(boot))
print("cmdline:", cmdline.decode())
