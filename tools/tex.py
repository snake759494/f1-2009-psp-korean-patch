import struct
from PIL import Image
from lz import decompress, compress
def swz_geom(e):
    fmt=e['dl'][3]&0xff; bpp=4 if fmt==4 else 8
    tbw=e['dl'][9]&0xffff
    rowb=tbw*bpp//8
    return fmt,bpp,tbw,rowb
def unswizzle(data,rowb,h):
    out=bytearray(rowb*h); bw=rowb//16; i=0
    for by in range(h//8):
        for bx in range(bw):
            for r in range(8):
                o=(by*8+r)*rowb+bx*16; out[o:o+16]=data[i:i+16]; i+=16
    return out
def swizzle(lin,rowb,h):
    out=bytearray(rowb*h); bw=rowb//16; i=0
    for by in range(h//8):
        for bx in range(bw):
            for r in range(8):
                o=(by*8+r)*rowb+bx*16; out[i:i+16]=lin[o:o+16]; i+=16
    return bytes(out)
def decode(d,chunk_off,e):
    fmt,bpp,tbw,rowb=swz_geom(e)
    raw,_=decompress(d,chunk_off+0x10+e['ptr'],e['size']+e['clut'])
    clut=raw[:e['clut']]; pix=raw[e['clut']:]
    h=len(pix)//rowb
    lin=unswizzle(pix,rowb,h) if (e['dl'][1]&1) else pix
    pal=[tuple(clut[i:i+4]) for i in range(0,len(clut),4)]
    idx=[]
    if bpp==4:
        for b in lin: idx+= [b&15, b>>4]
    else: idx=list(lin)
    return dict(fmt=fmt,bpp=bpp,tbw=tbw,h=h,pal=pal,idx=idx)
def to_image(t):
    im=Image.new('RGBA',(t['tbw'],t['h']))
    im.putdata([t['pal'][i] for i in t['idx']])
    return im
