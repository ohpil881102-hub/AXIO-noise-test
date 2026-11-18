import subprocess,re,time,datetime,sys
GROUP=sys.argv[1];OUT=sys.argv[2];MINUTES=sys.argv[3]
t0=time.time()
def log(s):
    open("wait_log.txt","a").write(datetime.datetime.now().strftime("%H:%M:%S ")+s+"\n")
log("대기 시작 %s"%GROUP)
while time.time()-t0<40*60:
    r=subprocess.run(["python3","aes67_rx_wav.py","--iface-ip","192.168.20.210","--group",GROUP,"--probe","--minutes","0.1","--out","probe_tmp"],capture_output=True,text=True).stdout
    m=re.search(r"활성 채널\(1부터\): \[([^\]]*)\] 피크.*?\[([^\]]*)\]",r)
    act=[x for x in (m.group(1).split(",") if m else []) if x.strip()]
    log("probe: 활성 채널=%s"%act)
    if act:
        save=",".join(x.strip() for x in act[:2]) if len(act)>=2 else (act[0].strip()+","+("2" if act[0].strip()=="1" else "1"))
        log("신호 감지 -> 녹음 시작 (save=%s, %s분)"%(save,MINUTES))
        subprocess.Popen(["python3","aes67_rx_wav.py","--iface-ip","192.168.20.210","--group",GROUP,"--save",save,"--minutes",MINUTES,"--out",OUT],stdout=open(OUT+"_stdout.log","w"),stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,close_fds=True)
        sys.exit(0)
    time.sleep(1)
log("40분 동안 신호 없음 -> 종료")
