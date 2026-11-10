"""Compact lecture map with lexical (not authoritative) objective links."""
import re

def generate(lecture, slides, objectives):
    header = f"# {lecture} · {len(slides)} slides · {len(objectives)} objectives · {sum(bool(s['flags']) for s in slides)} flagged"
    lines = [header]
    for s in slides:
        words = set(re.findall(r'[a-z]{5,}',s['text'].lower()))
        links = []
        for o in objectives:
            terms = set(re.findall(r'[a-z]{5,}',o['text'].lower()))
            if o['slide']==s['n'] or len(terms & words)>=2:
                links.append(('' if o['slide']==s['n'] else '~')+o['id'])
        figs = s['figures']
        labels = [r['text'] for f in figs for r in f['ocr_labels'] if r['conf'] >= 75][:2]
        label_text = ' ('+', '.join(labels)[:22]+')' if labels else ''
        tail = f" | {s['word_count']}w | fig:{len(figs)}{label_text} | {','.join(links) or '—'} | {','.join(s['flags']) or '—'}"
        prefix = f"{s['n']:02d} | "
        # Keep flags, count and links; truncate the title to the remaining budget.
        tail = tail[:85]
        title = s['title'].replace('\n',' ').replace('|','/')
        if len(prefix+title+tail)>110 and label_text:
            tail = tail.replace(label_text,'')
        room = max(0,110-len(prefix)-len(tail))
        if len(title)>room:
            title = title[:max(0,room-1)]+'…' if room else ''
        lines.append(prefix+title+tail)
    return '\n'.join(lines)+'\n'
