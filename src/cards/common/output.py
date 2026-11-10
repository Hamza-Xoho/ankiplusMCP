from dataclasses import dataclass, field

@dataclass
class Result:
    status: str = 'OK'
    lines: list[str] = field(default_factory=list)
    files: list = field(default_factory=list)
    exit_code: int = 0
    summary_only: bool = False
    readonly_paths: tuple = ()
    unlimited: bool = False

def render(result, max_lines=40, max_chars=2000):
    """Budget the complete output, including status and artifact paths."""
    if result.summary_only:
        if len(result.lines) != 1 or '\n' in result.lines[0] or len(result.lines[0]) > max_chars:
            raise ValueError('invalid one-line summary')
        return result.lines[0] + '\n'
    if result.unlimited:
        return '\n'.join([result.status, *result.lines, *[f'→ {p}' for p in result.files]])+'\n'
    status = result.status
    if status not in {'OK', 'FINDINGS', 'ERROR'}:
        raise ValueError('invalid result status')
    paths = [f'→ {p}' for p in result.files]
    details = [line for item in result.lines for line in str(item).splitlines()]
    tail = '\n'.join(paths) + ('\n' if paths else '')
    prefix = status + '\n'
    kept = []
    for line in details:
        candidate = prefix + '\n'.join(kept + [line]) + '\n' + tail
        if len(candidate) > max_chars or len(candidate.splitlines()) > max_lines:
            break
        kept.append(line)
    if len(kept) < len(details):
        while True:
            note = f'… {len(details)-len(kept)} more in {result.files[0] if result.files else "log.jsonl"}'
            candidate = prefix + '\n'.join(kept + [note]) + '\n' + tail
            if len(candidate) <= max_chars and len(candidate.splitlines()) <= max_lines:
                return candidate
            if not kept:
                raise ValueError('artifact paths exceed stdout budget')
            kept.pop()
    return prefix + ('\n'.join(kept) + '\n' if kept else '') + tail
