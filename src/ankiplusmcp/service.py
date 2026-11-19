"""Composition root for local helpers; explicit companion factory is supplied by the launcher."""
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
        if source_roots is None and (self.store.root/'.student-workflows/configuration/current.json').exists():
            from .configuration import ConfigStore
            saved,pointer=ConfigStore(self.store.root/'.student-workflows')._current()
            if pointer.get('change_id'):self.store.set_source_roots(saved.source_roots,'preferences')
        self._launch_profile = profile or PROFILES['default']
        self.browser = browser
        self.jobs = Jobs(self.store)
        self.source_catalog = SourceCatalog(self.store, self.jobs)
        self.publisher = ArtifactPublisher(self.store)

    @property
    def profile(self):
        """Launch style seeds setup; explicit student preferences govern future defaults."""
        if not (self.store.root/'.student-workflows/configuration/current.json').exists():return self._launch_profile
        from dataclasses import replace
        from .configuration import ConfigStore
        config=ConfigStore(self.store.root/'.student-workflows').read()
        return replace(self._launch_profile,note_type=config.note_type,tag_root=config.tag_root)

    def close(self):
        self.jobs.close()
