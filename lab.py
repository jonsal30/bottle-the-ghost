#!/usr/bin/env python3
import argparse, csv, glob, json, random
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORTS = ROOT / 'exports'
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
events, msgs = [], defaultdict(list)
privacy = {'advertisers': [], 'logins': [], 'apps': []}
parse_errors = []

def rel_source(path):
    try: return str(Path(path).resolve().relative_to(EXPORTS.resolve()))
    except Exception: return str(path)

def parse_dt(value):
    if value is None: return None
    try:
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1e12: ts /= 1000
            if ts <= 1e9: return None
            return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
        if isinstance(value, str):
            s = value.strip()
            if not s: return None
            if s.isdigit(): return parse_dt(int(s))
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            if dt.tzinfo: dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
    except Exception:
        return None

def add(value, platform, typ, text='', person='', source_file='', source_index=None):
    dt = parse_dt(value)
    if not dt: return
    rec = {'date': dt, 'platform': str(platform or 'Unknown')[:80], 'type': str(typ or 'activity')[:80],
           'text': str(text or '')[:2000], 'person': str(person or '')[:200],
           'source_file': source_file, 'source_index': source_index}
    events.append(rec)
    if rec['type'] in ('dm', 'message') and rec['person']: msgs[rec['person']].append(dt)

def load_json(path):
    try: return json.loads(Path(path).read_text(encoding='utf-8', errors='ignore'))
    except Exception as exc:
        parse_errors.append({'file': rel_source(path), 'error': str(exc)[:200]})
        return None

def scan_messages():
    for p in glob.glob(str(EXPORTS / '**/messages/inbox/**/*.json'), recursive=True):
        j = load_json(p)
        if not isinstance(j, dict): continue
        title = j.get('title') or Path(p).parent.name
        for idx, m in enumerate(j.get('messages', [])[:4000]):
            if isinstance(m, dict): add(m.get('timestamp_ms'), 'Instagram', 'dm', m.get('content') or '', title, rel_source(p), idx)

def scan_ads():
    keys = ('advertisers_using_your_activity_or_information', 'advertisers_who_uploaded_a_contact_list_with_your_information', "advertisers_you've_interacted_with")
    for p in glob.glob(str(EXPORTS / '**/ads_information/**/*.json'), recursive=True):
        j = load_json(p)
        if not isinstance(j, dict): continue
        for key in keys:
            rows = j.get(key, [])
            if not isinstance(rows, list): continue
            for idx, item in enumerate(rows[:1000]):
                name = (item.get('advertiser_name') or item.get('name') or json.dumps(item, ensure_ascii=False)[:120]) if isinstance(item, dict) else str(item)[:120]
                privacy['advertisers'].append({'name': name, 'source_file': rel_source(p), 'source_index': idx})

def extract_list_payload(j):
    if isinstance(j, list): return j
    if not isinstance(j, dict): return []
    for key in ('account_history_login_history', 'login_history', 'apps_and_websites', 'apps'):
        if isinstance(j.get(key), list): return j[key]
    lists = [v for v in j.values() if isinstance(v, list)]
    return lists[0] if len(lists) == 1 else []

def scan_security_apps():
    paths = []
    for pat in ('**/login*.json', '**/apps_and_websites/**/*.json'):
        paths += glob.glob(str(EXPORTS / pat), recursive=True)
    for p in sorted(set(paths)):
        for idx, item in enumerate(extract_list_payload(load_json(p))[:1000]):
            if not isinstance(item, dict): continue
            source, blob = rel_source(p), json.dumps(item, ensure_ascii=False)
            if 'ip' in blob.lower(): privacy['logins'].append({'ip_address': item.get('ip_address',''), 'city': item.get('city',''), 'timestamp': item.get('timestamp',''), 'source_file': source, 'source_index': idx})
            else: privacy['apps'].append({'name': str(item.get('name') or item.get('app_name') or item)[:160], 'source_file': source, 'source_index': idx})
            add(item.get('timestamp'), 'Security', 'login', blob[:500], '', source, idx)

def scan_activity():
    paths = []
    for pat in ('**/MyActivity.json', '**/data/tweets.js', '**/Watch*.json'):
        paths += glob.glob(str(EXPORTS / pat), recursive=True)
    for p in sorted(set(paths)):
        try:
            txt = Path(p).read_text(encoding='utf-8', errors='ignore').replace('window.YTD.tweets.part0 = ', '', 1)
            j = json.loads(txt)
        except Exception as exc:
            parse_errors.append({'file': rel_source(p), 'error': str(exc)[:200]}); continue
        if not isinstance(j, list): continue
        for idx, item in enumerate(j[:5000]):
            if isinstance(item, dict):
                add(item.get('Date') or item.get('created_at') or item.get('time') or item.get('timestamp'), Path(p).parts[-2] if len(Path(p).parts)>1 else 'Activity', 'activity', json.dumps(item, ensure_ascii=False)[:500], '', rel_source(p), idx)

def add_demo_data():
    now = datetime.utcnow(); people = [f'Demo Person {i}' for i in range(1,10)]; platforms = ['Instagram','X','TikTok','Discord','YouTube']
    for i in range(250):
        dt = now - timedelta(days=random.randint(0,600), hours=random.randint(0,23))
        add(dt.isoformat(), random.choice(platforms), random.choice(['dm','like','activity']), f'DEMO sample {i}', random.choice(people), '__demo__', i)

def ready(e):
    out = dict(e); out['date'] = e['date'].isoformat(); return out

def safe_script_json(obj): return json.dumps(obj, ensure_ascii=False).replace('</','<\\/')

ap = argparse.ArgumentParser(); ap.add_argument('--demo', action='store_true'); args = ap.parse_args()
print(f'💀 Scanning only {EXPORTS}')
scan_messages(); scan_ads(); scan_security_apps(); scan_activity()
synthetic = 0
if not events and args.demo: add_demo_data(); synthetic = len(events)
events.sort(key=lambda x:x['date'])
by_platform = Counter(e['platform'] for e in events); by_month = Counter(e['date'].strftime('%Y-%m') for e in events); by_hour = Counter(e['date'].hour for e in events); by_person = Counter(e['person'] for e in events if e['person'])
now = datetime.utcnow(); decay = []
for person, dates in msgs.items():
    dates = sorted(dates); days = max(0,(now-dates[-1]).days); freq = len(dates)
    if days > 60 and freq > 10: decay.append({'person':person,'days':days,'freq':freq,'score':int(freq*2+days/3)})
with (DATA/'events.jsonl').open('w',encoding='utf-8') as f:
    for e in events: f.write(json.dumps(ready(e),ensure_ascii=False)+'\n')
for name,key in (('advertisers.json','advertisers'),('logins.json','logins'),('apps.json','apps')): (DATA/name).write_text(json.dumps(privacy[key],ensure_ascii=False,indent=2),encoding='utf-8')
(DATA/'parse_errors.json').write_text(json.dumps(parse_errors,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'_lab_timeline.csv').open('w',newline='',encoding='utf-8') as f:
    fields=['date','platform','type','person','text','source_file','source_index']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); [w.writerow(ready(e)) for e in events]
manifest={'build':'1.2.1','mode':'demo' if synthetic else 'truth','generated_at_utc':datetime.utcnow().replace(microsecond=0).isoformat()+'Z','events':len(events),'advertisers':len(privacy['advertisers']),'logins':len(privacy['logins']),'apps':len(privacy['apps']),'parse_errors':len(parse_errors),'synthetic_records':synthetic,'scan_root':'exports/'}
(DATA/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
D={'byPlatform':dict(by_platform),'byMonth':dict(sorted(by_month.items())),'byHour':{str(i):by_hour.get(i,0) for i in range(24)},'byPerson':dict(by_person.most_common(12)),'recent':[ready(e) for e in sorted(events,key=lambda x:x['date'],reverse=True)[:1000]],'decay':sorted(decay,key=lambda x:x['score'],reverse=True)[:30],'advertisers':privacy['advertisers'][:300],'manifest':manifest}
html='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cloud in a Bottle</title><style>:root{color-scheme:dark;--g:#ff00ff}*{box-sizing:border-box}body{background:#000;color:#ddd;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;margin:0;padding:20px}.card{background:#0a0a0a;border:1px solid #1e1e1e;border-radius:16px;padding:20px;margin-bottom:16px}.god{border-color:#ff00ff55}.truth{border-color:#00ff9d55}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:900px){.grid{grid-template-columns:1fr}}h1{font-size:28px}h2{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--g);margin:0 0 12px}.muted{color:#777}.badge{display:inline-block;background:#151515;border:1px solid #2a2a2a;padding:4px 10px;border-radius:999px;font-size:11px;margin:3px}.warn{background:#ff005522;border-color:#ff0055}.barRow{display:grid;grid-template-columns:120px 1fr 56px;gap:8px;align-items:center;margin:7px 0;font-size:11px}.bar{height:10px;background:#171717;border-radius:999px;overflow:hidden}.fill{height:100%;background:#444}.fill.g{background:var(--g)}.row{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid #141414;font-size:12px;align-items:flex-start}.hidden{display:none}input{width:100%;background:#111;border:1px solid #333;color:#fff;padding:12px;border-radius:12px}a.btn{display:inline-block;background:transparent;color:#fff;border:1px solid #333;padding:10px 14px;border-radius:10px;text-decoration:none;font-weight:800;font-size:11px;margin:4px}.small{font-size:11px}</style></head><body><h1 id="title">🖤 Cloud in a Bottle</h1><div id="subtitle" class="muted"></div><div id="empty" class="card truth hidden"><h2>Truth Mode</h2><p>No supported records were found. Nothing was fabricated.</p></div><div class="grid"><div class="card"><h2>Platform Mix</h2><div id="platform"></div></div><div class="card"><h2>Monthly Timeline</h2><div id="month"></div></div><div class="card"><h2>Activity by Hour</h2><div id="hour"></div></div><div class="card"><h2>Top People</h2><div id="people"></div></div></div><div id="god" class="hidden"><div class="card god"><h2>💀 GOD MODE — Relationship Decay Signal</h2><div id="decay"></div><p class="small muted">Heuristic only: observed message frequency plus recency.</p></div><div class="card god"><h2>🧠 Advertiser Records</h2><div id="advertisers"></div></div></div><div class="card"><h2>Searchable Memory</h2><input id="q" placeholder="Search platform, person, text, or source file"><div id="tl" style="max-height:620px;overflow:auto;margin-top:10px"></div></div><div class="card truth"><h2>Source Integrity</h2><div id="manifest"></div><a class="btn" href="map.html?godmode=1">Open Offline Map</a></div><script id="dataset" type="application/json">__DATA__</script><script>"use strict";const D=JSON.parse(document.getElementById("dataset").textContent),god=new URLSearchParams(location.search).has("godmode");if(god){document.getElementById("god").classList.remove("hidden");document.getElementById("title").textContent="💀 Cloud in a Bottle — GOD MODE"}document.getElementById("subtitle").textContent=`${D.manifest.events} events • mode: ${D.manifest.mode} • synthetic: ${D.manifest.synthetic_records} • scan root: ${D.manifest.scan_root}`;if(!D.manifest.events)document.getElementById("empty").classList.remove("hidden");function el(t,x,c){const n=document.createElement(t);if(x!==undefined)n.textContent=String(x);if(c)n.className=c;return n}function bars(id,obj,g=false,limit=18){const root=document.getElementById(id),rows=Object.entries(obj).slice(-limit),max=Math.max(1,...rows.map(x=>Number(x[1])||0));root.replaceChildren();for(const[k,v]of rows){const r=el("div",undefined,"barRow"),b=el("div",undefined,"bar"),f=el("div",undefined,"fill"+(g?" g":""));f.style.width=(100*Number(v)/max)+"%";b.append(f);r.append(el("span",k),b,el("span",v));root.append(r)}}bars("platform",D.byPlatform,true);bars("month",D.byMonth,false,16);bars("hour",D.byHour,true,24);bars("people",D.byPerson,true,12);const dec=document.getElementById("decay");for(const d of D.decay){const r=el("div",undefined,"row");r.append(el("span",d.person,"badge"),el("span",`last ${d.days}d ago`),el("span",`${d.freq} msgs`),el("span",`score ${d.score}`,"muted"));dec.append(r)}if(!D.decay.length)dec.append(el("span","No decay signals met the heuristic threshold.","muted"));const ad=document.getElementById("advertisers");for(const a of D.advertisers.slice(0,120)){const s=el("span",a.name,"badge warn");s.title=a.source_file||"";ad.append(s)}if(!D.advertisers.length)ad.append(el("span","No advertiser records found.","muted"));function render(list){const root=document.getElementById("tl");root.replaceChildren();for(const r of list){const row=el("div",undefined,"row"),date=el("span",(r.date||"").slice(0,10),"muted"),right=el("div");date.style.minWidth="88px";right.append(el("span",r.text||""),el("br"),el("span",r.source_file||"","muted small"));row.append(date,el("span",r.platform,"badge"),el("span",r.person||"","badge"),right);root.append(row)}}render(D.recent);document.getElementById("q").addEventListener("input",e=>{const q=e.target.value.toLowerCase();render(D.recent.filter(r=>`${r.platform} ${r.person} ${r.text} ${r.source_file}`.toLowerCase().includes(q)))});const m=document.getElementById("manifest");for(const[k,v]of Object.entries(D.manifest)){const r=el("div",undefined,"row");r.append(el("span",k,"muted"),el("span",v));m.append(r)}</script></body></html>'''.replace('__DATA__', safe_script_json(D))
(ROOT/'lab_dashboard.html').write_text(html, encoding='utf-8')
print(f"✅ lab_dashboard.html — {len(events)} events — mode={manifest['mode']}")