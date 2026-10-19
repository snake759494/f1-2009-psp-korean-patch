import pycdlib,sys
iso=pycdlib.PyCdlib(); iso.open(sys.argv[1])
for root,dirs,files in iso.walk(iso_path='/'):
    for f in files:
        rec=iso.get_record(iso_path=root.rstrip('/')+'/'+f)
        print(f"{rec.extent_location():8d} {rec.data_length:10d} {root}/{f}")
