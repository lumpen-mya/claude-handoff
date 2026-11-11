#!/usr/bin/env python3
"""Compare all Claude Code sessions on this machine (test-period measurement).

Usage:
  python3 -I compare_sessions.py out.json     # writes one row per session, prints a group summary

Per session: API calls, active minutes, peak and average context, input/output tokens,
weighted cost (input 1, cache read 0.1, cache write 1.25, output 5), auto-compactions,
user messages, and a rough count of user corrections (short messages matching CORR).
Sessions are grouped by how they started (from a handoff note / a brief / plain) and by size.
Subagent logs (<session>/subagents/*.jsonl) are summed into the session's cost.
"""
import json,glob,os,re,datetime,sys
base=os.path.expanduser('~/.claude/projects')
# rough correction markers (Korean + English); adjust for your language
CORR=re.compile(r'(아니|ㄴㄴ|왜 ?안|다시 ?(해|확인)|잘못|안 ?되|안 ?돼|틀렸|뭔소리|이상해|\bno[,. ]|\bwrong\b|\bagain\b|not what)',re.I)
def ts(s):
    try: return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
    except: return None
rows=[]
for f in glob.glob(base+'/*/*.jsonl'):
    seen=set(); req=0; ctxs=[]; w=0.0; inp=0; out=0; comp=0; users=0; corr=0; times=[]; first=None; kind='plain'
    sub=glob.glob(f[:-6]+'/subagents/*.jsonl')
    for path,is_sub in [(f,False)]+[(s,True) for s in sub]:
      for l in open(path,encoding='utf-8',errors='ignore'):
        try:d=json.loads(l)
        except:continue
        t=ts(d.get('timestamp','')) 
        if t and not is_sub: times.append(t)
        if d.get('isCompactSummary') and not is_sub: comp+=1
        if d.get('type')=='user' and not is_sub and not d.get('isMeta') and not d.get('isCompactSummary'):
            c=d['message']['content']
            txt=c if isinstance(c,str) else ' '.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type')=='text')
            if not txt.strip() or txt.lstrip().startswith('<') and 'command-name' not in txt and len(re.sub(r'<[^>]+>[\s\S]*?</[^>]+>','',txt).strip())==0: continue
            if 'tool_use_id' in l and isinstance(c,list) and all(x.get('type')=='tool_result' for x in c if isinstance(x,dict)): continue
            clean=re.sub(r'<system-reminder>[\s\S]*?</system-reminder>','',txt).strip()
            if not clean: continue
            if first is None:
                first=clean
                if re.search(r'handoffs/[\w-]+\.md',clean): kind='handoff'
                elif clean.startswith('Background (from the session') or 'session that started this one' in clean: kind='brief'
            users+=1
            if len(clean)<300 and CORR.search(clean): corr+=1
        if d.get('type')=='assistant':
            m=d.get('message') or {}; u=m.get('usage'); rid=d.get('requestId') or m.get('id')
            if not u or rid in seen: continue
            seen.add(rid); req+=1
            i=u.get('input_tokens',0); cr=u.get('cache_read_input_tokens',0); cw=u.get('cache_creation_input_tokens',0); o=u.get('output_tokens',0)
            if not is_sub: ctxs.append(i+cr+cw)
            inp+=i+cr+cw; out+=o; w+=i+cr*0.1+cw*1.25+o*5
    if req<3: continue
    times.sort(); active=sum(min((b-a).total_seconds(),600) for a,b in zip(times,times[1:]))/60
    rows.append(dict(id=os.path.basename(f)[:8],proj=os.path.basename(os.path.dirname(f)).replace('-home-ksw------eum','eum'),start=times[0].strftime('%m-%d') if times else '',kind=kind,req=req,active=round(active),peak=max(ctxs) if ctxs else 0,avgctx=round(sum(ctxs)/len(ctxs)) if ctxs else 0,inp=inp,out=out,w=round(w),comp=comp,users=users,corr=corr))
json.dump(rows,open(sys.argv[1],'w'),ensure_ascii=False)
def group(x):
    if x['kind'] in ('brief','handoff') and x['req']<400: return 'A started from brief/handoff'
    if x['req']>=400: return 'C long (400+ calls)'
    if x['req']>=100: return 'B medium (100-399 calls)'
    return 'D short plain (<100 calls)'
G={}
for x in rows:
    if x['users']: G.setdefault(group(x),[]).append(x)
print('group | sessions | user msgs | avg context | weighted cost per user msg | output per call | compactions | corrections')
for k in sorted(G):
    L=G[k]; S=lambda f:sum(x[f] for x in L)
    print(f"{k} | {len(L)} | {S('users')} | {round(sum(x['avgctx']*x['req'] for x in L)/S('req')/1000)}K | {S('w')//S('users')//1000}K | {S('out')//S('req')} | {S('comp')} | {round(S('corr')*100/S('users'),1)}%")
