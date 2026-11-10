"""Shared source artifact validation and slide selection."""
from pathlib import Path
import re
from .errors import CardsError, Refused
from .files import read_json

def source_path(build):
    data = read_json(build.state)
    try:
        path = Path(data['source']['path']).resolve()
        if path.is_relative_to(build.root):
            raise CardsError('E21', f'{path}: line 1 field source.path inside build',
                             'keep the lecture source outside --build')
        return path, data
    except (KeyError, TypeError) as exc:
        raise CardsError('E21', f'{build.state}: line 1 field source.path missing',
                         'run cards state init on the lecture') from exc

def slides_data(build):
    path = build.path('source/slides.json')
    if not path.is_file():
        raise Refused('E22', f'{path}: line 1 field slides missing', 'run cards extract first')
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get('slides'), list) or not all(
        isinstance(s,dict) and isinstance(s.get('n'),int) and isinstance(s.get('title'),str)
        and isinstance(s.get('text'),str) and isinstance(s.get('figures'),list) for s in data['slides']):
        raise CardsError('E22', f'{path}: line 1 field slides invalid', 'run cards extract again')
    return data

def selection(spec, available):
    if not spec:
        return list(available)
    chosen = set()
    try:
        for piece in spec.split(','):
            if not re.fullmatch(r'\d+(?:-\d+)?', piece.strip()):
                raise ValueError()
            ends = list(map(int, piece.strip().split('-')))
            start, end = ends[0], ends[-1]
            if start > end or end-start > len(available):
                raise ValueError()
            chosen.update(range(start, end+1))
        if not chosen or not chosen.issubset(set(available)):
            raise ValueError()
    except ValueError as exc:
        raise CardsError('E23', 'slides: line 1 field range out of range or malformed',
                         'choose slide numbers present in source/slides.json') from exc
    return sorted(chosen)
