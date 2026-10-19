import struct,sys
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from chunks import chunks
def entries(d,o):
    n=struct.unpack_from('<I',d,o+0x18)[0]; out=[]
    for i in range(n):
        e=o+0x1c+0x54*i
        h,z,wh,f,size,cl,ptr=struct.unpack_from('<7I',d,e)
        dl=struct.unpack_from('<14I',d,e+0x1c)
        out.append(dict(e=e,hash=h,w=wh&0xffff,h=wh>>16,f=f,size=size,clut=cl,ptr=ptr,dl=dl))
    return out
if __name__=='__main__':
    d=open(sys.argv[1],'rb').read()
    for o,tag,sz,u in chunks(d):
        if tag==b'PTEX':
            print('PTEX',hex(o),hex(sz),hex(u))
            for e in entries(d,o): print({k:(hex(v) if isinstance(v,int) else ' '.join('%08x'%x for x in v)) for k,v in e.items()})
