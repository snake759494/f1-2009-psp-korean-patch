import struct,sys
def chunks(d):
    o=0;out=[]
    while o+16<=len(d):
        tag=d[o:o+4]; sz,u,m=struct.unpack_from('<III',d,o+4)
        if m!=0x44332211 or sz==0: break
        out.append((o,tag,sz,u)); o+=sz
    return out
if __name__=='__main__':
    d=open(sys.argv[1],'rb').read()
    for c in chunks(d): print(hex(c[0]),c[1],hex(c[2]),hex(c[3]))
