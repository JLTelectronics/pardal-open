#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
typedef struct{unsigned char e_ident[16];uint16_t ty,ma;uint32_t ve;uint64_t en,ph,sh;uint32_t fl;uint16_t ehs,phes,phn,shes,shn,shx;}Ehdr;
typedef struct{uint32_t name,type;uint64_t fl,addr,off,size;uint32_t link,info;uint64_t al,es;}Shdr;
typedef struct{int64_t tag;uint64_t val;}Dyn;
static int soname(const char*p,char*out,int n){
  int f=open(p,O_RDONLY);if(f<0)return 0;
  Ehdr e;if(read(f,&e,sizeof e)!=sizeof e||memcmp(e.e_ident,"\177ELF",4)||e.e_ident[4]!=2){close(f);return 0;}
  if(e.ty!=3){close(f);return 0;}
  if(e.shes!=sizeof(Shdr)||e.shn==0||e.shn>2000||e.sh==0){close(f);return 0;}
  size_t shsz=(size_t)e.shn*e.shes;
  Shdr*sh=malloc(shsz);if(!sh){close(f);return 0;}
  if(pread(f,sh,shsz,e.sh)!=(ssize_t)shsz){free(sh);close(f);return 0;}
  uint64_t dynoff=0,dynsz=0,strlink=0;
  for(int i=0;i<e.shn;i++){Shdr*s=(Shdr*)((char*)sh+(size_t)i*e.shes);
    if(s->type==6){dynoff=s->off;dynsz=s->size;strlink=s->link;}}
  if(!dynoff||dynsz==0||dynsz>1000000||strlink>=e.shn){free(sh);close(f);return 0;}
  Shdr*ds=(Shdr*)((char*)sh+(size_t)strlink*e.shes); uint64_t stroff=ds->off,strsz=ds->size;
  if(strsz==0||strsz>2000000){free(sh);close(f);return 0;}
  Dyn*d=malloc(dynsz);if(!d){free(sh);close(f);return 0;}
  if(pread(f,d,dynsz,dynoff)!=(ssize_t)dynsz){free(d);free(sh);close(f);return 0;}
  uint64_t soff=0; int has=0;
  for(size_t i=0;i<dynsz/sizeof(Dyn);i++){if(d[i].tag==14){soff=d[i].val;has=1;break;}}
  int ok=0;
  if(has&&soff<strsz){char*str=malloc(strsz);pread(f,str,strsz,stroff);
    strncpy(out,str+soff,n-1);out[n-1]=0;ok=1;free(str);}
  free(d);free(sh);close(f);return ok;
}
int main(int argc,char**argv){char s[256];
  for(int i=1;i<argc;i++) if(soname(argv[i],s,sizeof s)) printf("%s %s\n",argv[i],s);
  return 0;}
