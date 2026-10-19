import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch_iso import patch
SRC = '../F1 2009 (Europe) (En,Fr,De,Es,It).iso'
def files():
    out = {}
    for p in sorted(glob.glob('build/UI/*.DAT') + glob.glob('build/UI/*.REL')):
        out['/PSP_GAME/USRDIR/UI/' + os.path.basename(p)] = open(p, 'rb').read()
    for p in sorted(glob.glob('build/OTHER/**/*', recursive=True)):
        if os.path.isfile(p):
            rel = os.path.relpath(p, 'build/OTHER').replace(os.sep, '/')
            out['/' + rel] = open(p, 'rb').read()
    return out
if __name__ == '__main__':
    dst = sys.argv[1] if len(sys.argv) > 1 else 'test.iso'
    f = files(); patch(SRC, dst, f); print(len(f), 'files ->', dst, os.path.getsize(dst))
