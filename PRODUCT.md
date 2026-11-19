# AnkiPlus student workflows

Product authority: [approved workflow design](docs/superpowers/specs/2026-11-18-student-workflows-design.md).
Visual direction: [DESIGN.md](DESIGN.md). Connected operations and trust boundaries:
[student workflow](docs/refactor/student-workflow.md).

Students turn their own lecture PDFs, text sections and custom images into
source-linked study cards while checking existing collection coverage first.
They can use premade decks, their own decks, or no premade deck. Source reading
and existing-note modification require explicit choices.

The core journey is resumable setup, bounded source selection, approved-scope
collection search, durable proposals, source-linked review, independent quality
evidence, exact approval, guarded application, per-item verification and permanent
history. Uncertain writes require reconciliation before further work. Existing
notes remain protected unless the student explicitly selects an update.

The review surface serves a careful reading/comparison task. It shows run identity,
source evidence, existing coverage, decisions and unresolved findings before
approval. Controls use native labels, keyboard focus and responsive single-column
reading on narrow screens. Text from sources/cards stays inert. Unsaved edits
must survive until save or explicit reload; reconnect restores saved selections.

Linux acceptance uses disposable synthetic collections and host evidence. It does
not prove Mac host embedding or private collection correctness. Actual prescribed
independent card reviewers, cumulative host controls, Mac lifecycle and explicitly
authorized real collection operations remain acceptance gates. Their absence
cannot produce a quality pass or authorize a write.
