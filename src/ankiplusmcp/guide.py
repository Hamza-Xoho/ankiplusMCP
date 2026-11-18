"""Personalised beginner instructions, generated only from supplied verified capabilities."""
import hashlib
import json
from pathlib import Path

from filelock import FileLock

from cards.common.files import atomic_write
from .configuration import UserConfig
from .models import Model
from .runs import _publish
from .store import DomainError

START = '<!-- user-notes:start -->'
END = '<!-- user-notes:end -->'


class VerifiedCapabilities(Model):
    anki_connection: bool = False
    interactive_review: bool = False
    independent_quality_review: bool = False
    source_evidence: bool = False
    history: bool = False


def _inline(value):
    value = str(value).replace('\n', ' ').replace('\r', ' ')
    fence = '`'
    while fence in value:
        fence += '`'
    return fence + ' ' + value + ' ' + fence


def _parts(text):
    if text.count(START) != 1 or text.count(END) != 1:
        raise DomainError('GUIDE', 'Guide was edited outside the recognised notes section; preserve it before regenerating.')
    before, rest = text.split(START)
    notes, after = rest.split(END)
    return before + START + '\n' + END + after, notes


def _sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Guide:
    @staticmethod
    def render(config: UserConfig, capabilities: VerifiedCapabilities) -> str:
        config = UserConfig.model_validate(config)
        capabilities = VerifiedCapabilities.model_validate(capabilities)
        ready = all(capabilities.model_dump().values())
        sources = ', '.join(config.source_materials) or 'the materials you choose for each session'
        decks = ', '.join(config.selected_decks) or 'your own cards; no premade deck is required'
        prompt = 'Make cards from this material, checking my existing cards first.'
        kinds = sources.casefold()
        if 'textbook' in kinds or 'chapter' in kinds:
            prompt = 'Make cards for chapters 2 and 3 of this textbook, checking my existing cards first.'
        elif 'lecture' in kinds or 'slide' in kinds:
            prompt = 'Make cards from this lecture PDF, checking my existing cards first.'
        review = ('Your draft review is on. Read the proposed card text, compare its source passage, and keep, edit or exclude it before approving changes.'
                  if config.review_mode == 'manual' else
                  'Your draft review is off for automatic processing. You can still say “Show me the drafts before applying changes for this run.” Existing quality checks still apply.')
        if config.uncertain_match == 'pending':
            uncertainty = 'Uncertain matches wait for your decision while unrelated work continues.'
        elif config.uncertain_match == 'reuse':
            uncertainty = 'For uncertain matches in automatic mode, your saved preference favours reusing the selected existing cards.'
        else:
            uncertainty = 'For uncertain matches in automatic mode, your saved preference favours proposing a new card; this can increase duplication.'
        status = ('Your verified setup is ready for this workflow.' if ready else
                  'Setup still needs verification. Finish setup before applying changes; this guide does not establish that missing connections or review features work.')
        evidence = ('Use the source reference to check the exact passage behind a card. OCR-read text is labelled because recognition can make mistakes.'
                    if capabilities.source_evidence else 'Source-reference support still needs verification; do not assume a displayed citation has been checked.')
        return f'''# Start here — AnkiPlus

{status}

## 1. Your AnkiPlus setup

Your materials: {_inline(sources)}.
Your relevant decks: {_inline(decks)}.

AnkiPlus checks existing cards before creating gaps, so you do not study the same idea twice. You do not need a premade deck to start; your own cards become part of future coverage checks.

## 2. Make your first cards

First learn the material well enough to understand it. Make the file available on your computer, then tell Claude which file and chapters or pages to use. A whole textbook is not automatically the right scope for one run.

Try this request:

> {prompt}

Why: the source and selection tell AnkiPlus what to cover. Its card-design rules combine and select material rather than making one card for every sentence.

## 3. Check what AnkiPlus proposes

{review}

Existing suitable cards can be left unchanged or proposed for unsuspension. “Unsuspend” means making an existing paused card available for Anki reviews. Editing a new draft does not authorise modifying a premade note.

{evidence}

{uncertainty} A disagreement between the source and an existing card always needs resolution.

Why: review lets you check what matches your needs before it changes Anki. Your corrections affect this run unless you explicitly save a lasting preference. Changed drafts go through the relevant quality checks again.

## 4. What happens after approval

Keep Anki open and connected when applying changes. Only confirmed results should be described as completed. If a run stops halfway through, ask to resume that run and reconcile its recorded results before retrying writes.

Why: blindly repeating an interrupted write can create duplicates. A note may produce several Anki review cards; note counts and unsuspended-card counts are different. Sync Anki after confirmed changes if you use it on other devices.

## 5. Everyday requests

- “Use only these pages for this run.”
- “Show me the drafts before applying changes.”
- “Keep that existing card and exclude this new draft.”
- “Resume the interrupted run and check what already completed.”
- “Show me the proposed preference changes before saving them.”

Why: these requests change source scope, selection or processing without making you manage internal identifiers or files.

## 6. Find your files and history

Your AnkiPlus folder is {_inline(config.data_root)}.
Run records are in {_inline(Path(config.data_root) / 'runs')}.
This guide is {_inline(Path(config.data_root) / 'Start here — AnkiPlus.md')}.

History records sources, proposals, decisions and operation outcomes. It is separate from the review interface. Caller-reported success and independently checked results must remain distinguishable.

Why: the records help you inspect what happened, find related cards and recover from an interruption. Keep this folder when reinstalling AnkiPlus.

## 7. Change your setup or get help

Ask Claude to show a preference change before saving it. You can change your materials, relevant decks or review preference without repeating the whole interview. Saved changes apply to later decisions; earlier run records stay intact.

If a file is unavailable, make it available offline. If a connection or quality check fails, finish that setup step before applying cards. Do not work around a refusal by repeating writes. Tell Claude what you wanted and the error you saw; internal troubleshooting is its job.

Why: explicit saved choices keep one-off edits from silently changing how future runs behave.

### Your notes

Write personal reminders between the markers below. Regeneration preserves those notes. If you edit other generated sections, AnkiPlus will preserve your file and ask you to resolve those edits before replacing them.

{START}
{END}
'''

    @staticmethod
    def write(config: UserConfig, capabilities: VerifiedCapabilities) -> Path:
        root = Path(config.data_root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        target = root / 'Start here — AnkiPlus.md'
        state_path = root / '.ankiplus-guide.json'
        with FileLock(root / '.guide.lock', timeout=5):
            if target.is_symlink() or state_path.is_symlink():
                raise DomainError('GUIDE', 'Guide files cannot be symbolic links.')
            state = json.loads(state_path.read_bytes()) if state_path.exists() else {'schema_version': 1, 'known_generated_hashes': []}
            if state.get('schema_version') != 1:
                raise DomainError('GUIDE', 'Unknown guide metadata version; preserve it for recovery.')
            notes = '\n'
            if target.exists():
                old, notes = _parts(target.read_text(encoding='utf-8'))
                if _sha(old) not in state['known_generated_hashes']:
                    raise DomainError('GUIDE', 'Generated guide was edited; your document was preserved.')
            generated = Guide.render(config, capabilities)
            normalized, _ = _parts(generated)
            known = list(dict.fromkeys([*state['known_generated_hashes'], _sha(normalized)]))
            # Preserve old hashes too: interruption before replacing the document
            # leaves the previous generated version recoverable on the next run.
            _publish(state_path, {'schema_version': 1, 'known_generated_hashes': known})
            content = generated.replace(START + '\n' + END, START + notes + END)
            atomic_write(target, content)
        return target
