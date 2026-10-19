"""원본 ISO 를 복사하고 파일을 교체. 원래 섹터 안에 들어가면 제자리, 아니면 ISO 끝에 덧붙이고
디렉터리 레코드(LBA/크기)와 PVD 볼륨 크기를 고친다. 다른 파일 위치는 움직이지 않는다."""
import struct, shutil, os, sys
SECTOR=2048
def walk(f):
    f.seek(16*SECTOR); pvd=f.read(SECTOR); root=pvd[156:190]
    out={}
    def rec(lba,length,path):
        f.seek(lba*SECTOR); data=f.read(((length+SECTOR-1)//SECTOR)*SECTOR); o=0
        while o<length:
            n=data[o]
            if n==0:
                o=((o//SECTOR)+1)*SECTOR
                if o>=length: break
                continue
            r=data[o:o+n]; elba=struct.unpack('<I',r[2:6])[0]; esz=struct.unpack('<I',r[10:14])[0]
            fl,nl=r[25],r[32]; nm=r[33:33+nl]
            if nm not in (b'\0',b'\1'):
                name=nm.decode('ascii','replace').split(';')[0]; full=path+'/'+name
                if fl&2: rec(elba,esz,full)
                else: out[full.upper()]=(lba*SECTOR+o,elba,esz)
            o+=n
    rec(struct.unpack('<I',root[2:6])[0],struct.unpack('<I',root[10:14])[0],'')
    return out
def patch(src_iso,dst_iso,files):
    shutil.copyfile(src_iso,dst_iso)
    with open(dst_iso,'r+b') as f:
        ents=walk(f)
        extents=sorted((v[1],v[1]+(v[2]+SECTOR-1)//SECTOR) for v in ents.values())
        f.seek(0,2); end_sec=(f.tell()+SECTOR-1)//SECTOR
        for isop,data in files.items():
            ro,lba,sz=ents[isop.upper()]
            cap=(sz+SECTOR-1)//SECTOR
            nxt=min([a for a,b in extents if a>lba]+[end_sec])
            cap=max(cap,nxt-lba)
            need=(len(data)+SECTOR-1)//SECTOR
            if need<=cap: nl=lba
            else: nl=end_sec; end_sec+=need
            f.seek(nl*SECTOR); f.write(data+bytes(need*SECTOR-len(data)))
            f.seek(ro+2); f.write(struct.pack('<I',nl)+struct.pack('>I',nl)+struct.pack('<I',len(data))+struct.pack('>I',len(data)))
        f.seek(0,2); total=f.tell()//SECTOR
        f.seek(16*SECTOR+80); f.write(struct.pack('<I',total)+struct.pack('>I',total))
