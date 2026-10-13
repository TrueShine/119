import csv, json, statistics as S, collections as C
from datetime import datetime
D = '/Users/jiukryu/Downloads/'
rd = lambda n, e='utf-8-sig': list(csv.DictReader(open(D + n, encoding=e)))
F = {2024: rd('화재 현황_2024_전국.csv'), 2025: rd('화재 현황_2025_전국.csv')}
W = rd('강원특별자치도_소방용수시설_20251231.csv', 'cp949')
B = rd('소방대상물 현황_2025_전국.csv')
SIDO = {'강원특별자치도': '강원'}
short = lambda s: s.replace('특별자치도', '').replace('특별자치시', '').replace('특별시', '').replace('광역시', '').replace('청북도', '북').replace('청남도', '남').replace('라북도', '북').replace('라남도', '남').replace('상북도', '북').replace('상남도', '남').replace('경기도', '경기').replace('제주', '제주')
def num(x, d=0.0):
    try: return float(x)
    except (TypeError, ValueError): return d
ts = lambda x: datetime.strptime(x[:14], '%Y%m%d%H%M%S') if len(x or '') >= 14 else None

# population (sido)
pop = {}
for r in csv.reader(open(D + '202609_202609_주민등록인구및세대현황_월간.csv', encoding='cp949')):
    if r[0].startswith('행정구역') or r[0].startswith('전국'): continue
    pop[r[0].split('  (')[0].strip()] = int(r[1].replace(',', ''))

rows = []
for y, rs in F.items():
    for r in rs:
        t = ts(r['rcpt_dt']); a = ts(r['grnds_arvl_dt'])
        resp = (a - t).total_seconds() / 60 if t and a else None
        if resp is not None and not (0 < resp < 60): resp = None
        rows.append(dict(y=y, sido=r['ctpv_nm'], sgg=r['sgg_nm'], type=r['fire_type_nm'], cause=r['igtn_dmnt_lclsf_nm'] or '미상',
            place=r['fclt_plc_lclsf_nm'] or r['fire_type_nm'], dth=int(num(r['dth_cnt'])), inj=int(num(r['injpsn_cnt'])),
            dam=num(r['prpt_dam_amt']), mon=t.month if t else 0, hr=t.hour if t else 0, wd=t.weekday() if t else 0,
            temp=num(r['hr_unit_artmp'], None) if r['hr_unit_artmp'] else None, resp=resp))
CAUSES = [c for c, _ in C.Counter(r['cause'] for r in rows).most_common(8)]
med = lambda l: round(S.median(l), 2) if l else None
top = lambda it, n=5: [[k, v] for k, v in C.Counter(it).most_common(n)]

# --- sido table
sidos = sorted({r['sido'] for r in rows})
sido_t = []
for s in sidos:
    rr = [r for r in rows if r['sido'] == s]
    n = {y: sum(1 for r in rr if r['y'] == y) for y in F}
    p = pop.get(s)
    sido_t.append(dict(name=s, short=short(s), pop=p, n24=n[2024], n25=n[2025], per10k=round(n[2025] / p * 1e4, 2) if p else None,
        dth=sum(r['dth'] for r in rr if r['y'] == 2025), inj=sum(r['inj'] for r in rr if r['y'] == 2025),
        dam24=round(sum(r['dam'] for r in rr if r['y'] == 2024)), dam25=round(sum(r['dam'] for r in rr if r['y'] == 2025)),
        resp=med([r['resp'] for r in rr if r['resp']])))

# --- golden time
def grp(f): return {k: med([r['resp'] for r in rows if r['resp'] and f(r) == k]) for k in sorted({f(r) for r in rows})}
kind = lambda r: '시(도시)' if r['sgg'].endswith('시') or r['sgg'].endswith('구') else '군(농어촌)'
gold = dict(byHour=grp(lambda r: r['hr']), byKind=grp(kind), byMonth=grp(lambda r: r['mon']),
    byKindHour={k: [med([r['resp'] for r in rows if r['resp'] and kind(r) == k and r['hr'] == h]) for h in range(24)] for k in ('시(도시)', '군(농어촌)')},
    over10=round(100 * sum(1 for r in rows if r['resp'] and r['resp'] > 10) / sum(1 for r in rows if r['resp']), 1))

# --- calendar / cause
tb = lambda t: None if t is None else max(-10, min(35, int(t // 5 * 5)))
cal = dict(causes=CAUSES,
    monCause=[[sum(1 for r in rows if r['mon'] == m and r['cause'] == c) for m in range(1, 13)] for c in CAUSES],
    hrCause=[[sum(1 for r in rows if r['hr'] == h and r['cause'] == c) for h in range(24)] for c in CAUSES],
    wdCause=[[sum(1 for r in rows if r['wd'] == w and r['cause'] == c) for w in range(7)] for c in CAUSES],
    monHr=[[sum(1 for r in rows if r['mon'] == m and r['hr'] == h) for h in range(24)] for m in range(1, 13)],
    tempBins=list(range(-10, 40, 5)),
    tempCause=[[sum(1 for r in rows if tb(r['temp']) == b and r['cause'] == c) for b in range(-10, 40, 5)] for c in CAUSES])

# --- sigungu reports
rep = {}
for r in rows: rep.setdefault(r['sido'] + ' ' + r['sgg'], []).append(r)
reports = {}
for k, rr in rep.items():
    reports[k] = dict(sido=rr[0]['sido'], sgg=rr[0]['sgg'], n24=sum(r['y'] == 2024 for r in rr), n25=sum(r['y'] == 2025 for r in rr),
        dth=sum(r['dth'] for r in rr), inj=sum(r['inj'] for r in rr), dam=round(sum(r['dam'] for r in rr)),
        causes=top(r['cause'] for r in rr), places=top(r['place'] for r in rr), resp=med([r['resp'] for r in rr if r['resp']]),
        mon=[sum(1 for r in rr if r['mon'] == m) for m in range(1, 13)], hr=[sum(1 for r in rr if r['hr'] == h) for h in range(24)])

# --- Gangwon map
wsgg = lambda n: '원주시' if n == '원주' else n
fac = C.defaultdict(list)
for r in W:
    la, lo = num(r['위도'], None), num(r['경도'], None)
    if la and lo and 36.8 < la < 39 and 127 < lo < 130: r['위도'], r['경도'] = la, lo; fac[wsgg(r['시군구명'])].append(r)
gw = [r for r in rows if r['sido'] == '강원특별자치도']
bld = C.Counter(r['sgg_nm'] for r in B if r['ctpv_nm'] == '강원특별자치도')
chk = C.Counter(r['sgg_nm'] for r in B if r['ctpv_nm'] == '강원특별자치도' and r['isf_chck_trgt_yn'] == 'Y')
mp = []
for s, ff in fac.items():
    la = [float(r['위도']) for r in ff]; lo = [float(r['경도']) for r in ff]
    yrs = [int(r['설치연도']) for r in ff if r['설치연도'].isdigit() and 1950 < int(r['설치연도']) <= 2025]
    nf = sum(1 for r in gw if r['sgg'] == s); fi = sum(1 for r in gw if r['sgg'] == s and r['type'] == '임야')
    mp.append(dict(sgg=s, lat=round(S.median(la), 4), lon=round(S.median(lo), 4), fac=len(ff), fires=nf, forest=fi,
        per100=round(nf / len(ff) * 100, 1), age=round(2025 - S.mean(yrs), 1) if yrs else None, old=sum(1 for y in yrs if 2025 - y >= 25),
        low=sum(1 for r in ff if num(r['출수압력'], None) is not None and num(r['출수압력']) < 3), bld=bld[s], chk=chk[s],
        resp=med([r['resp'] for r in gw if r['sgg'] == s and r['resp']]), types=dict(C.Counter(r['시설유형코드'] for r in ff))))
mp.sort(key=lambda x: -x['per100'])
pts = [[round(float(r['위도']), 4), round(float(r['경도']), 4)] for rs in fac.values() for r in rs]
fires_gw_cause = {m['sgg']: top((r['cause'] for r in gw if r['sgg'] == m['sgg']), 3) for m in mp}

# --- YoY
mon = lambda y: [sum(1 for r in rows if r['y'] == y and r['mon'] == m) for m in range(1, 13)]
yoy = dict(mon24=mon(2024), mon25=mon(2025),
    cause={c: [sum(1 for r in rows if r['y'] == y and r['cause'] == c) for y in F] for c in CAUSES},
    place={p: [sum(1 for r in rows if r['y'] == y and r['place'] == p) for y in F] for p, _ in C.Counter(r['place'] for r in rows).most_common(8)},
    tot=[sum(1 for r in rows if r['y'] == y) for y in F], dth=[sum(r['dth'] for r in rows if r['y'] == y) for y in F],
    inj=[sum(r['inj'] for r in rows if r['y'] == y) for y in F], dam=[round(sum(r['dam'] for r in rows if r['y'] == y) / 1e4) / 10 for y in F])

out = dict(sido=sido_t, gold=gold, cal=cal, reports=reports, map=mp, pts=pts, gwCause=fires_gw_cause, yoy=yoy)
open('data.js', 'w', encoding='utf-8').write('window.D=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';')
print(len(rows), len(reports), len(mp), len(pts)); print(mp[:3]); print(gold['byKind'], gold['over10'])
