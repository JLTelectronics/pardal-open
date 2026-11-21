#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <poll.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include "font.h"
struct fbv{uint32_t xres,yres,xv,yv,xo,yo,bpp,gray;uint32_t r[3],g[3],b[3],a[3];uint32_t nonstd,act,h,w,acc,pix,lm,rm,um,lo,hl,vl,sync,vmode,rot,cs,res[4];};
struct fbf{char id[16];unsigned long ss;uint32_t sl,t,ta,v;uint16_t xp,yp,yw;uint32_t ll;unsigned long ms;uint32_t ml,ac;uint16_t cap,r2[2];};
#define GV 0x4600
#define GF 0x4602
#define PAN 0x4606
struct iev{long s,u;uint16_t type,code;int32_t val;};
static uint8_t*fb;static int LL,W,H,BPP,fbfd;static struct fbv V;
static void px(int x,int y,uint32_t c){if(x<0||y<0||x>=W||y>=H)return;*(uint32_t*)(fb+(long)y*LL+x*(BPP/8))=c;}
static void rect(int x,int y,int w,int h,uint32_t c){for(int j=0;j<h;j++)for(int i=0;i<w;i++)px(x+i,y+j,c);}
static void frect(int x,int y,int w,int h,int r,uint32_t c){for(int j=0;j<h;j++)for(int i=0;i<w;i++){int dx=0,dy=0;
  if(i<r&&j<r){dx=r-1-i;dy=r-1-j;}else if(i>=w-r&&j<r){dx=i-(w-r);dy=r-1-j;}
  else if(i<r&&j>=h-r){dx=r-1-i;dy=j-(h-r);}else if(i>=w-r&&j>=h-r){dx=i-(w-r);dy=j-(h-r);}
  if(dx*dx+dy*dy<=r*r)px(x+i,y+j,c);}}
static void glyph(int x,int y,char ch,uint32_t c,int s){if(ch<32||ch>126)return;const unsigned char*g=FONT[ch-32];
  for(int row=0;row<FONT_H;row++){unsigned char b=g[row];for(int col=0;col<FONT_W;col++)if(b&(0x80>>col))rect(x+col*s,y+row*s,s,s,c);}}
static int tw(const char*t,int s){return strlen(t)*FONT_W*s;}
static void text(int x,int y,const char*t,uint32_t c,int s){for(;*t;t++){glyph(x,y,*t,c,s);x+=FONT_W*s;}}
static void ctext(int cx,int y,const char*t,uint32_t c,int s){text(cx-tw(t,s)/2,y,t,c,s);}
static void flip(){V.yo=0;V.act=128;ioctl(fbfd,PAN,&V);}
static void rdstr(const char*p,char*b,int n){int f=open(p,O_RDONLY);b[0]=0;if(f>=0){int r=read(f,b,n-1);if(r>0){b[r]=0;for(int i=0;i<r;i++)if(b[i]=='\n'){b[i]=0;break;}}close(f);}}
static int rdint(const char*p){char b[32];rdstr(p,b,sizeof b);return atoi(b);}
static void wrint(const char*p,int v){int f=open(p,O_WRONLY);if(f>=0){char b[16];int n=snprintf(b,sizeof b,"%d",v);write(f,b,n);close(f);}}
#define BG   0xFF14100A
#define IVORY 0xFFE8F0F3
#define DIM  0xFF8A8A80
#define BL "/sys/class/leds/lcd-backlight/brightness"
static const char*APP[4]={"PARDAL","GPS","WIFI","INFO"};
static uint32_t ACC[4]={0xFF2B6AFF,0xFF6ACF3F,0xFF4EB0F0,0xFFE77B9A};
static int TX[4],TY[4],TW,TH;
static void statusbar(){
  char t[32],cap[16];rdstr("/sys/class/rtc/rtc0/time",t,sizeof t);t[5]=0;
  rdstr("/sys/class/power_supply/battery/capacity",cap,sizeof cap);
  char bat[16];snprintf(bat,sizeof bat,"%s%%",cap[0]?cap:"?");
  text(24,16,t[0]?t:"--:--",IVORY,2);
  text(W-24-tw(bat,2),16,bat,0xFF6ACF3F,2);
}
static void draw_home(int sel){
  rect(0,0,W,H,BG);statusbar();
  ctext(W/2,52,"DASH-PURE",IVORY,2);
  for(int i=0;i<4;i++){
    if(i==sel)frect(TX[i]-6,TY[i]-6,TW+12,TH+12,30,IVORY);
    frect(TX[i],TY[i],TW,TH,24,ACC[i]);
    ctext(TX[i]+TW/2,TY[i]+TH/2-8,APP[i],0xFF141414,2);
  }
  ctext(W/2,H-26,"tik balk = licht",DIM,1);
  flip();
}
static void draw_info(){
  char up[64],cap[16];rdstr("/proc/uptime",up,sizeof up);for(char*q=up;*q;q++)if(*q==' '){*q=0;break;}
  rdstr("/sys/class/power_supply/battery/capacity",cap,sizeof cap);
  rect(0,0,W,H,BG);ctext(W/2,24,"DEVICE INFO",IVORY,2);
  int y=76,lh=26;char b[64];
  text(28,y,"MT6771  480x480  RGBA",IVORY,1);y+=lh;
  text(28,y,"kernel 4.19.191",DIM,1);y+=lh;
  snprintf(b,sizeof b,"uptime %ss",up);text(28,y,b,DIM,1);y+=lh;
  snprintf(b,sizeof b,"battery %s%%",cap);text(28,y,b,0xFF6ACF3F,1);y+=lh;
  text(28,y,"DASH-PURE / Lume-stijl",IVORY,1);y+=lh;
  text(28,y,"eigen OS, geen Android",DIM,1);
  ctext(W/2,H-40,"tik om terug te gaan",DIM,1);flip();
}
static void draw_light(){
  int b=rdint(BL),pct=b*100/255;
  rect(0,0,W,H,BG);ctext(W/2,24,"HELDERHEID",IVORY,2);
  char v[16];snprintf(v,sizeof v,"%d%%",pct);ctext(W/2,70,v,0xFF6ACF3F,3);
  int bw=170,bh=170,gy=130;
  frect(30,gy,bw,bh,24,0xFF3A3A44);ctext(30+bw/2,gy+bh/2-24,"DIM",IVORY,3);ctext(30+bw/2,gy+bh/2+16,"-",IVORY,3);
  frect(W-30-bw,gy,bw,bh,24,0xFFF0B04E);ctext(W-30-bw/2,gy+bh/2-24,"MAX",0xFF141414,3);ctext(W-30-bw/2,gy+bh/2+16,"+",0xFF141414,3);
  ctext(W/2,H-40,"tik onder = terug",DIM,1);flip();
}
int main(int argc,char**argv){
  fbfd=open("/dev/fb0",O_RDWR);if(fbfd<0)return 1;
  struct fbf F;ioctl(fbfd,GV,&V);ioctl(fbfd,GF,&F);
  W=V.xres;H=V.yres;BPP=V.bpp;LL=F.ll;long sz=(long)LL*V.yv;if(sz<F.sl)sz=F.sl;
  fb=mmap(0,sz,PROT_READ|PROT_WRITE,MAP_SHARED,fbfd,0);if(fb==MAP_FAILED)return 1;
  int m=22,top=78;TW=(W-3*m)/2;TH=(H-top-m-40-m)/2;
  TX[0]=m;TY[0]=top;TX[1]=2*m+TW;TY[1]=top;TX[2]=m;TY[2]=top+m+TH;TX[3]=2*m+TW;TY[3]=top+m+TH;
  int sel=-1,screen=0;
  if(argc>1){if(!strcmp(argv[1],"info"))screen=1;else if(!strcmp(argv[1],"light"))screen=2;else sel=atoi(argv[1]);}
  int tf=open("/dev/input/event2",O_RDONLY);struct iev e;int x=-1,y=-1;
  struct pollfd pfd={.fd=tf,.events=POLLIN};
  while(1){
    if(screen==0)draw_home(sel);else if(screen==1)draw_info();else draw_light();
    int r=poll(&pfd,1,1000);
    if(r>0&&(pfd.revents&POLLIN)){
      while(read(tf,&e,sizeof e)==sizeof e){
        if(e.type==3){if(e.code==0x35)x=e.val;if(e.code==0x36)y=e.val;}
        else if(e.type==0){
          if(screen==1){screen=0;sel=-1;}
          else if(screen==2){
            int b=rdint(BL);
            if(y>H-90)screen=0;
            else if(x<W/2){b-=40;if(b<10)b=10;wrint(BL,b);}
            else{b+=40;if(b>255)b=255;wrint(BL,b);}
          } else {
            if(y<56)screen=2;
            else{int s=-1;for(int i=0;i<4;i++)if(x>=TX[i]&&x<TX[i]+TW&&y>=TY[i]&&y<TY[i]+TH)s=i;
              if(s==3)screen=1;else sel=s;}
          }
          break;
        }
      }
    }
  }
  return 0;
}
