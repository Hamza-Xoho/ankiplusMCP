"""Composition root; no model calls and no Anki client."""
from .publication import ArtifactPublisher
from .source_catalog import SourceCatalog
from .store import Store
from .jobs import Jobs
from .sources import Sources
from .artifacts import Artifacts

from .cards import Cards
from .review import Review
from .payloads import Payloads
from .settings import PROFILES

class Service(Sources, Artifacts, Cards, Review, Payloads):
    def __init__(self, root, source_roots, profile=None, browser='auto'):
        self.companion_connection = None
        self.store = Store(root, source_roots)
        self.profile = profile or PROFILES['default']
        self.browser = browser
        self.jobs = Jobs(self.store)
        self.source_catalog = SourceCatalog(self.store, self.jobs)
        self.publisher = ArtifactPublisher(self.store)

    def close(self):
        self.jobs.close()
