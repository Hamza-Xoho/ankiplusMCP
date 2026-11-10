"""`cards build`: the CLI owns the pipeline; the agent works only at pauses.

Phases P0, P1, P3, P5 and P7 run without input. P2, P4 and P6 stop with a
short prompt naming the files to read, what to produce and the resume command.
Every stop is exit 0; a failed gate is the only routine exit 1.
"""
import os
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from . import state, extract, target, check, render, gate, report
from .review import packets, apply
from .review.apply import load_report, report_path
from .write import plan
from .common.errors import CardsError, Refused
from .common.files import read_json, read_jsonl, _write
from .common.output import Result
from .common.paths import Build

NEXT = {f'P{i}': f'P{i+1}' for i in range(7)} | {'P7': 'done'}


def _args(build, **values):
    return SimpleNamespace(build=str(build.root), **values)


def builds_root():
    return Path(os.environ.get('CARDS_BUILDS', 'builds')).expanduser().resolve()


def active_build(args):
    """The --build folder, or the one builds/.current points at."""
    if getattr(args, 'build', None):
        build = Build(args.build)
        if not build.state.is_file():
            raise Refused('E73', f'{build.state}: line 1 field build missing',
                          'run cards build --pdf <path> first')
        return build
    pointer = builds_root() / '.current'
    if not pointer.is_file():
        raise Refused('E73', 'no build in progress',
                      'run cards build --pdf <path>, or pass --build')
    name = pointer.read_text().strip()
    build = Build(Path(name) if Path(name).is_absolute() else builds_root() / name)
    if not build.state.is_file():
        raise Refused('E73', f'{build.state}: line 1 field build missing',
                      'run cards build --pdf <path>')
    return build


def _phase(build, name, status):
    return state.run(SimpleNamespace(action='phase', build=str(build.root),
                                     phase=name, status=status))


def ensure_started(build, data):
    last = data['history'][-1] if data['history'] else None
    if not last or last.get('phase') != data['phase'] or last.get('status') != 'start':
        _phase(build, data['phase'], 'start')
        data = state.load(build)
    return data


def require_predecessor(build, data):
    """No phase may run before the one before it is marked done."""
    if data['phase'] == 'done':
        return
    index = state.PHASES.index(data['phase'])
    if not index:
        return
    previous = state.PHASES[index-1]
    if any(entry.get('phase') == previous and entry.get('status') == 'done'
           for entry in data['history']):
        return
    raise Refused('E73', f'{data["phase"]}: previous phase {previous} not marked done',
                  'complete the preceding phase, then run cards build --continue')


def finish(build, name, lines):
    """Mark the phase done and open the next one, so resume is idempotent."""
    _phase(build, name, 'done')
    _phase(build, NEXT[name], 'start')
    return list(lines)


def _first(result, fallback):
    return result.lines[0] if result.lines else fallback


def _show(path):
    """Prefer a path relative to the working directory: fewer tokens on screen."""
    try:
        return str(Path(path).relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _page_images(build):
    """Materialise flagged page images reviewers need, for PDF sources only."""
    data = state.load(build)
    if data['source'].get('kind') != 'pdf':
        return
    cited = {ref for n in read_jsonl(build.path('drafts.jsonl'))
             if isinstance(n, dict) for ref in (n.get('source_ref') or []) if isinstance(ref, int)}
    slides = read_json(build.path('source/slides.json'))['slides']
    from . import source
    for slide in slides:
        if not (slide.get('flags') and any(abs(slide['n'] - c) <= 1 for c in cited)):
            continue
        if build.path(f'source/pages/p{slide["n"]:02d}.png').exists():
            continue
        source.run(SimpleNamespace(build=str(build.root), slides=None, all=False, grep=None,
                                   figure=None, page_image=slide['n']))


def preflight(build, data, args):
    lines = ['P0: preflight recorded · Anki checks are MCP calls',
             '  tools.anki.model_names → ColdRecall Cloze must exist',
             '  tools.anki.list_decks → save the names as existing-decks.json',
             f'  cards state set --build {build.root} facts.anki_reachable=true facts.note_type_exists=true']
    return finish(build, 'P0', lines)


def extract_and_target(build, data, args):
    lines = []
    if not build.path('source/slides.json').is_file():
        lines.append('P1: ' + _first(extract.run(_args(build, slides=None)), 'extracted'))
    else:
        lines.append('P1: extraction cached')
    target_path = build.path('target.json')
    target_data = read_json(target_path) if target_path.is_file() else {}
    if not target_data.get('confident'):
        decks = build.path('existing-decks.json')
        if not decks.is_file():
            _write(decks, '[]\n')
            lines.append('P1: existing-decks.json missing · targeted with an empty deck list')
            target_data = {}
        if not target_data:
            result = target.run(SimpleNamespace(build=str(build.root), existing_decks=str(decks),
                                                course=None, number=None, title=None,
                                                subject=None, system=None))
            lines.append('P1: ' + _first(result, 'targeted'))
            target_data = read_json(target_path)
        if not target_data.get('confident'):
            return Result(lines=[*lines, '⏸️  P1 Target needs identity',
                                 'Action: cards target --build <build> --existing-decks '
                                 f'{build.path("existing-decks.json")} --course <course> --number <n> --title "<title>"',
                                 'Resume: cards build --continue'], files=[build.state])
    lines.append(f"P1: deck “{target_data['deck']}” · create_deck "
                 f"{str(target_data.get('create_deck')).lower()}")
    return finish(build, 'P1', lines)


def drafting(build, data, args):
    drafts = build.path('drafts.jsonl')
    notes = list(read_jsonl(drafts)) if drafts.is_file() else []
    active = [n for n in notes if isinstance(n, dict) and n.get('status') != 'dropped']
    if active:
        return finish(build, 'P2', [f'P2: {len(active)} active drafts · {len(notes)-len(active)} dropped'])
    lines = ['⏸️  P2 Drafting',
             f'Source: {_show(build.path("source/slides.json"))}',
             f'Summary: {_show(build.path("source/slides_summary.json"))} (pre-digested key facts)',
             'Draft rules: load phases/draft.md from the installed ankiv2 skill',
             f'Figures: cards figures --build {_show(build.root)} --summary (text only; never read full PNGs)',
             f'Action: write drafts.jsonl and skipped.jsonl in {_show(build.root)}']
    slides = read_json(build.path('source/slides.json'))['slides']
    labelled = sum(1 for slide in slides for figure in slide.get('figures') or []
                   if len(figure.get('ocr_labels') or []) >= 5)
    if labelled:
        lines.append(f'Figures: {labelled} labelled diagrams — read phases/occlusion.md, then '
                     'verify only the generated *_preview.png')
    target_data = read_json(build.path('target.json'))
    if target_data.get('create_deck'):
        lines.append(f'Also: tools.anki.create_deck (“{target_data["deck"]}”), then '
                     f'facts.deck_exists=true')
    lines.append('Resume: cards build --continue')
    return Result(lines=lines, files=[build.state])


def checked_and_rendered(build, data, args):
    result = check.run(_args(build))
    findings = read_json(build.path('checks/check.json'))['findings']
    blockers = [f for f in findings if f.get('severity') == 'blocker']
    if blockers:
        counts = Counter(f.get('code', '?') for f in blockers)
        return Result(lines=['⏸️  P3 Check blockers',
                             f'{len(blockers)} blockers: ' + ', '.join(
                                 f'{code}×{count}' for code, count in counts.most_common(6)),
                             f'Findings: {build.path("checks/check.json")}',
                             'Action: fix drafts.jsonl, then run cards build --continue',
                             'Resume: cards build --continue'], files=[build.state])
    rendered = render.run(_args(build, only=None, per_sheet=8, anki_html=None))
    return finish(build, 'P3', [f'P3: {_first(rendered, "rendered")}'])


def _log(build, rnd):
    path = build.path(f'review/round{rnd}/apply_log.json')
    return read_json(path) if path.is_file() else None


def _reports_ready(build, rnd):
    return all(report_path(build, f'review/round{rnd}', who).is_file()
               for who in ('maintainer', 'student'))


def _packetized(build, rnd):
    return build.path(f'review/round{rnd}/maintainer/PROMPT.md').is_file()


def _rerender(build, ids):
    active = {n['id'] for n in read_jsonl(build.path('drafts.jsonl'))
              if isinstance(n, dict) and isinstance(n.get('id'), str) and n.get('status') != 'dropped'}
    if not ids or not set(ids) <= active:
        # apply lists dropped notes as changed; they no longer exist, so the sheets shifted.
        render.run(_args(build, only=None, per_sheet=8, anki_html=None))
        return
    try:
        render.run(_args(build, only=','.join(ids), per_sheet=8, anki_html=None))
    except Refused:
        # Notes were dropped by review, so the sheet manifest legitimately changed.
        render.run(_args(build, only=None, per_sheet=8, anki_html=None))


def _verdict_conflicts(build, rnd):
    """Notes one reviewer passed and the other sent back."""
    base = build.path(f'drafts.r{rnd}.jsonl')
    if not base.is_file():
        base = build.path('drafts.jsonl')
    notes = [n for n in read_jsonl(base) if isinstance(n, dict) and isinstance(n.get('id'), str)]
    ids = {n['id'] for n in notes}
    fields = {n['id']: n.get('fields', {}) for n in notes}
    verdicts = {}
    for who in ('maintainer', 'student'):
        path = report_path(build, f'review/round{rnd}', who)
        for row in load_report(path, who, ids, fields):
            if row.get('type') == 'note':
                verdicts.setdefault(row['note_id'], set()).add(row['verdict'])
    return {ident for ident, seen in verdicts.items()
            if 'pass' in seen and seen & {'fix', 'reject'}}


def review_scope(build, rnd, log):
    """(ids, full_round) when round 2 is needed, else None."""
    if rnd >= 2:
        return None
    hard = {c['id'] for c in log.get('conflicts', [])
            if isinstance(c, dict) and isinstance(c.get('id'), str)}
    blocker_ids = {b['note_id'] for b in log.get('open_blockers', [])
                   if isinstance(b, dict) and isinstance(b.get('note_id'), str)}
    ids = sorted(hard | _verdict_conflicts(build, rnd) | blocker_ids)
    unresolved = log.get('unresolved') or []
    blockers = log.get('open_blockers') or []
    css = log.get('css_fix_needed') or []
    if not ids and not unresolved and not blockers and not css:
        return None
    full = len(ids) > 3 or bool(unresolved) or bool(css)
    return ids, full


def _pause_review(build, rnd, scope, lines):
    folder = build.path(f'review/round{rnd}')
    header = f'⏸️  P4 Review (round {rnd})'
    actions = [header,
               f'Packets: {_show(folder)}/maintainer/PROMPT.md',
               f'         {_show(folder)}/student/PROMPT.md',
               'Action: launch one anki-maintainer and one anki-student subagent, '
               'each with its PROMPT.md path only',
               f'Reports: {_show(folder)}/{{maintainer,student}}_report.md (Markdown format)']
    if scope:
        ids, full = scope
        if full:
            actions.insert(1, 'Scope: full round 2 (conflicts, blockers or CSS fixes remain)')
        else:
            actions.insert(1, 'Scope: ' + (','.join(ids) if ids else 'none'))
    actions.append('Resume: cards build --continue')
    return Result(lines=[*lines, *actions], files=[build.state])


def reviewed(build, data, args):
    rounds = [k for k in (1, 2) if build.path(f'review/round{k}').exists()]
    rnd = max(rounds, default=1)
    log = _log(build, rnd)
    lines = []
    if log is None:
        if not _reports_ready(build, rnd):
            if not _packetized(build, rnd):
                _page_images(build)
                packets.run(_args(build, round=rnd, only=None, student_subset='all'))
            return _pause_review(build, rnd, None, lines)
        result = apply.run(SimpleNamespace(build=str(build.root), round=rnd, decline=[]))
        log = _log(build, rnd)
        lines.append(f'P4: round {rnd} applied · {_first(result, "ok")}')
    changed = [i for i in log.get('changed_ids', []) if isinstance(i, str)]
    if changed:
        check.run(_args(build))
        _rerender(build, changed)
        lines.append(f'P4: re-checked and re-rendered {len(changed)} changed notes')
    scope = review_scope(build, rnd, log)
    if scope:
        if not _reports_ready(build, 2):
            if not _packetized(build, 2):
                ids, full = scope
                packets.run(_args(build, round=2, only=None if full else (','.join(ids) or None),
                                  student_subset='all'))
            return _pause_review(build, 2, scope, lines)
        result = apply.run(SimpleNamespace(build=str(build.root), round=2, decline=[]))
        log = _log(build, 2)
        lines.append(f'P4: round 2 applied · {_first(result, "ok")}')
        changed = [i for i in log.get('changed_ids', []) if isinstance(i, str)]
        if changed:
            check.run(_args(build))
            _rerender(build, changed)
            lines.append(f'P4: re-checked and re-rendered {len(changed)} changed notes')
    return finish(build, 'P4', lines)


def gated(build, data, args):
    rounds = [k for k in (1, 2) if _log(build, k)]
    if not rounds:
        raise Refused('E73', 'review apply log missing',
                      'launch both reviewers and run cards build --continue')
    latest = max(rounds)
    missing = [who for who in ('maintainer', 'student')
               if not report_path(build, f'review/round{latest}', who).is_file()]
    if missing:
        raise Refused('E73', 'review report missing: ' + ', '.join(missing),
                      'launch both reviewers and run cards build --continue')
    result = gate.run(_args(build))
    if result.exit_code != 0:
        return Result('FINDINGS', ['P5: gate failed', *result.lines[:8],
                                   f'Gate: {build.path("gate.json")}'],
                      [build.path('gate.json')], 1)
    return finish(build, 'P5', [f'P5: {_first(result, "gate passed")}'])


def written(build, data, args):
    gate_path = build.path('gate.json')
    gate_data = read_json(gate_path) if gate_path.is_file() else {}
    if gate_data.get('status') != 'passed':
        raise Refused('E73', 'gate not passed', 'run cards build --continue to pass the gate first')
    receipts = build.path('write/receipts.json')
    if not receipts.is_file():
        plan.run(_args(build))
        batches = sorted(build.path('write/batches').glob('*.json'))
        return Result(lines=['⏸️  P6 Write to Anki',
                             f'Batches: {_show(build.path("write/batches"))} ({len(batches)} files)',
                             f'Plan: {_show(build.path("write/expected.json"))}',
                             'Action: add each batch with tools.anki.add_notes; apply updates and '
                             'suspend per expected.json; write write/receipts.json',
                             'Resume: cards build --continue'], files=[build.state])
    result = state.record_write(build, state.load(build))
    return finish(build, 'P6', [f'P6: {_first(result, "write recorded")}'])


def reported(build, data, args):
    result = report.run(_args(build))
    lines = [f'P7: report written · {_show(build.path("report.md"))}']
    lines.extend(result.lines[:1])
    return finish(build, 'P7', lines)


BODIES = {'P0': preflight, 'P1': extract_and_target, 'P2': drafting, 'P3': checked_and_rendered,
          'P4': reviewed, 'P5': gated, 'P6': written, 'P7': reported}


def run(args):
    if getattr(args, 'pdf', None):
        created = state.run(SimpleNamespace(action='init', source=args.pdf, job='build'))
        build = Build(Path(created.files[0]).parent)
    else:
        build = active_build(args)
    data = state.load(build)
    if data['phase'] == 'done':
        return Result(lines=[f'done · {build.root.name} complete'], files=[build.state])
    require_predecessor(build, data)
    data = ensure_started(build, data)
    lines = []
    while data['phase'] != 'done':
        require_predecessor(build, data)
        name = data['phase']
        outcome = BODIES[name](build, data, args)
        if isinstance(outcome, Result):
            return Result(outcome.status, [*lines, *outcome.lines], outcome.files,
                          outcome.exit_code)
        lines.extend(outcome)
        data = state.load(build)
    lines.append(f'done · {build.root.name} complete')
    return Result(lines=lines, files=[build.state])