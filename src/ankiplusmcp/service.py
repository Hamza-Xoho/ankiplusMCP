"""Composition root; no model calls and no Anki client."""
from .store import Store
from .jobs import Jobs
from .sources import Sources
from .artifacts import Artifacts

from .cards import Cards
from .review import Review
from .payloads import Payloads
from .settings import PROFILES

class Service(Sources, Artifacts, Cards, Review, Payloads):
    def __init__(self, root, source_roots, profile=None):
        self.store = Store(root, source_roots)
        self.profile = profile or PROFILES['default']
        self.jobs = Jobs(self.store)

    def close(self):
        self.jobs.close()
