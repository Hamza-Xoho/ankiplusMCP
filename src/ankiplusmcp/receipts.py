"""Read cumulative caller evidence without depending on a complete projection."""
import json

from .store import DomainError


def read_receipts(directory, read):
    """Merge legacy projection and published journal entries without changing either.

    Callers supply their boundary-checked JSON reader. No readback from Anki or
    independent verification is implied by recovery of a caller's saved receipt.
    """
    projection = directory / 'external-results.json'
    paths = ([projection] if projection.exists() else [])
    paths += sorted((directory / 'result-events').glob('*.json'))
    if not paths:
        return None
    combined, seen = [], set()
    metadata = {'evidence_origin': 'caller_supplied', 'independently_verified': False}
    for path in paths:
        record = read(path)
        if not isinstance(record, dict) or not isinstance(record.get('results'), list):
            raise DomainError('RESULT_CORRUPT', 'Invalid receipt record; preserve it for recovery.')
        if path == projection:
            # Legacy import fingerprints include this exact wrapper shape.
            metadata = record
        for result in record['results']:
            if not isinstance(result, dict):
                raise DomainError('RESULT_CORRUPT', 'Invalid receipt result; preserve it for recovery.')
            key = json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False)
            if key not in seen:
                seen.add(key)
                combined.append(result)
    return {**metadata, 'results': combined}
