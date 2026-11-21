#include <unistd.h>
#include <sys/wait.h>
int main(int argc, char**argv){
  pid_t p = fork();
  if(p==0){ execv("/system/bin/apexd.real", argv); _exit(127); }
  int st; waitpid(p,&st,0);
  return 0;
}
