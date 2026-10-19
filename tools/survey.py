import struct,sys,os,glob,collections
sys.path.insert(0,os.path.dirname(__file__))
from chunks import chunks
fmt=collections.Counter(); tags=collections.Counter()
for p in glob.glob('ext/PSP_GAME/USRDIR/**/*.DAT',recursive=True):
    d=open(p,'rb').read()
    for o,tag,sz,u in chunks(d):
        tags[tag]+=1
        if tag==b'PTEX':
            n=struct.unpack_from('<I',d,o+0x18)[0]
            # entries variable; just print first
            h,z,wh,f,size,a,b=struct.unpack_from('<7I',d,o+0x1c)
            fmt[(f,)] +=1
            if f!=3 and fmt[(f,)]<4: print(p,hex(wh),f,hex(size),hex(a),hex(b),hex(sz),hex(u),n)
print(tags); print(fmt)
