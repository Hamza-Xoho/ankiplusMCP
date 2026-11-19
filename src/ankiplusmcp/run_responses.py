"""Bounded previews; exact immutable journal records have separate slice reads."""
import json
from .store import DomainError


def page(rows,offset=0,limit=10,budget=24000):
    if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:
        raise DomainError('LIMIT','Use a nonnegative offset and a limit from 1 to 100.')
    result=[];size=0
    for row in rows[offset:offset+limit]:
        length=len(json.dumps(row,ensure_ascii=False).encode())
        if size+length>budget:
            if not result:raise DomainError('LIMIT','Read this complete item through read_run_record slices.')
            break
        result.append(row);size+=length
    end=offset+len(result)
    return result,end if end<len(rows) else None


def application_summary(value,offset=0,limit=10):
    rows,next_offset=page(value['results'],offset,limit)
    return {**value,'results':rows,'total':len(value['results']),'next_offset':next_offset,
            'pending_operation_ids':value['pending_operation_ids'][:100],
            'pending_operations':len(value['pending_operation_ids'])}
