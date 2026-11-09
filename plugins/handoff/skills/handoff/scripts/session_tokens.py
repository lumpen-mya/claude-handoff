#!/usr/bin/env python3
"""Claude Code 세션 토큰 사용량 요약.

사용법:
  session_tokens.py                 # 현재 폴더 프로젝트의 가장 최근 세션
  session_tokens.py <session-id>    # 특정 세션 (id 앞부분만 줘도 됨)
  session_tokens.py <path.jsonl>    # 파일 직접 지정
  --json                            # JSON 한 줄로 출력 (handoff md 기록용)

같은 requestId 는 한 번만 센다. 서브에이전트(isSidechain) 사용량도 합산하고 따로 표시한다.
"""
import json, sys, glob, os, datetime

def find_file(arg):
    if arg and arg.endswith('.jsonl') and os.path.isfile(arg):
        return arg
    base = os.path.expanduser('~/.claude/projects')
    files = glob.glob(os.path.join(base, '*', '*.jsonl'))
    if arg:
        hit = [f for f in files if os.path.basename(f).startswith(arg)]
        if not hit:
            sys.exit(f'세션을 찾지 못함: {arg}')
        return max(hit, key=os.path.getmtime)
    proj = os.getcwd().replace('/', '-')
    proj = ''.join(c if c.isascii() and (c.isalnum() or c == '-') else '-' for c in proj)
    local = [f for f in files if os.path.basename(os.path.dirname(f)) == proj]
    return max(local or files, key=os.path.getmtime)

def main():
    args = [a for a in sys.argv[1:] if a != '--json']
    as_json = '--json' in sys.argv
    path = find_file(args[0] if args else None)
    seen = set()
    tot = dict(input=0, cache_write=0, cache_read=0, output=0)
    side = dict(tot)
    turns = 0; peak = 0; models = set(); ts = []
    for line in open(path, encoding='utf-8'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get('timestamp'):
            ts.append(o['timestamp'])
        m = o.get('message')
        if o.get('type') != 'assistant' or not isinstance(m, dict) or not m.get('usage'):
            continue
        rid = o.get('requestId') or o.get('uuid')
        if rid in seen:
            continue
        seen.add(rid)
        u = m['usage']
        row = dict(input=u.get('input_tokens', 0) or 0,
                   cache_write=u.get('cache_creation_input_tokens', 0) or 0,
                   cache_read=u.get('cache_read_input_tokens', 0) or 0,
                   output=u.get('output_tokens', 0) or 0)
        target = side if o.get('isSidechain') else tot
        for k in row:
            target[k] += row[k]
        if not o.get('isSidechain'):
            turns += 1
            peak = max(peak, row['input'] + row['cache_write'] + row['cache_read'])
        if m.get('model'):
            models.add(m['model'])
    dur = None
    if len(ts) >= 2:
        p = lambda s: datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        dur = round((p(max(ts)) - p(min(ts))).total_seconds() / 60)
    all_in = sum(tot[k] for k in ('input', 'cache_write', 'cache_read')) + sum(side[k] for k in ('input', 'cache_write', 'cache_read'))
    out = dict(session=os.path.basename(path)[:-6], minutes=dur, requests=turns,
               peak_context=peak, models=sorted(models),
               main=tot, subagents=side,
               total_input=all_in, total_output=tot['output'] + side['output'],
               cache_hit=round((tot['cache_read'] + side['cache_read']) / all_in, 3) if all_in else None)
    if as_json:
        print(json.dumps(out, ensure_ascii=False)); return
    f = lambda n: f'{n:,}'
    print(f"세션 {out['session']}  ({dur}분, 요청 {turns}회, 모델 {', '.join(out['models'])})")
    print(f"  입력 합계 {f(all_in)}  (캐시 읽기 {f(tot['cache_read'] + side['cache_read'])}, 적중률 {out['cache_hit']})")
    print(f"  출력 합계 {f(out['total_output'])}")
    print(f"  최대 컨텍스트 {f(peak)}")
    print(f"  서브에이전트 입력 {f(side['input'] + side['cache_write'] + side['cache_read'])} / 출력 {f(side['output'])}")

if __name__ == '__main__':
    main()
