"""F1 2009 PSP PTEX LZ (EBOOT 0x169894).
flag byte MSB-first; bit=0 literal; bit=1 token b0 b1:
  dist=(b0<<4)|(b1>>4); dist!=0 -> copy (b1&15)+3 from out-dist
  dist==0 -> RLE: byte b3 repeated ((b1&15)<<8|b2)+16 times."""
def decompress(src, pos, outlen):
    out=bytearray()
    while len(out)<outlen:
        flag=src[pos]; pos+=1
        for b in range(7,-1,-1):
            if len(out)>=outlen: break
            if flag&(1<<b):
                b0,b1=src[pos],src[pos+1]; pos+=2
                dist=(b0<<4)|(b1>>4)
                if dist:
                    for _ in range((b1&15)+3): out.append(out[-dist])
                else:
                    n=(((b1&15)<<8)|src[pos])+16
                    out+=bytes([src[pos+1]])*n; pos+=2
            else:
                out.append(src[pos]); pos+=1
    return bytes(out[:outlen]), pos

def compress(data):
    n=len(data); i=0; items=[]
    head={}; prev=[-1]*n
    def ins(p):
        if p+3<=n:
            k=data[p:p+3]; prev[p]=head.get(k,-1); head[k]=p
    while i<n:
        run=1
        while i+run<n and run<4111 and data[i+run]==data[i]: run+=1
        if run>=19:
            items.append(('R',run,data[i]))
            for p in range(i,i+run): ins(p)
            i+=run; continue
        best=0;bd=0
        if i+3<=n:
            c=head.get(data[i:i+3],-1); tries=0
            while c>=0 and i-c<=4095 and tries<128:
                l=0
                while l<18 and i+l<n and data[c+l]==data[i+l]: l+=1
                if l>best: best=l;bd=i-c
                if best==18: break
                c=prev[c]; tries+=1
        if best>=3:
            items.append((bd,best))
            for p in range(i,i+best): ins(p)
            i+=best
        else:
            items.append(data[i]); ins(i); i+=1
    out=bytearray()
    for k in range(0,len(items),8):
        grp=items[k:k+8]; flag=0; body=bytearray()
        for j,it in enumerate(grp):
            if isinstance(it,tuple) and it[0]=='R':
                flag|=1<<(7-j); m=it[1]-16; body+=bytes([0,m>>8,m&255,it[2]])
            elif isinstance(it,tuple):
                flag|=1<<(7-j); t=(it[0]<<4)|(it[1]-3); body+=bytes([t>>8,t&255])
            else: body.append(it)
        out.append(flag); out+=body
    return bytes(out)
