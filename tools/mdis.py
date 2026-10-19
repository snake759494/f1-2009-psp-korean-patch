import capstone,sys,struct
d=open('dec/EBOOT.DEC','rb').read()
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN)
md.skipdata=True
a=int(sys.argv[1],16); n=int(sys.argv[2])
# file off = vaddr + 0x74 (seg0 offset 116, vaddr 0)
for i in md.disasm(d[a+0x74:a+0x74+n*4],a):
    print(f"{i.address:08x} {i.mnemonic} {i.op_str}")
