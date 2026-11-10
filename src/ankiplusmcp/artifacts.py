"""Bounded artifact access, never an arbitrary host-file browser."""
import io
from PIL import Image
from .store import DomainError, MAX_FILE

class Artifacts:
    def artifacts(self, workspace, offset=0, limit=50):
        root = self.store.directory(workspace)
        files = sorted(str(p.relative_to(root)) for p in root.rglob('*')
                       if p.is_file() and not p.is_symlink() and not any(x.startswith('.') for x in p.relative_to(root).parts))
        return {'artifacts':files[offset:offset+limit], 'total':len(files), 'next_offset':offset+limit if offset+limit<len(files) else None}

    def read_artifact(self, workspace, artifact, offset=0, limit=12000):
        path = self.store.path(workspace, artifact)
        if not path.is_file() or path.stat().st_size > MAX_FILE or path.suffix.lower() not in ('.json','.jsonl','.txt','.md','.html','.css','.csv','.toml'):
            raise DomainError('ARTIFACT', 'Artifact missing, oversized, or not text.', 'Use list_artifacts or get_image.')
        text = path.read_text(encoding='utf-8')
        return {'artifact':artifact, 'text':text[offset:offset+limit], 'total_chars':len(text),
                'next_offset':offset+limit if offset+limit<len(text) else None}

    def image_bytes(self, workspace, artifact):
        path = self.store.path(workspace, artifact)
        if not path.is_file() or path.stat().st_size > MAX_FILE:
            raise DomainError('IMAGE', 'Image missing or oversized.')
        try:
            with Image.open(path) as im:
                if im.width*im.height > 20_000_000: raise ValueError('pixel limit')
                im.thumbnail((1600,1600))
                out = io.BytesIO(); im.convert('RGB').save(out, 'PNG')
                return out.getvalue()
        except Exception as exc:
            raise DomainError('IMAGE', 'Not a readable image under 20 million pixels.') from exc
