#!/usr/bin/env python3
import sys,struct
def ev(t,c,v): return struct.pack('<qqHHi',0,0,t,c,v)
def esc(b): return ''.join('\\%03o'%x for x in b)
EV_SYN,EV_KEY,EV_ABS=0,1,3; BTN_TOUCH=330
def down(x,y): return ev(EV_ABS,0x30,5)+ev(EV_ABS,0x35,x)+ev(EV_ABS,0x36,y)+ev(EV_ABS,0x39,0)+ev(EV_SYN,2,0)+ev(EV_KEY,BTN_TOUCH,1)+ev(EV_SYN,0,0)
def move(x,y): return ev(EV_ABS,0x30,5)+ev(EV_ABS,0x35,x)+ev(EV_ABS,0x36,y)+ev(EV_ABS,0x39,0)+ev(EV_SYN,2,0)+ev(EV_SYN,0,0)
up=ev(EV_KEY,BTN_TOUCH,0)+ev(EV_SYN,2,0)+ev(EV_SYN,0,0)
a=list(map(int,sys.argv[1:]))
D='/dev/input/event2'
if len(a)==2:
    print(f"printf '{esc(down(*a))}' > {D}; usleep 80000; printf '{esc(up)}' > {D}; echo tap")
else:
    x1,y1,x2,y2=a; n=10; parts=[f"printf '{esc(down(x1,y1))}' > {D}"]
    for i in range(1,n+1): parts.append(f"usleep 20000; printf '{esc(move(x1+(x2-x1)*i//n,y1+(y2-y1)*i//n))}' > {D}")
    parts.append(f"printf '{esc(up)}' > {D}; echo swipe"); print('; '.join(parts))
