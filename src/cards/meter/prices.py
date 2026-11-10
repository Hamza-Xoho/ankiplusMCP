"""API-equivalent accounting from the versioned audit price table."""
from pathlib import Path
import tomllib

def cost(calls, table=None):
    if table is None:
        table=tomllib.loads(Path(__file__).with_name('prices.toml').read_text())
    usd, unknown = 0.0, set()
    for c in calls:
        p=table.get(c['model'],{})
        if not all(k in p for k in ('input','cache_1h','cache_5m','cache_read','output')):
            unknown.add(c['model']); continue
        # No lifetime breakdown: default Claude Code cache writes have a 5m TTL.
        h=c.get('cache_1h',0); m=c.get('cache_5m',c['cache_write'])
        usd += (c['input']*p['input']+h*p['cache_1h']+m*p['cache_5m']+
                c['cache_read']*p['cache_read']+c['output']*p['output'])/1e6
    return {'usd':None if unknown else round(usd,6),
            'model':', '.join(sorted({c['model'] for c in calls})), 'unknown_prices':sorted(unknown)}
