from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import json
from pathlib import Path
import os
import tempfile
from .errors import CardsError

try:
    VERSION = version('cards')
except PackageNotFoundError:
    VERSION = '0.1.0'

def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')

def meta(tool):
    return {'tool': tool, 'version': VERSION, 'created': now()}

def write_json(path, data, tool):
    path = Path(path)
    payload = {'_meta': data.get('_meta', meta(tool)), **data}
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')

def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)

_write = atomic_write

def write_jsonl(path, records, tool):
    rows = [{'_meta': meta(tool)}, *records]
    _write(path, ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))

def write_text(path, text, tool):
    m = meta(tool)
    _write(path, f'<!-- {tool} {m["version"]} {m["created"]} -->\n' + text)

def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeError) as exc:
        line = getattr(exc, 'lineno', 1)
        raise CardsError('E11', f'{path}: line {line} field JSON: {exc}', 'repair the input file') from exc

def read_jsonl(path):
    with open(path, encoding='utf-8') as stream:
        for n, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CardsError('E11', f'{path}: line {n} field JSON', 'repair the JSONL record') from exc
            if '_meta' not in record:
                yield record
