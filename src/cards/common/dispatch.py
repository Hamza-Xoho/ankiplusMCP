import time
from .errors import CardsError, Refused
from .output import Result, render
from .log import append_log

def execute(run, build=None, cmd='cards state', args=()):
    started = time.monotonic()
    try:
        result = run()
    except CardsError as exc:
        result = Result('ERROR', [str(exc)], [], 3 if isinstance(exc, Refused) else 2,
                        readonly_paths=getattr(exc, 'readonly_paths', ()))
    except OSError as exc:
        result = Result('ERROR', [f'ERROR E10 {exc.filename or "input"}: line 1 field path: {exc.strerror} — check file paths and permissions'], [], 2)
    except (ValueError, TypeError) as exc:
        result = Result('ERROR', [f'ERROR E10 input: line 1 field value: {exc} — check input values'], [], 2)
    output = render(result)
    if build is not None and build.root.is_dir():
        try:
            if build.path('log.jsonl') in result.readonly_paths:
                print(output, end='')
                return result.exit_code
            append_log(build, cmd, list(args), result.exit_code,
                       round((time.monotonic()-started)*1000), len(output))
        except (OSError, CardsError) as exc:
            result = Result('ERROR', [f'ERROR E10 log.jsonl: {exc} — restore a writable build log'], [], 2)
            output = render(result)
    print(output, end='')
    return result.exit_code
