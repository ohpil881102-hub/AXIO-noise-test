#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
static inline int32_t rd(const uint8_t*p){int32_t v=p[0]|(p[1]<<8)|(p[2]<<16); if(v&0x800000)v|=~0xFFFFFF; return v;}
int cmpd(const void*a,const void*b){double x=*(double*)a,y=*(double*)b;return (x>y)-(x<y);}
int main(int argc,char**argv){
 int SR=96000,NCH=2; double mult=atof(argv[2]); FILE*f=fopen(argv[1],"rb");fseek(f,0,SEEK_END);long fs=ftell(f);long len=fs-44;long n=len/(3*NCH);fseek(f,44,SEEK_SET);
 uint8_t*b=malloc(len);fread(b,1,len,f);fclose(f);
 int W=96; long nw=n/W; double*hf=malloc(nw*8),*lf=malloc(nw*8),*ratio=malloc(nw*8);
 for(long k=0;k<nw;k++){double sh=0,sl=0;for(int i=1;i<W-1;i++){long j=k*W+i;double x0=rd(b+(j*NCH)*3),xm=rd(b+((j-1)*NCH)*3),xp=rd(b+((j+1)*NCH)*3);double r=xp-2*x0+xm;sh+=r*r;sl+=x0*x0;}hf[k]=sqrt(sh/(W-2));lf[k]=sqrt(sl/(W-2));}
 // 국소 LF 기준(10창 평균)
 for(long k=0;k<nw;k++){long a=k>5?k-5:0,e=k+5<nw?k+5:nw-1;double s=0;for(long q=a;q<=e;q++)s+=lf[q]*lf[q];s=sqrt(s/(e-a+1));ratio[k]=s>1000?hf[k]/s:0;}
 double*t=malloc(nw*8);long m=0;for(long k=0;k<nw;k++)if(ratio[k]>0)t[m++]=ratio[k];qsort(t,m,8,cmpd);double med=t[m/2];
 printf("창=%d샘플(1ms) 개수=%ld 중앙 hf/lf 비=%.5f (p99=%.5f, 최대=%.5f)\n",W,nw,med,t[(long)(m*0.99)],t[m-1]);
 long ev=0,last=-1000;for(long k=0;k<nw;k++){if(ratio[k]>mult*med){if(k-last>20){ev++;if(ev<=100000)printf("  이벤트 #%ld t=%.3fs 비=%.4f\n",ev,(double)k*W/SR,ratio[k]);}last=k;}}
 printf("이벤트 수(비>%.1f×중앙)=%ld\n",mult,ev);return 0;}
