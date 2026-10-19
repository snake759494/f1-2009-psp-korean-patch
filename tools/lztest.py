import sys; sys.path.insert(0,'tools')
from PIL import Image
def dec(src,pos,outlen,mode):
    out=bytearray()
    try:
     while len(out)<outlen:
        flag=src[pos]; pos+=1
        for b in range(7,-1,-1):
            if len(out)>=outlen: break
            if flag&(1<<b):
                t=(src[pos]<<8)|src[pos+1]; pos+=2
                dist,ln=mode(t)
                for _ in range(ln): out.append(out[-dist] if dist<=len(out) else 0)
            else:
                out.append(src[pos]); pos+=1
    except IndexError: pass
    return out,pos
def show(out,w,name,off=64):
    px=out[off:]; h=len(px)*2//w
    im=Image.new('L',(w,h))
    for i,b in enumerate(px[:w*h//2]):
        im.putpixel(((2*i)%w,(2*i)//w),(b&15)*17); im.putpixel(((2*i+1)%w,(2*i+1)//w),(b>>4)*17)
    im.resize((w*4,h*4)).save(name)
def unswizzle(data,rowbytes,h):
    out=bytearray(rowbytes*h); bw=rowbytes//16; i=0
    for by in range(h//8):
        for bx in range(bw):
            for r in range(8):
                o=(by*8+r)*rowbytes+bx*16
                out[o:o+16]=data[i:i+16]; i+=16
    return out
