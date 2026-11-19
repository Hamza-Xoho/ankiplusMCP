"""Rebuildable local search projection. Immutable run files remain authoritative."""
import sqlite3
from contextlib import closing

from pydantic import Field

from .models import Model, Positive
from .run_models import RunSnapshot
from .runs import RunStore
from .store import DomainError


class RunQuery(Model):
    source_hash: str | None = None
    run_id: str | None = None
    note_id: Positive | None = None
    card_id: Positive | None = None
    stage: str | None = None
    outcome: str | None = None
    text: str | None = Field(default=None, max_length=200)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class RunPage(Model):
    runs: list[RunSnapshot]
    next_offset: int | None = None
    errors: dict[str, str] = Field(default_factory=dict)


class RunIndex:
    def __init__(self, store: RunStore):
        self.store = store
        self.path = store.root / 'run-index.sqlite3'

    def _connect(self):
        if self.path.is_symlink():
            raise DomainError('RUN', 'Index cannot be a symbolic link.')
        db = sqlite3.connect(self.path)
        try:
            # Serialize schema inspection and migration across connections/processes.
            # DDL is transactional only when a transaction is explicitly begun.
            with db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, source_hash TEXT, label TEXT, updated TEXT, sequence INTEGER, snapshot TEXT NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS lookups (run_id TEXT, kind TEXT, value TEXT, PRIMARY KEY(run_id,kind,value))')
                db.execute('CREATE INDEX IF NOT EXISTS runs_source ON runs(source_hash)')
                db.execute('CREATE INDEX IF NOT EXISTS runs_recency ON runs(updated DESC,id)')
                db.execute('CREATE INDEX IF NOT EXISTS lookup_value ON lookups(kind,value,run_id)')
                db.execute('CREATE TABLE IF NOT EXISTS index_errors (id TEXT PRIMARY KEY, code TEXT)')
                db.execute('CREATE TABLE IF NOT EXISTS journal_watermarks (id TEXT PRIMARY KEY, sequence INTEGER NOT NULL)')
                if 'journal_token' not in {row[1] for row in db.execute('PRAGMA table_info(runs)')}:
                    db.execute('ALTER TABLE runs ADD COLUMN journal_token TEXT')
        except BaseException:
            db.close()
            raise
        return db

    def _sync(self, db, *, reset=False):
        db.execute('BEGIN IMMEDIATE')
        if reset:
            db.execute('DELETE FROM lookups')
            db.execute('DELETE FROM runs')
            db.execute('DELETE FROM index_errors')
            db.execute('DELETE FROM journal_watermarks')
        known=dict(db.execute('SELECT id,journal_token FROM runs'))
        db.execute('INSERT OR IGNORE INTO journal_watermarks (id,sequence) SELECT id,sequence FROM runs')
        sequences=dict(db.execute('SELECT id,sequence FROM journal_watermarks'))
        catalog=self.store.catalog(known)
        truncated={item.snapshot.id for item in catalog.changed if len(item.snapshot.events)<sequences.get(item.snapshot.id,0)}
        catalog.errors.update({ident:'RUN_CORRUPT' for ident in truncated})
        catalog.changed=[item for item in catalog.changed if item.snapshot.id not in truncated]
        present=set(catalog.unchanged_ids) | {item.snapshot.id for item in catalog.changed}
        for ident in set(known)-present:
            db.execute('DELETE FROM lookups WHERE run_id=?',(ident,))
            db.execute('DELETE FROM runs WHERE id=?',(ident,))
        db.execute('DELETE FROM index_errors')
        db.executemany('INSERT INTO index_errors (id,code) VALUES (?,?)',sorted(catalog.errors.items()))
        for item in catalog.changed:
            run=item.snapshot
            db.execute('INSERT OR REPLACE INTO journal_watermarks (id,sequence) VALUES (?,?)',(run.id,len(run.events)))
            db.execute('INSERT OR REPLACE INTO runs (id,source_hash,label,updated,sequence,snapshot,journal_token) VALUES (?,?,?,?,?,?,?)',
                (run.id,run.selection.source_hash,run.selection.label.casefold(),run.events[-1].timestamp,
                 run.events[-1].sequence,run.model_dump_json(),item.token))
            db.execute('DELETE FROM lookups WHERE run_id=?',(run.id,))
            values = set()
            for event in run.events:
                for key in ('note_ids', 'card_ids'):
                    for value in event.payload.get(key, []):
                        if type(value) is int and value > 0:
                            values.add((run.id, key, str(value)))
                for key in ('stage', 'outcome'):
                    if isinstance(event.payload.get(key), str):
                        values.add((run.id, key, event.payload[key]))
            db.executemany('INSERT INTO lookups VALUES (?,?,?)', sorted(values))
        return len(present)

    def rebuild(self) -> int:
        with closing(self._connect()) as db, db:
            return self._sync(db, reset=True)

    def search(self, query: RunQuery) -> RunPage:
        query = RunQuery.model_validate(query)
        clauses, params = [], []
        for key in ('source_hash', 'run_id'):
            value = getattr(query, key)
            if value is not None:
                clauses.append(('id' if key == 'run_id' else key) + '=?')
                params.append(value)
        if query.text:
            clauses.append('instr(label,?)>0')
            params.append(query.text.casefold())
        for key, kind in [('note_id', 'note_ids'), ('card_id', 'card_ids'), ('stage', 'stage'), ('outcome', 'outcome')]:
            value = getattr(query, key)
            if value is not None:
                clauses.append('EXISTS (SELECT 1 FROM lookups WHERE run_id=runs.id AND kind=? AND value=?)')
                params.extend((kind, str(value)))
        sql = 'SELECT snapshot FROM runs'
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY updated DESC,id LIMIT ? OFFSET ?'
        with closing(self._connect()) as db, db:
            self._sync(db)
            rows = db.execute(sql, [*params, query.limit + 1, query.offset]).fetchall()
            errors = dict(db.execute('SELECT id,code FROM index_errors ORDER BY id LIMIT 100'))
        return RunPage(runs=[RunSnapshot.model_validate_json(row[0]) for row in rows[:query.limit]],
                       next_offset=query.offset + query.limit if len(rows) > query.limit else None,
                       errors=errors)
