"""Identify numbered/bulleted items on explicitly titled objective slides."""
import re

def find(slides):
    items = []
    for s in slides:
        if not re.search(r'\b(objectives?|outcomes?|ILOs?)\b',s['title'],re.I):
            continue
        s['flags'].append('objectives')
        current = []
        for line in s['text'].splitlines():
            line = line.strip()
            if re.match(r'^(?:[•●▪-]|\d+[.)])',line):
                if current:
                    items.append({'id':f'ILO{len(items)+1}','text':'\n'.join(current),'slide':s['n']})
                current = [line]
            elif current and line:
                current.append(line)
        if current:
            items.append({'id':f'ILO{len(items)+1}','text':'\n'.join(current),'slide':s['n']})
    return {'objectives':items,'flags':[] if items else ['no_objectives']}
