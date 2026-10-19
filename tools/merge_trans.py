import json,glob,re,sys
lines=[l.rstrip('\n').split('\t') for l in open('uniq_EN.txt',encoding='utf-8')]
src={int(i):json.loads(s) for i,k,s in lines}
tr={}
for p in sorted(glob.glob('trans/b*.json')):
    for k,v in json.load(open(p,encoding='utf-8')).items(): tr[int(k)]=v
ko={src[i]:v for i,v in tr.items()}
for p in sorted(glob.glob('trans/p*.json')):
    ko.update(json.load(open(p,encoding='utf-8')))
json.dump(ko,open('trans/ko.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
# 플레이스홀더 검사
bad=0
for i,v in tr.items():
    a=sorted(re.findall(r'\{[A-Z]\d\}|%[a-z]|%%',src[i])); b=sorted(re.findall(r'\{[A-Z]\d\}|%[a-z]|%%',v))
    if a!=b: bad+=1; print('PH',i,a,b)
print('translated',len(tr),'placeholder mismatches',bad)
if len(sys.argv)>1:
    for i,s in src.items():
        if i not in tr and re.search(r'[A-Za-z]{2,}',s): print(i,json.dumps(s,ensure_ascii=False)[:90])
