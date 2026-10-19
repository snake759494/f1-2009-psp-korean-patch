import struct
def read_pak(d):
    n = struct.unpack_from('<I', d, 0)[0]
    hdr = struct.unpack_from('<4I', d, 0)
    ents = []
    for i in range(n):
        h, off, sz, sz2 = struct.unpack_from('<4I', d, 16 + 16 * i)
        ents.append(dict(hash=h, off=off, size=sz, size2=sz2, data=d[off:off + sz]))
    return hdr, ents
