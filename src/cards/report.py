"""Short final report, metered from the current Claude session."""
import os
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
from . import meter
from .review.apply import report_path, load_report
from .common.paths import Build
from .common.files import read_json, read_jsonl, write_text
from .common.errors import Refused, CardsError
from .common.hashing import sha256_file
from .common.output import Result


def run(args):
    b=Build(args.build); state=read_json(b.state); written=state.get('write',{})
    done=written.get('status')=='done' or any(h.get('phase')=='P6' and h.get('status')=='done' for h in state.get('history',[]))
    if not done or written.get('errors'):
        raise Refused('E72','write not done','finish Anki writes, suspend and verify, then record P6 done')
    if not b.path('write/expected.json').exists():
        raise Refused('E72','write plan missing','run cards write and finish writes')
    gate=read_json(b.path('gate.json'))
    manifest=read_json(b.path('write/provenance.json'))
    if gate.get('status')!='passed' or gate.get('drafts_sha256')!=sha256_file(b.path('drafts.jsonl')) or manifest.get('gate_sha256')!=sha256_file(b.path('gate.json')) or any(sha256_file(b.path(p))!=h for p,h in manifest.get('artifacts',{}).items()):
        raise Refused('E72','write evidence stale','repeat gate, write and Anki verification')
    expected=read_json(b.path('write/expected.json'))
    dup=int(written.get('skipped_duplicate',0))  # drafts Anki's duplicate guard refused; listed in skipped.jsonl
    if written.get('created',0)+dup!=expected['created'] or any(written.get(k)!=expected[e] for k,e in [('updated','updated'),('suspended','suspend_notes')]):
        raise Refused('E72','write counts differ from plan','verify Anki read-back and record actual counts')
    session=os.environ.get('CLAUDE_SESSION_ID')
    try:
        usage=meter.run(SimpleNamespace(build=str(b.root),session=session,latest=str(Path.cwd()) if not session else None,out=str(b.path('usage')),line=True))
    except CardsError as exc:
        # The report must not fail just because this runtime keeps no Claude transcript.
        if exc.code!='E81': raise
        usage=SimpleNamespace(status='OK',lines=['Usage: not metered (no session transcript found)'],exit_code=0)
    notes=[n for n in read_jsonl(b.path('drafts.jsonl')) if n['status']!='dropped']
    kinds=Counter(n['kind'] for n in notes); tiers=Counter(str(n['tier']) for n in notes)
    per_action={action:Counter(n['kind'] for n in notes if n['action']==action) for action in ('create','update')}
    per_tier={action:Counter(str(n['tier']) for n in notes if n['action']==action) for action in ('create','update')}
    logs=[read_json(b.path(f'review/round{k}/apply_log.json')) for k in (1,2) if b.path(f'review/round{k}/apply_log.json').exists()]
    skipped=list(read_jsonl(b.path('skipped.jsonl'))) if b.path('skipped.jsonl').exists() else []
    attempts=[]
    for k in (1,2):
        path=report_path(b,f'review/round{k}','student')
        if path.is_file(): attempts=[r['attempt']['result'] for r in load_report(path,'student') if r.get('type')=='note' and 'attempt' in r]
    lines=['# Build report',f"Deck: {read_json(b.path('target.json'))['deck']}",
           f"Written: created {written['created']}; updated {written['updated']}; suspended {written['suspended']}"+(f"; skipped as duplicate of existing notes {dup}" if dup else ''),
           'Kinds created/updated: '+', '.join(f'{k} {per_action["create"][k]}/{per_action["update"][k]}' for k in sorted(kinds)),
           'Tiers created/updated: '+', '.join(f'{k} {per_tier["create"][k]}/{per_tier["update"][k]}' for k in sorted(tiers))+f"; tier-3 share {tiers['3']/max(1,len(notes)):.0%}",
           f"Figures occluded: {kinds['io']}; skipped: {len(skipped)}",
           f"Review rounds: {len(logs)}; fixed {sum(len(x.get('applied',[])) for x in logs)}; rejected {sum(len(x.get('dropped',[])) for x in logs)}; declined {sum(len(x.get('declined',[])) for x in logs)}",
           f"Conflicts: {sum(len(x.get('conflicts',[])) for x in logs)}; resolutions: see review apply logs",
           'Independent review: '+str(state.get('review',{}).get('independent','not recorded')),
           f"Student attempts: {attempts.count('right')}/{len(attempts)} right",
           'AnKing unsuspend proposals: '+'see review/round1/maintainer/reconcile.md',
           'Search: '+expected['verify'][0],'Sync Anki.',usage.lines[0]]
    lines=[' '.join(str(line).splitlines()) for line in lines]
    text='\n'.join(lines)+'\n'; path=b.path('report.md')
    if not path.exists() or '\n'.join(path.read_text().splitlines()[1:])+'\n'!=text: write_text(path,text,'cards report')
    current=b.root.parent/'.current'
    if current.is_file() and current.read_text().strip() in (b.root.name,str(b.root)): current.unlink()
    return Result(usage.status,lines,[],usage.exit_code,unlimited=True)
