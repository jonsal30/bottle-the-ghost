#!/usr/bin/env python3
import glob, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; EXPORTS=ROOT/'exports'; DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
locations=[]
def rel_source(path):
    try:return str(Path(path).resolve().relative_to(EXPORTS.resolve()))
    except Exception:return str(path)
def add_loc(lat,lng,date,source,label='',source_file='',source_index=None):
    try:
        lat=float(lat);lng=float(lng)
        if -90<=lat<=90 and -180<=lng<=180 and not(lat==0 and lng==0):locations.append({'lat':lat,'lng':lng,'date':str(date or '')[:40],'source':source,'label':str(label or '')[:200],'source_file':source_file,'source_index':source_index})
    except Exception:pass
def load(p):
    try:return json.loads(Path(p).read_text(encoding='utf-8',errors='ignore'))
    except Exception:return None
for p in glob.glob(str(EXPORTS/'**/checkins.json'),recursive=True)+glob.glob(str(EXPORTS/'**/location_history/*.json'),recursive=True):
    j=load(p);items=j if isinstance(j,list) else j.get('checkins',[]) if isinstance(j,dict) else []
    for i,it in enumerate(items[:5000]):
        if isinstance(it,dict):add_loc(it.get('latitude') or it.get('lat'),it.get('longitude') or it.get('lng'),it.get('timestamp'),'Instagram',it.get('title') or '',rel_source(p),i)
for p in glob.glob(str(EXPORTS/'**/Timeline*.json'),recursive=True)+glob.glob(str(EXPORTS/'**/Location History*.json'),recursive=True)+glob.glob(str(EXPORTS/'**/Records.json'),recursive=True):
    j=load(p);objs=j.get('timelineObjects',[]) if isinstance(j,dict) else j if isinstance(j,list) else []
    for i,o in enumerate(objs[:10000]):
        if not isinstance(o,dict):continue
        pv=o.get('placeVisit',{});place=pv.get('location',{}) if isinstance(pv,dict) else {}
        if place.get('latitudeE7') is not None and place.get('longitudeE7') is not None:add_loc(place['latitudeE7']/1e7,place['longitudeE7']/1e7,pv.get('duration',{}).get('startTimestamp'),'Google',place.get('name') or '',rel_source(p),i)
seen=set();uniq=[]
for l in locations:
    k=(round(l['lat'],5),round(l['lng'],5),l['date'][:10],l['label'])
    if k not in seen:seen.add(k);uniq.append(l)
locations=uniq[:5000];(DATA/'locations.json').write_text(json.dumps(locations,ensure_ascii=False,indent=2),encoding='utf-8')
payload=json.dumps(locations,ensure_ascii=False).replace('</','<\\/')
html='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Offline Map</title><style>:root{color-scheme:dark}body{margin:0;background:#000;color:#ddd;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}#map{position:fixed;inset:0;background:linear-gradient(#101010 1px,transparent 1px),linear-gradient(90deg,#101010 1px,transparent 1px),#050505;background-size:32px 32px}canvas{width:100%;height:100%}.panel{position:fixed;z-index:3;top:14px;left:14px;width:min(360px,calc(100vw - 28px));background:#0a0a0af2;border:1px solid #222;border-radius:14px;padding:14px}h2{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#00ff9d;margin:0 0 10px}input{width:100%;box-sizing:border-box;background:#111;border:1px solid #333;color:#fff;padding:9px;border-radius:8px}.row{padding:6px 0;border-bottom:1px solid #171717;font-size:11px}.muted{color:#666}.badge{display:inline-block;background:#1a1a1a;border:1px solid #333;padding:3px 8px;border-radius:999px;font-size:10px}a{color:#fff}.note{font-size:10px;color:#777;margin:8px 0}</style></head><body><div id="map"><canvas id="c"></canvas></div><div class="panel"><h2>🗺️ Offline Map — <span id="count"></span> pins</h2><input id="q" placeholder="Filter"><div class="note">No external map tiles or network requests. Coordinates are plotted within observed bounds.</div><div id="list" style="max-height:280px;overflow:auto"></div><p><a href="lab_dashboard.html?godmode=1">← Dashboard</a></p></div><script id="dataset" type="application/json">__LOCS__</script><script>const all=JSON.parse(document.getElementById("dataset").textContent),canvas=document.getElementById("c"),ctx=canvas.getContext("2d");let filtered=all.slice();function bounds(a){if(!a.length)return null;let minLat=90,maxLat=-90,minLng=180,maxLng=-180;for(const p of a){minLat=Math.min(minLat,p.lat);maxLat=Math.max(maxLat,p.lat);minLng=Math.min(minLng,p.lng);maxLng=Math.max(maxLng,p.lng)}return{minLat,maxLat,minLng,maxLng}}function draw(a){ctx.clearRect(0,0,canvas.width,canvas.height);document.getElementById("count").textContent=a.length;const b=bounds(a);if(!b)return;const pad=60*devicePixelRatio,w=canvas.width-pad*2,h=canvas.height-pad*2,dx=Math.max(.000001,b.maxLng-b.minLng),dy=Math.max(.000001,b.maxLat-b.minLat);for(const p of a){const x=pad+(p.lng-b.minLng)/dx*w,y=pad+(b.maxLat-p.lat)/dy*h;ctx.beginPath();ctx.arc(x,y,5*devicePixelRatio,0,Math.PI*2);ctx.fillStyle=p.source==="Google"?"#00ff9d":"#ff00ff";ctx.globalAlpha=.72;ctx.fill();ctx.globalAlpha=1}}function resize(){canvas.width=innerWidth*devicePixelRatio;canvas.height=innerHeight*devicePixelRatio;draw(filtered)}addEventListener("resize",resize);function list(a){const root=document.getElementById("list");root.replaceChildren();for(const p of a.slice(0,100)){const r=document.createElement("div");r.className="row";const b=document.createElement("span");b.className="badge";b.textContent=p.source;const t=document.createTextNode(` ${String(p.date).slice(0,10)} — ${p.label||"(unlabeled)"} `),s=document.createElement("span");s.className="muted";s.textContent=`${p.lat.toFixed(4)}, ${p.lng.toFixed(4)} • ${p.source_file}`;r.append(b,t,document.createElement("br"),s);root.append(r)}}document.getElementById("q").addEventListener("input",e=>{const q=e.target.value.toLowerCase();filtered=all.filter(p=>`${p.source} ${p.label} ${p.date} ${p.source_file}`.toLowerCase().includes(q));draw(filtered);list(filtered)});resize();list(filtered)</script></body></html>'''.replace('__LOCS__',payload)
(ROOT/'map.html').write_text(html,encoding='utf-8');print(f'✅ map.html — {len(locations)} pins — fully offline')