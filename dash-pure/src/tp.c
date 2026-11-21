#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
struct iev { long sec, usec; uint16_t type, code; int32_t value; };
int main(int argc,char**argv){
  const char*dev = argc>1?argv[1]:"/dev/input/event2";
  int fd=open(dev,O_RDONLY);
  if(fd<0){ perror("open"); return 1; }
  fprintf(stderr,"reading %s (struct=%zu bytes)\n",dev,sizeof(struct iev));
  struct iev e; int x=-1,y=-1;
  while(read(fd,&e,sizeof e)==sizeof e){
    if(e.type==3){
      if(e.code==0x35||e.code==0) x=e.value;
      if(e.code==0x36||e.code==1) y=e.value;
      if(e.code==0x39) printf("trackid=%d\n",e.value);
    } else if(e.type==1 && e.code==0x14a){ printf("BTN_TOUCH=%d\n",e.value); }
    else if(e.type==0){ printf("SYN x=%d y=%d\n",x,y); fflush(stdout); }
    else printf("type=%d code=%d val=%d\n",e.type,e.code,e.value);
  }
  return 0;
}
