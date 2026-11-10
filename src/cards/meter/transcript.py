"""Read-only Claude Code transcript parsing; unknown row types are ignored."""
import json
from pathlib import Path
from cards.common.errors import CardsError

FIELDS = {'input':'input_tokens', 'cache_write':'cache_creation_input_tokens',
          'cache_read':'cache_read_input_tokens', 'output':'output_tokens'}

def require(obj, key, kind, path, line, prefix=''):
    value = obj.get(key) if isinstance(obj, dict) else None
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise CardsError('E80', f'{path}: line {line} field {prefix}{key} missing or invalid',
                         'supply the original complete Claude Code transcript')
    return value

def rows(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line, text in enumerate(stream, 1):
            try:
                row = json.loads(text)
            except (ValueError, UnicodeError) as exc:
                raise CardsError('E80', f'{path}: line {line} field JSON', 'repair the transcript JSONL') from exc
            require(row, 'type', str, path, line)
            yield line, row

def totals(calls):
    return {k:sum(c[k] for c in calls) for k in FIELDS}

def parse(path):
    calls, by_id, tools, results, compactions, attachments = [], {}, {}, {}, [], []
    for line, row in rows(path):
        typ = row['type']
        if typ == 'assistant':
            m = require(row, 'message', dict, path, line)
            mid = require(m, 'id', str, path, line, 'message.')
            model = require(m, 'model', str, path, line, 'message.')
            usage = require(m, 'usage', dict, path, line, 'message.')
            counts = {k:require(usage, v, int, path, line, 'message.usage.') for k,v in FIELDS.items()}
            if any(v < 0 for v in counts.values()):
                raise CardsError('E80', f'{path}: line {line} field message.usage negative', 'repair token counts')
            content = require(m, 'content', list, path, line, 'message.')
            ts = require(row, 'timestamp', str, path, line)
            if mid not in by_id:
                call = {'idx':len(calls)+1,'ts':ts,'model':model,'tools':[]}
                by_id[mid] = call
                calls.append(call)
            call = by_id[mid]
            # Streamed blocks carry cumulative output usage; the final row is authoritative.
            call.update(counts)
            call['ctx'] = sum(counts[k] for k in ('input','cache_write','cache_read'))
            cache = usage.get('cache_creation')
            if cache is not None:
                call['cache_1h'] = require(cache,'ephemeral_1h_input_tokens',int,path,line,'message.usage.cache_creation.')
                call['cache_5m'] = require(cache,'ephemeral_5m_input_tokens',int,path,line,'message.usage.cache_creation.')
                if call['cache_1h'] + call['cache_5m'] != counts['cache_write']:
                    raise CardsError('E80', f'{path}: line {line} field cache_creation inconsistent', 'repair cache token counts')
            for block in content:
                require({'block':block},'block',dict,path,line,'message.content.')
                require(block,'type',str,path,line,'message.content.')
                if block.get('type') != 'tool_use': continue
                tid = require(block,'id',str,path,line,'tool_use.')
                tool = require(block,'name',str,path,line,'tool_use.')
                args = require(block,'input',dict,path,line,'tool_use.')
                argument = 'file_path' if tool in {'Read','Edit','Write'} else 'command' if tool=='Bash' else 'subagent_type' if tool=='Agent' else None
                if argument: require(args,argument,str,path,line,'tool_use.input.')
                if tid not in tools:
                    event = {'idx':call['idx'],'id':tid,'tool':tool,'input':args,'line':line}
                    tools[tid] = event
                    call['tools'].append(tool)
        elif typ == 'user':
            message = require(row,'message',dict,path,line)
            content = require(message,'content',(str,list),path,line,'message.')
            if isinstance(content,list):
                for block in content:
                    require({'block':block},'block',dict,path,line,'message.content.')
                    if block.get('type') == 'tool_result':
                        tid = require(block,'tool_use_id',str,path,line,'tool_result.')
                        require(block,'content',(str,list),path,line,'tool_result.')
                        if isinstance(block['content'],list):
                            for part in block['content']:
                                require({'block':part},'block',dict,path,line,'tool_result.content.')
                        results[tid] = block
        elif typ == 'system' and row.get('subtype') == 'compact_boundary':
            m = require(row,'compactMetadata',dict,path,line)
            compactions.append({'idx':len(calls),'pre':require(m,'preTokens',int,path,line,'compactMetadata.'),
                                'post':require(m,'postTokens',int,path,line,'compactMetadata.'),
                                'trigger':require(m,'trigger',str,path,line,'compactMetadata.')})
        elif typ == 'attachment':
            attachment = require(row,'attachment',dict,path,line)
            attachments.append({'line':line, **attachment})
    if not calls:
        raise CardsError('E80', f'{path}: line 1 field message no assistant calls', 'choose a completed session')
    events = list(tools.values())
    for event in events:
        result = results.get(event['id'],{})
        content = result.get('content',[])
        event['images'] = sum(b.get('type') == 'image' for b in content if isinstance(b,dict)) if isinstance(content,list) else 0
        text = content if isinstance(content,str) else '\n'.join(b.get('text','') for b in content if isinstance(b,dict))
        event['failed'] = result.get('is_error',False) or text.lstrip().startswith('Error')
    return {'calls':calls,'totals':totals(calls),'first_ctx':calls[0]['ctx'],
            'peak_ctx':max(c['ctx'] for c in calls),'compactions':compactions,
            'events':events,'attachments':attachments}

def session(path):
    path = Path(path)
    main = parse(path)
    agents = []
    for sub in sorted(path.with_suffix('').glob('subagents/agent-*.jsonl')):
        meta_path = sub.with_suffix('.meta.json')
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
        except ValueError as exc:
            raise CardsError('E80', f'{meta_path}: line 1 field JSON', 'restore subagent metadata') from exc
        typ = require(meta,'agentType',str,meta_path,1)
        fork = require(meta,'isFork',bool,meta_path,1) if 'isFork' in meta else typ == 'fork'
        parsed = parse(sub)
        agents.append({'id':sub.stem.removeprefix('agent-'),'type':typ,'is_fork':fork, **parsed})
    main['subagents'] = agents
    return main
