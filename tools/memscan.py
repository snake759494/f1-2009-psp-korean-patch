import sys,os,base64; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from ppsspp_rpc import Debugger
def dump(path='dec/ram.bin'):
    d=Debugger()
    try:
        pass
        out=bytearray()
        for a in range(0x08800000,0x0a000000,0x100000):
            r=d.call('memory.read',address=a,size=0x100000); out+=base64.b64decode(r['base64'])
        pass
    finally: d.close()
    open(path,'wb').write(out); return out
if __name__=='__main__':
    dump(sys.argv[1] if len(sys.argv)>1 else 'dec/ram.bin')
