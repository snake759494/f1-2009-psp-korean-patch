import pycdlib,sys,os
iso=pycdlib.PyCdlib(); iso.open(sys.argv[1]); out=sys.argv[2]; pref=sys.argv[3] if len(sys.argv)>3 else '/'
for root,dirs,files in iso.walk(iso_path='/'):
    if not root.startswith(pref): continue
    for f in files:
        p=root.rstrip('/')+'/'+f
        if p.endswith(('.AT3','.PMF','.PAC')): continue
        d=os.path.join(out,root.strip('/')); os.makedirs(d,exist_ok=True)
        iso.get_file_from_iso(os.path.join(d,f),iso_path=p)
