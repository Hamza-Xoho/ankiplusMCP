import json
from .files import meta, now

def append_log(build, cmd, args, exit_code, ms, stdout_chars):
    path = build.path('log.jsonl')
    with path.open('a', encoding='utf-8') as stream:
        if path.stat().st_size == 0:
            stream.write(json.dumps({'_meta': meta(cmd)}) + '\n')
        stream.write(json.dumps({'ts': now(), 'cmd': cmd, 'args': args, 'exit': exit_code,
                                 'ms': ms, 'stdout_chars': stdout_chars}, ensure_ascii=False) + '\n')
