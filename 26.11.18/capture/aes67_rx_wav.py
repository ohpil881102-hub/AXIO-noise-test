#!/usr/bin/env python3
"""AES67(RTP L24) 멀티캐스트 수신 -> WAV 저장 + 이상 기록 (stdlib만 사용, 읽기 전용 수신)
사용: python3 aes67_rx_wav.py --iface-ip 192.168.20.210 --group 239.1.0.1 --port 5004 --channels 8 --fs 96000 --spp 48 --minutes 10 [--save 1,2] [--out base]
"""
import argparse,socket,struct,time,datetime,sys,os,csv,signal,select
ap=argparse.ArgumentParser()
ap.add_argument("--iface-ip",required=True);ap.add_argument("--group",default="239.1.0.1");ap.add_argument("--port",type=int,default=5004)
ap.add_argument("--channels",type=int,default=8);ap.add_argument("--fs",type=int,default=96000);ap.add_argument("--spp",type=int,default=48)
ap.add_argument("--minutes",type=float,default=10);ap.add_argument("--save",default="auto");ap.add_argument("--out",default=None)
ap.add_argument("--probe",action="store_true",help="저장 없이 채널 활동만 확인")
a=ap.parse_args()
stamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
base=a.out or ("aes67rx_"+stamp)
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
try: s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEPORT,1)
except Exception: pass
s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,8*1024*1024)
s.bind(("",a.port))
s.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,socket.inet_aton(a.group)+socket.inet_aton(a.iface_ip))
s.setblocking(False)
payload_len=a.channels*3*a.spp
anom=open(base+"_anomalies.csv","w",newline="");cw=csv.writer(anom);cw.writerow(["wall_time","event","rtp_seq","detail"]);
def log(ev,seq,det):
    cw.writerow([datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],ev,seq,det]);anom.flush()
stop=False
def _s(*_): 
    global stop;stop=True
signal.signal(signal.SIGINT,_s);signal.signal(signal.SIGTERM,_s)
t_end=time.time()+a.minutes*60
npk=0;prev_seq=None;prev_ts=None;prev_t=None;seq_gaps=0;ts_jumps=0;late=0;ssrcs=set()
peak=[0]*a.channels;prob_n=0;chsave=None;wav=None;wavn=0;buf=bytearray()
def wav_header(nch,fs,data_bytes):
    ba=nch*3
    return b"RIFF"+struct.pack("<I",36+data_bytes)+b"WAVEfmt "+struct.pack("<IHHIIHH",16,1,nch,fs,fs*ba,ba,24)+b"data"+struct.pack("<I",data_bytes)
def conv(payload):
    # 입력: 채널 인터리브 L24 빅엔디언 -> 선택 채널만 24bit 리틀엔디언 인터리브
    out=bytearray()
    for f in range(a.spp):
        base_i=f*a.channels*3
        for c in chsave:
            p=base_i+c*3
            out+=bytes((payload[p+2],payload[p+1],payload[p]))
    return bytes(out)
print("수신 시작 %s:%d iface %s, %d채널 %dHz %d샘플/패킷, %.1f분"%(a.group,a.port,a.iface_ip,a.channels,a.fs,a.spp,a.minutes),flush=True)
while not stop and time.time()<t_end:
    r,_,_=select.select([s],[],[],0.5)
    if not r: continue
    while True:
        try: d,addr=s.recvfrom(4096)
        except BlockingIOError: break
        now=time.time()
        if len(d)<12: continue
        b0,b1,seq,ts,ssrc=struct.unpack(">BBHII",d[:12]);pt=b1&0x7f
        cc=b0&0x0f;hdr=12+4*cc
        if b0&0x10: 
            ext=struct.unpack(">HH",d[hdr:hdr+4]);hdr+=4+4*ext[1]
        pl=d[hdr:]
        if len(pl)!=payload_len:
            if npk<5: print("payload 길이 %d (기대 %d) pt=%d"%(len(pl),payload_len,pt),flush=True)
            log("payload_len",seq,"%d != %d"%(len(pl),payload_len));continue
        ssrcs.add((addr[0],ssrc));npk+=1
        if prev_seq is not None:
            exp=(prev_seq+1)&0xffff
            if seq!=exp: seq_gaps+=1;log("seq_gap",seq,"expected=%d missing=%d"%(exp,(seq-exp)&0xffff))
            dts=(ts-prev_ts)&0xffffffff
            if dts!=a.spp*(((seq-prev_seq)&0xffff) or 1) and seq==exp: ts_jumps+=1;log("ts_jump",seq,"dts=%d"%dts)
        if prev_t is not None and now-prev_t>0.010: late+=1;log("late",seq,"gap_ms=%.2f"%((now-prev_t)*1000))
        prev_seq=seq;prev_ts=ts;prev_t=now
        # 채널 활동(최초 4000패킷)
        if npk<=4000:
            for c in range(a.channels):
                for f in range(0,a.spp,8):
                    p=f*a.channels*3+c*3
                    v=(pl[p]<<16)|(pl[p+1]<<8)|pl[p+2]
                    if v&0x800000: v-=1<<24
                    if abs(v)>peak[c]: peak[c]=abs(v)
        if npk==4000:
            act=[c for c in range(a.channels) if peak[c]>20000]
            print("활성 채널(1부터):",[c+1 for c in act],"피크(최대 8388607):",peak,flush=True)
            if not a.probe:
                if a.save=="auto": chsave=act[:2] if act else [0,1]
                else: chsave=[int(x)-1 for x in a.save.split(",")]
                wav=open(base+".wav","wb");wav.write(wav_header(len(chsave),a.fs,0))
                print("저장 채널:",[c+1 for c in chsave],"->",base+".wav",flush=True)
        if wav is not None and chsave is not None and npk>4000:
            wav.write(conv(pl));wavn+=len(chsave)*3*a.spp
    if a.probe and npk>=4000: break
    if int(time.time())%30==0 and npk>0 and False: pass
if wav is not None:
    wav.seek(0);wav.write(wav_header(len(chsave),a.fs,wavn));wav.close()
print("\n=== 종료 요약 ===\n패킷 %d, 송신원 %s, seq_gap %d, ts_jump %d, late(>10ms) %d"%(npk,sorted(ssrcs),seq_gaps,ts_jumps,late),flush=True)
if wav is not None: print("저장 샘플프레임 %d (%.1f초)"%(wavn//(len(chsave)*3),wavn/(len(chsave)*3)/a.fs))
