#!/usr/bin/env python3
"""Run workshop references in disposable containers; require full marks."""
from pathlib import Path
import argparse, json, subprocess, sys, tempfile
import yaml
ROOT = Path(__file__).resolve().parents[1]
manifest = yaml.safe_load((ROOT / 'workshop.course.yaml').read_text())
parser = argparse.ArgumentParser()
parser.add_argument('--advanced-only', action='store_true')
args = parser.parse_args()
failed = []
with tempfile.TemporaryDirectory(prefix='workshop-smoke-') as tmp:
    for entry in manifest['schedule']:
        if args.advanced_only and not entry['id'].startswith('WS-ADV-'): continue
        lab = ROOT / 'labs/13-workshop' / entry['id']
        result = Path(tmp) / (entry['id'] + '.json')
        cp = subprocess.run([sys.executable, str(ROOT/'grader/runner.py'), '--lab', str(lab), '--submission', str(lab/'reference/solution.sh'), '--seed', '424242', '--json-out', str(result)], capture_output=True, text=True)
        data = json.loads(result.read_text()) if result.exists() else {}
        ok = cp.returncode == 0 and data.get('score') == data.get('max_score') == 100
        print(f"{'PASS' if ok else 'FAIL'} {entry['id']}: {data.get('score')}/100", flush=True)
        if not ok:
            print(cp.stdout + cp.stderr, flush=True)
            failed.append(entry['id'])
    # A submission that does nothing must not pass any advanced scenario.
    noop = Path(tmp)/'noop.sh'
    noop.write_text('#!/usr/bin/env bash\nexit 0\n')
    for lab in sorted((ROOT/'labs/13-workshop').glob('WS-ADV-*')):
        result = Path(tmp)/(lab.name+'-noop.json')
        cp = subprocess.run([sys.executable,str(ROOT/'grader/runner.py'),'--lab',str(lab),'--submission',str(noop),'--seed','17','--json-out',str(result)],capture_output=True,text=True)
        data = json.loads(result.read_text()) if result.exists() else {}
        ok = cp.returncode == 2 and data.get('passed') is False
        print(f"{'PASS' if ok else 'FAIL'} {lab.name} rejects no-op",flush=True)
        if not ok: failed.append(lab.name+'-noop')
sys.exit(bool(failed))
