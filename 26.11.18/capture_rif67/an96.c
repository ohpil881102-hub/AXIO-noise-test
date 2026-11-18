#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
static inline int32_t rd(const uint8_t*p){int32_t v=p[0]|(p[1]<<8)|(p[2]<<16); if(v&0x800000)v|=~0xFFFFFF; return v;}
int cmpd(const void*a,const void*b){double x=*(double*)a,y=*(double*)b;return (x>y)-(x<y);}
int main(int argc,char**argv){
 // 사용: an96 file.wav SR NCH [thr_mult]
 FILE*f=fopen(argv[1],"rb"); int SR=atoi(argv[2]); int NCH=atoi(argv[3]); double mult=argc>4?atof(argv[4]):40;
 fseek(f,0,SEEK_END);long fsz=ftell(f);long len=fsz-44;long n=len/(3*NCH);fseek(f,44,SEEK_SET);
 uint8_t*b=malloc(len);if(fread(b,1,len,f)!=len){printf("short read\n");}fclose(f);
 printf("frames=%ld dur=%.2fs\n",n,(double)n/SR);
 for(int ch=0;ch<NCH;ch++){
  long nb=n/SR;if(nb<2){printf("too short\n");return 0;}
  double*cc=malloc(nb*8),*tmp=malloc(SR*8),*noise=malloc(nb*8);
  #define X(i) rd(b+((long)(i)*NCH+ch)*3)
  double pk=0;
  for(long k=0;k<nb;k++){long s=k*SR;double num=0,den=0;for(long i=s+1;i<s+SR-1;i++){double x=X(i);num+=x*(X(i+1)+X(i-1));den+=2*x*x; if(fabs(x)>pk)pk=fabs(x);}
   cc[k]=den>0?num/den:1; for(long i=s+1;i<s+SR-1;i++){double r=X(i+1)+X(i-1)-2*cc[k]*X(i);tmp[i-s-1]=fabs(r);} qsort(tmp,SR-2,8,cmpd);noise[k]=tmp[(SR-2)/2];}
  double*ns=malloc(nb*8);for(long k=0;k<nb;k++)ns[k]=noise[k];qsort(ns,nb,8,cmpd);
  double thr=fmax(3000.0,ns[nb/2]*mult);
  double fr=acos(fmax(-1,fmin(1,cc[nb/2])))*SR/(2*M_PI);
  printf("CH%d 피크=%.0f (%.1f dBFS) 주파수≈%.3f Hz 잔차 노이즈 중앙값=%.1f 임계=%.0f\n",ch+1,pk,20*log10(pk/8388608.0),fr,ns[nb/2],thr);
  long ev=0,last=-1000000;
  for(long i=SR/2;i<nb*SR-1;i++){long k=i/SR;double r=fabs(X(i+1)+X(i-1)-2*cc[k]*X(i));
   if(r>thr){ if(i-last>SR/40){ev++; if(ev<=100000)printf("  이벤트 #%ld t=%.4fs (%02d:%07.4f) 잔차=%.0f\n",ev,(double)i/SR,(int)(i/SR/60),fmod((double)i/SR,60),r);} last=i;}}
  printf("CH%d 이벤트 수=%ld\n",ch+1,ev);
 }
 long run=0,mx=0,r8=0;for(long i=0;i<=n;i++){int z=(i<n);if(z){for(int c=0;c<NCH;c++)if(rd(b+((long)i*NCH+c)*3)!=0){z=0;break;}}
  #undef X
  if(z)run++;else{if(run>mx)mx=run;if(run>=8)r8++;run=0;}}
 printf("전 채널 0 연속(>=8샘플)=%ld 최장=%ld\n",r8,mx);return 0;}
