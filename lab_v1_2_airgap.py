#!/usr/bin/env python3
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent
remote=re.compile(r'''(?:src|href)\s*=\s*["']https?://''',re.I)
bad=[]
for p in (ROOT/'lab_dashboard.html',ROOT/'map.html'):
    if p.exists() and remote.search(p.read_text(encoding='utf-8',errors='ignore')):bad.append(p.name)
if bad:raise SystemExit('❌ Runtime airgap check failed: '+', '.join(bad))
print('✅ AIRGAP CHECK — no remote runtime asset references')