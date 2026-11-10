from pathlib import Path
from .errors import CardsError

class Build:
    def __init__(self, path):
        self.root = Path(path).resolve()

    def path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise CardsError('E10', f'{path}: line 1 field path escapes build', 'use a path inside --build')
        return path

    @property
    def state(self):
        return self.path('build.json')
