#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <poll.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
struct bf{uint32_t o,l,m;};
struct fbv{uint32_t xres,yres,xv,yv,xo,yo,bpp,gray;struct bf r,g,b,a;uint32_t nonstd,act,h,w,acc,pix,lm,rm,um,lo,hl,vl,sync,vmode,rot,cs,res[4];};
struct fbf{char id[16];unsigned long ss;uint32_t sl,t,ta,v;uint16_t xp,yp,yw;uint32_t ll;unsigned long ms;uint32_t ml,ac;uint16_t cap,r2[2];};
#define GV 0x4600
#define GF 0x4602
#define PAN 0x4606
struct iev{long s,u;uint16_t type,code;int32_t val;};
static uint8_t*fb; static int LL,W,H,BPP; static int fbfd; static struct fbv V;
static void px(int x,int y,uint32_t c){ if(x<0||y<0||x>=W||y>=H)return; *(uint32_t*)(fb+(long)y*LL+x*(BPP/8))=c; }
static void rect(int x,int y,int w,int h,uint32_t c){ for(int j=0;j<h;j++)for(int i=0;i<w;i++)px(x+i,y+j,c); }
static void border(int x,int y,int w,int h,int t,uint32_t c){ rect(x,y,w,t,c);rect(x,y+h-t,w,t,c);rect(x,y,t,h,c);rect(x+w-t,y,t,h,c); }
static void flip(){ V.yo=0;V.act=0|128; ioctl(fbfd,PAN,&V); }
static int TX[4],TY[4],TW,TH; static uint32_t COL[4]={0xFF4E3BFF,0xFF6ACF3F,0xFFFF6A2B,0xFFE7CF6A};
static void draw(int sel){
  rect(0,0,W,H,0xFF1A1A14);
  for(int i=0;i<4;i++){
    rect(TX[i],TY[i],TW,TH,COL[i]);
    if(i==sel) border(TX[i],TY[i],TW,TH,8,0xFFFFFFFF);
  }
  flip();
}
int main(){
  fbfd=open("/dev/fb0",O_RDWR); if(fbfd<0){perror("fb");return 1;}
  struct fbf F; ioctl(fbfd,GV,&V); ioctl(fbfd,GF,&F);
  W=V.xres;H=V.yres;BPP=V.bpp;LL=F.ll; long sz=(long)LL*V.yv; if(sz<F.sl)sz=F.sl;
  fb=mmap(0,sz,PROT_READ|PROT_WRITE,MAP_SHARED,fbfd,0); if(fb==MAP_FAILED){perror("mmap");return 1;}
  fprintf(stderr,"UI %dx%d bpp=%d ll=%d\n",W,H,BPP,LL);
  int m=24; TW=(W-3*m)/2; TH=(H-3*m)/2;
  TX[0]=m;TY[0]=m; TX[1]=2*m+TW;TY[1]=m; TX[2]=m;TY[2]=2*m+TH; TX[3]=2*m+TW;TY[3]=2*m+TH;
  draw(-1);
  int tf=open("/dev/input/event2",O_RDONLY);
  struct iev e; int x=-1,y=-1,sel=-1;
  while(read(tf,&e,sizeof e)==sizeof e){
    if(e.type==3){ if(e.code==0x35)x=e.val; if(e.code==0x36)y=e.val; }
    else if(e.type==0){
      int s=-1; for(int i=0;i<4;i++) if(x>=TX[i]&&x<TX[i]+TW&&y>=TY[i]&&y<TY[i]+TH)s=i;
      if(s!=sel){ sel=s; draw(sel); fprintf(stderr,"touch %d,%d tile=%d\n",x,y,sel); }
    }
  }
  return 0;
}
