#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/mman.h>
#include <sys/ioctl.h>

struct bf { uint32_t offset, length, msb_right; };
struct fb_var {
  uint32_t xres,yres,xres_virtual,yres_virtual,xoffset,yoffset;
  uint32_t bits_per_pixel,grayscale;
  struct bf red,green,blue,transp;
  uint32_t nonstd,activate,height,width,accel_flags;
  uint32_t pixclock,left_margin,right_margin,upper_margin,lower_margin,hsync_len,vsync_len,sync,vmode,rotate,colorspace;
  uint32_t reserved[4];
};
struct fb_fix {
  char id[16];
  unsigned long smem_start;
  uint32_t smem_len;
  uint32_t type,type_aux,visual;
  uint16_t xpanstep,ypanstep,ywrapstep;
  uint32_t line_length;
  unsigned long mmio_start;
  uint32_t mmio_len,accel;
  uint16_t capabilities,reserved[2];
};
#define FBIOGET_VSCREENINFO 0x4600
#define FBIOGET_FSCREENINFO 0x4602
#define FBIOPAN_DISPLAY     0x4606
#define FB_ACTIVATE_NOW 0
#define FB_ACTIVATE_FORCE 128

int main(int argc,char**argv){
  int fd=open("/dev/graphics/fb0",O_RDWR);
  if(fd<0){ fd=open("/dev/fb0",O_RDWR); }
  if(fd<0){ perror("open"); return 1; }
  struct fb_var v; struct fb_fix f;
  memset(&v,0,sizeof v); memset(&f,0,sizeof f);
  ioctl(fd,FBIOGET_VSCREENINFO,&v);
  ioctl(fd,FBIOGET_FSCREENINFO,&f);
  fprintf(stderr,"xres=%u yres=%u vy=%u bpp=%u line=%u smem=%u yoff=%u\n",
    v.xres,v.yres,v.yres_virtual,v.bits_per_pixel,f.line_length,f.smem_len,v.yoffset);
  long sz=(long)f.line_length*v.yres_virtual; if(sz<(long)f.smem_len)sz=f.smem_len; if(sz<=0)sz=480L*1440*4;
  unsigned char*fb=mmap(0,sz,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
  if(fb==MAP_FAILED){ perror("mmap"); return 1; }
  uint32_t color=0xFFFFFFFF; if(argc>1)color=(uint32_t)strtoul(argv[1],0,16);
  int bpp=v.bits_per_pixel?v.bits_per_pixel/8:4;
  int line=f.line_length?f.line_length:v.xres*bpp;
  int nbuf=v.yres_virtual/(v.yres?v.yres:480); if(nbuf<1)nbuf=1;
  for(int b=0;b<nbuf;b++){
    unsigned char*base=fb+(long)b*v.yres*line;
    for(unsigned y=0;y<v.yres;y++){
      unsigned char*row=base+(long)y*line;
      for(unsigned x=0;x<v.xres;x++) *(uint32_t*)(row+x*bpp)=color;
    }
  }
  v.yoffset=0; v.activate=FB_ACTIVATE_NOW|FB_ACTIVATE_FORCE;
  if(ioctl(fd,FBIOPAN_DISPLAY,&v)<0) perror("FBIOPAN_DISPLAY"); else fprintf(stderr,"panned color=%08x\n",color);
  msync(fb,sz,MS_SYNC);
  return 0;
}
