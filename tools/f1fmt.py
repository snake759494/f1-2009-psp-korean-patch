import struct
from chunks import chunks
def parse_text(d,o):
    n=struct.unpack_from('<I',d,o+0x18)[0]; recs=[]
    for i in range(n):
        h,p=struct.unpack_from('<II',d,o+0x1c+8*i)
        s=o+0x10+p; e=d.index(b'\0',s)
        recs.append((h,d[s:e].decode('utf-8')))
    return recs
def parse_font(d,o):
    n=struct.unpack_from('<I',d,o+0x18)[0]; fonts=[]
    for i in range(n):
        f=struct.unpack_from('<IIIIIIff',d,o+0x1c+0x20*i)
        fonts.append(dict(hash=f[0],count=f[1]&0xffff,cflags=f[1]>>16,tab=f[2],end=f[3],c=f[4],lh=f[5],fx=f[6],fy=f[7]))
    for f in fonts:
        g=[]; base=o+0x10+f['tab']
        for k in range(f['count']):
            r=struct.unpack_from('<IHHHHHhhhI',d,base+0x18*k)
            g.append(dict(tex=r[0],ch=r[1],x=r[2],y=r[3],w=r[4],h=r[5],ox=r[6],adv=r[7],oy=r[8],flag=r[9]))
        f['glyphs']=g
    return fonts
