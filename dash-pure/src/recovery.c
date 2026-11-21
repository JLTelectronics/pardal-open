#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <poll.h>
#include <time.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <sys/reboot.h>
#include "font.h"

struct fbv{uint32_t xres,yres,xv,yv,xo,yo,bpp,gray;uint32_t r[3],g[3],b[3],a[3];uint32_t nonstd,act,h,w,acc,pix,lm,rm,um,lo,hl,vl,sync,vmode,rot,cs,res[4];};
struct fbf{char id[16];unsigned long ss;uint32_t sl,t,ta,v;uint16_t xp,yp,yw;uint32_t ll;unsigned long ms;uint32_t ml,ac;uint16_t cap,r2[2];};
#define GV 0x4600
#define GF 0x4602
#define PAN 0x4606
struct iev{long s,u;uint16_t type,code;int32_t val;};

static uint8_t *fb; static int LL, W, H, BPP, fbfd; static struct fbv V;

#define BG      0xFF0B0D10
#define WIT     0xFFF2F4F6
#define DIM     0xFF8A9099
#define ORANJE  0xFFFF7A2E
#define ROOD    0xFFE5484D
#define GROEN   0xFF4CD27A
#define KNOP    0xFF1C2128
#define KNOPRND 0xFF2C333D

static void px(int x,int y,uint32_t c){ if(x<0||y<0||x>=W||y>=H) return; *(uint32_t*)(fb+(long)y*LL+x*(BPP/8))=c; }
static void rect(int x,int y,int w,int h,uint32_t c){ for(int j=0;j<h;j++) for(int i=0;i<w;i++) px(x+i,y+j,c); }
static void frect(int x,int y,int w,int h,int r,uint32_t c){
  for(int j=0;j<h;j++) for(int i=0;i<w;i++){ int dx=0,dy=0;
    if(i<r&&j<r){dx=r-1-i;dy=r-1-j;} else if(i>=w-r&&j<r){dx=i-(w-r);dy=r-1-j;}
    else if(i<r&&j>=h-r){dx=r-1-i;dy=j-(h-r);} else if(i>=w-r&&j>=h-r){dx=i-(w-r);dy=j-(h-r);}
    if(dx*dx+dy*dy<=r*r) px(x+i,y+j,c); } }
static void ring(int cx,int cy,int r,int t,uint32_t c){
  for(int y=-r;y<=r;y++) for(int x=-r;x<=r;x++){ int d=x*x+y*y; if(d<=r*r && d>=(r-t)*(r-t)) px(cx+x,cy+y,c); } }
static void glyph(int x,int y,char ch,uint32_t c,int s){ if(ch<32||ch>126) return; const unsigned char*g=FONT[ch-32];
  for(int row=0;row<FONT_H;row++){ unsigned char b=g[row]; for(int col=0;col<FONT_W;col++) if(b&(0x80>>col)) rect(x+col*s,y+row*s,s,s,c);} }
static int tw(const char*t,int s){ return strlen(t)*FONT_W*s; }
static void text(int x,int y,const char*t,uint32_t c,int s){ for(;*t;t++){ glyph(x,y,*t,c,s); x+=FONT_W*s; } }
static void ctext(int cx,int y,const char*t,uint32_t c,int s){ text(cx-tw(t,s)/2,y,t,c,s); }
static void flip(void){ V.yo=0; V.act=128; ioctl(fbfd,PAN,&V); }
static void rdstr(const char*p,char*b,int n){ int f=open(p,O_RDONLY); b[0]=0; if(f>=0){ int r=read(f,b,n-1); if(r>0){ b[r]=0; for(int i=0;i<r;i++) if(b[i]=='\n'){b[i]=0;break;} } close(f);} }

static int tf=-1;
static int wait_tap(int ms,int*tx,int*ty){
  struct pollfd p={.fd=tf,.events=POLLIN}; struct iev e; int x=-1,y=-1,down=0;
  long start=0; struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); start=ts.tv_sec*1000+ts.tv_nsec/1000000;
  for(;;){
    int left=-1;
    if(ms>=0){ clock_gettime(CLOCK_MONOTONIC,&ts); long now=ts.tv_sec*1000+ts.tv_nsec/1000000; left=ms-(int)(now-start); if(left<=0) return 0; }
    if(poll(&p,1,left)<=0) { if(ms>=0) return 0; continue; }
    while(read(tf,&e,sizeof e)==sizeof e){
      if(e.type==3){ if(e.code==0x35) x=e.val; if(e.code==0x36) y=e.val; }
      if(e.type==1 && e.code==0x14a){ if(e.val==1) down=1; else if(down){ *tx=x; *ty=y; return 1; } }
    }
  }
}
static void drain(void){ struct iev e; struct pollfd p={.fd=tf,.events=POLLIN}; while(poll(&p,1,150)>0) if(read(tf,&e,sizeof e)<=0) break; }

static void logo(int y){ ring(W/2,y,34,5,ORANJE); ctext(W/2,y-16,"D",WIT,2); }

#define KR 22
#define KHIT 60
static void kruisje(uint32_t c){
  for(int t=-KR;t<=KR;t++) for(int d=-2;d<=2;d++){ px(W/2+t+d,H/2+t,c); px(W/2+t+d,H/2-t,c); }
}
static void scherm_countdown(int s,int n){
  rect(0,0,W,H,BG);
  ring(W/2,H/2,44,2,0xFF2A2A2A);
  kruisje(s==n?WIT:DIM);
  flip();
}

#define NMENU 6
static const char*MENU[NMENU]={"Android starten","Opnieuw opstarten","Uitzetten","Android-data wissen","Info","Pure-menu"};
static const int MY0=92, MH=46, MG=8, MW=300;
static void scherm_menu(const char*melding){
  rect(0,0,W,H,BG);
  ctext(W/2,40,"HERSTELMENU",ORANJE,2);
  for(int i=0;i<NMENU;i++){
    int y=MY0+i*(MH+MG); uint32_t kl = i==0?ORANJE : i==3?0xFF3A1E21 : KNOP;
    frect(W/2-MW/2,y,MW,MH,23,kl);
    ctext(W/2,y+(MH-32)/2+8,MENU[i], i==0?0xFF141414 : i==3?ROOD : WIT, 2);
  }
  if(melding) ctext(W/2,MY0+NMENU*(MH+MG)+6,melding,GROEN,1);
  flip();
}
static int menu_hit(int x,int y){
  if(x<W/2-MW/2||x>W/2+MW/2) return -1;
  for(int i=0;i<NMENU;i++){ int yy=MY0+i*(MH+MG); if(y>=yy&&y<yy+MH) return i; }
  return -1;
}
static int bevestig(const char*vraag,const char*regel2){
  rect(0,0,W,H,BG);
  ctext(W/2,110,vraag,WIT,2); ctext(W/2,146,regel2,DIM,1);
  frect(W/2-150,200,140,64,32,ROOD); ctext(W/2-80,224,"JA",WIT,2);
  frect(W/2+10,200,140,64,32,KNOP);  ctext(W/2+80,224,"NEE",WIT,2);
  flip(); drain();
  int x,y; if(!wait_tap(15000,&x,&y)) return 0;
  return (y>=200&&y<264&&x<W/2);
}
static void scherm_info(void){
  char b[96],c[32],ip[64]="?",lk[64],pak[96],up[32];
  rect(0,0,W,H,BG); ctext(W/2,60,"INFO",ORANJE,2);
  rdstr("/sys/class/power_supply/battery/capacity",c,sizeof c);
  rdstr("/sys/kernel/ccci/lk_md",lk,sizeof lk);
  rdstr("/proc/uptime",up,sizeof up); for(char*q=up;*q;q++) if(*q=='.'){*q=0;break;}
  FILE*f=popen("ip addr show usb0 2>/dev/null | grep -o 'inet [0-9.]*' | cut -d' ' -f2","r"); if(f){ if(fgets(ip,sizeof ip,f)) ip[strcspn(ip,"\n")]=0; pclose(f); }
  f=popen("dd if=/dev/mmcblk0p53 bs=4096 skip=917504 count=1 2>/dev/null | head -3 | tr '\\n' ' '","r");
  pak[0]=0; if(f){ if(!fgets(pak,sizeof pak,f)) pak[0]=0; pclose(f); }
  int y=110, lh=34;
  snprintf(b,sizeof b,"accu   %s%%",c[0]?c:"?"); ctext(W/2,y,b,GROEN,2); y+=lh;
  snprintf(b,sizeof b,"usb    %s",ip); ctext(W/2,y,b,WIT,2); y+=lh;
  snprintf(b,sizeof b,"uptime %s s",up); ctext(W/2,y,b,WIT,2); y+=lh;
  ctext(W/2,y,strstr(lk,"Enabled")?"modem  geladen":"modem  niet geladen",strstr(lk,"Enabled")?GROEN:ROOD,2); y+=lh+6;
  pak[40]=0; ctext(W/2,y,pak[0]?pak:"geen pakket",DIM,1); y+=24;
  ctext(W/2,y,"DASH-PURE recovery",DIM,1);
  ctext(W/2,H-70,"tik om terug te gaan",ORANJE,1);
  flip(); drain(); int x,yy; wait_tap(60000,&x,&yy);
}
static void bericht(const char*t){ rect(0,0,W,H,BG); logo(170); ctext(W/2,240,t,WIT,2); flip(); }

static int wis_data(void){
  int f=open("/dev/mmcblk0p53",O_WRONLY); if(f<0) return 0;
  static char nul[65536]; off_t off=4294967296LL; int ok=1;
  for(int i=0;i<16;i++){ if(pwrite(f,nul,sizeof nul,off+(off_t)i*sizeof nul)!=sizeof nul){ ok=0; break; } }
  fsync(f); close(f); sync(); return ok;
}

static int menu_loop(void){
  const char*melding=NULL;
  for(;;){
    scherm_menu(melding); melding=NULL; drain();
    int x,y; if(!wait_tap(-1,&x,&y)) continue;
    switch(menu_hit(x,y)){
      case 0: bericht("Android start..."); return 0;
      case 1: bericht("Opnieuw opstarten..."); sync(); sleep(1); reboot(RB_AUTOBOOT); break;
      case 2: bericht("Uitzetten..."); sync(); sleep(1); reboot(RB_POWER_OFF); break;
      case 3:
        if(bevestig("Android-data wissen?","apps/instellingen weg; eSIM blijft")){
          bericht("Wissen..."); melding = wis_data() ? "Android-data gewist" : "WISSEN MISLUKT";
        }
        break;
      case 4: scherm_info(); break;
      case 5: return 2;
    }
  }
}

static int sf_draait(void){
  char p[64],b[32]; for(int pid=2;pid<40000;pid++){ snprintf(p,sizeof p,"/proc/%d/comm",pid);
    int f=open(p,O_RDONLY); if(f<0) continue; int r=read(f,b,sizeof b-1); close(f);
    if(r>0){ b[r]=0; if(!strncmp(b,"surfaceflinger",14)) return 1; } }
  return 0;
}
static int splash(const char*raw){
  int f=open(raw,O_RDONLY); if(f<0) return 1;
  static uint8_t img[480*480*4]; int n=0,r; while(n<(int)sizeof img && (r=read(f,img+n,sizeof img-n))>0) n+=r; close(f);
  if(n!=(int)sizeof img) return 1;
  int ox=(W-480)/2, oy=(H-480)/2;
  rect(0,0,W,H,0xFF000000);
  for(int y=0;y<480;y++) for(int x=0;x<480;x++){ uint32_t c=*(uint32_t*)(img+(y*480+x)*4)|0xFF000000; px(ox+x,oy+y,c); }
  const int BX=ox+200, BY=oy+336, BW=80, SW=24;
  struct timespec t0,t; clock_gettime(CLOCK_MONOTONIC,&t0);
  for(int i=0;;i++){
    clock_gettime(CLOCK_MONOTONIC,&t); long ms=(t.tv_sec-t0.tv_sec)*1000+(t.tv_nsec-t0.tv_nsec)/1000000;
    if(ms>240000) break;
    if(i%15==0 && sf_draait()) break;
    int per=1400, ph=ms%per; int pos = ph<per/2 ? ph*(BW-SW)/(per/2) : (per-ph)*(BW-SW)/(per/2);
    rect(BX,BY,BW,4,0xFF262626); rect(BX+pos,BY,SW,4,0xFFFF6A1A);
    flip(); usleep(33000);
  }
  return 0;
}

int main(int argc,char**argv){
  fbfd=open("/dev/fb0",O_RDWR); if(fbfd<0) return 0;
  struct fbf F; ioctl(fbfd,GV,&V); ioctl(fbfd,GF,&F);
  W=V.xres; H=V.yres; BPP=V.bpp; LL=F.ll; long sz=(long)LL*V.yv; if(sz<F.sl) sz=F.sl;
  fb=mmap(0,sz,PROT_READ|PROT_WRITE,MAP_SHARED,fbfd,0); if(fb==MAP_FAILED) return 0;
  if(argc>2 && !strcmp(argv[1],"splash")) return splash(argv[2]);
  tf=open("/dev/input/event2",O_RDONLY|O_NONBLOCK);
  if(tf<0) return 0;
  if(argc>1 && !strcmp(argv[1],"countdown")){
    int n = argc>2 ? atoi(argv[2]) : 3; drain();
    long eind; { struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); eind=ts.tv_sec*1000+ts.tv_nsec/1000000+n*1000L; }
    scherm_countdown(n,n);
    for(;;){
      struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); long nu=ts.tv_sec*1000+ts.tv_nsec/1000000;
      if(nu>=eind) break;
      int x,y;
      if(wait_tap((int)(eind-nu),&x,&y)){
        int dx=x-W/2, dy=y-H/2;
        if(dx*dx+dy*dy<=KHIT*KHIT) return menu_loop();
      }
    }
    rect(0,0,W,H,BG); flip(); return 0;
  }
  return menu_loop();
}
