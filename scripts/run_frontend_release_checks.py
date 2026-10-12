"""Execute local frontend checks and retain actual result/source metadata."""
from pathlib import Path
from hashlib import sha256
import json
import re
import shutil
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/'frontend'
npm=shutil.which('npm.cmd' if sys.platform=='win32' else 'npm')
if not npm: raise SystemExit('npm is unavailable')
sources={}
for folder in ('app','components','hooks','services','utils','tests'):
    for path in sorted((FRONTEND/folder).rglob('*')):
        if path.is_file() and path.suffix in {'.ts','.tsx','.css','.js'}:
            sources[str(path.relative_to(ROOT)).replace('\\','/')]=sha256(path.read_bytes()).hexdigest()
for name in ('package.json','package-lock.json','vite.config.ts','tsconfig.json'):
    path=FRONTEND/name
    if path.is_file(): sources['frontend/'+name]=sha256(path.read_bytes()).hexdigest()
checks=[]
for task in ('test','typecheck','lint','build'):
    command=[npm,'run',task]
    started=perf_counter()
    result=subprocess.run(command,cwd=FRONTEND,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
    output=result.stdout+'\n'+result.stderr
    entry={'task':task,'exit_code':result.returncode,'seconds':perf_counter()-started,
           'output_sha256':sha256(output.encode()).hexdigest()}
    if task=='test':
        counts=re.findall(r'\btests\s+(\d+)\s*$',output,re.MULTILINE)
        if not counts: raise SystemExit('Could not parse actual Node test count')
        entry['tests']=int(counts[-1])
    checks.append(entry)
    print(task, 'PASS' if result.returncode==0 else 'FAIL')
    if result.returncode:
        print(output)
        break
changed=any(sha256((ROOT/name).read_bytes()).hexdigest()!=digest for name,digest in sources.items())
record={'checks':checks,'source_sha256':sources,'source_changed_during_run':changed,
        'all_passed':len(checks)==4 and all(x['exit_code']==0 for x in checks) and not changed}
target=ROOT/'output/release/frontend-checks.json';target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['all_passed'] else 1)
