#include <unistd.h>
#include <fcntl.h>
#include <sys/syscall.h>
int main(int c,char**v){
  int out = (v[1][0]=='-'&&!v[1][1]) ? 1 : open(v[1],O_WRONLY|O_CREAT|O_TRUNC,0666);
  if(out<0)return 2;
  char b[16384];
  for(;;){
    long n=syscall(SYS_syslog,2,b,(long)sizeof b);
    if(n>0){ write(out,b,n); }
    else if(n<0){ usleep(50000); }
  }
  return 0;
}
