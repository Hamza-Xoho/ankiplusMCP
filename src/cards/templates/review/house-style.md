## House style — AnKing

Full rules and worked ✗/✓ rewrites: `references/card-quality.md`. The core,
including the conventions from the AnKing maintainers' submission guidelines:

**Content**

- **Cloze is the default for everything textual.** One sentence, one
  relationship, enough visible context that exactly one answer fits.
- **Two or three clozes per note**; blanks that form one answer **share a
  number**; cap ~5 per note except a genuine enumeration.
- **Cloze both sides of a relationship** (drug as c2, class as c1) instead of
  making reversed cards.
- **One item per deletion** — a comma inside a blank is a list card in disguise.
  Never blank a filler word; blank the operative word.
- **`a(n)` before a blank.** No counts that tell you when to stop. Grammar
  (singular/plural, verb agreement) must not give the answer away. Better
  still, rephrase so no article sits before the blank ("contains the
  {{c2::indole}} ring"); students read `a(n)` as clunky.
- **Context words stay outside the blank:** "bacterial {{c1::peptidoglycan}}
  cell walls", not "{{c1::bacterial peptidoglycan}} cell walls".
- **Members of a scheme-specific group** (aliphatic, aromatic, basic…): if
  another amino acid, drug or structure would also fit the blank in a
  different scheme, state the exception in the visible text: "(histidine
  counts as heterocyclic)". This was the commonest blocker in testing.
- **Sibling clozes must not answer each other:** "aspartic acid … {{c3::acidic}}"
  is answered by the visible name. Blank what the names don't give away.
- **The source's terms and the source's hedges.** "Associated with" never
  becomes "causes". Use the lecturer's vocabulary, but shape it into a card
  sentence — don't paste whole slide sentences or paragraphs verbatim.

**Hints**

- **Hints name the category, never the answer:** `{{c1::parotid::gland}}`.
- **Direction blanks get the binary hint, in this order:**
  `{{c1::increases::increases/decreases}}`, `{{c1::high::high/low}}` — unless
  the answer is obvious from context.
- Use the **same hint word for the same category** across the deck (always
  `location`, never `location` on one note and `site` on the next), but
  don't reuse one hint on sister notes whose answers differ and could swap
  (`[structural group]` on aliphatic, branched-chain and aromatic made each
  accept the others). Make it specific: `[chain shape]`, `[ring type]`.
- **A hint must not describe the answer uniquely.** `{{c1::arginine::guanidino
  side chain}}` turns "which amino acids are basic" into "which has a
  guanidino group", which is a leak.
- **Keep hints short** (about 20 characters). A long hint such as
  `[glucogenic/ketogenic/both]` overflows a phone screen; use
  `[gluco/keto/both]`.

**Formatting** — the eye goes to bold first, then underline, then italics

- **`<b>` the main subject** — the named thing the sentence is about (drug,
  disease, structure, cell, enzyme). Don't bold everything that is a noun.
- **Bold goes outside the cloze braces:** `<b>{{c1::tryptophan}}</b>`, never
  `{{c1::<b>tryptophan</b>}}`. In AnKing-styled note types bold has its own
  colour, and inside the braces it hides the answer colour, so the revealed
  answer looks like every other bold word. (The ColdRecall note type guards
  against this too, but write it correctly anyway.)
- **`<u>` sparingly** — at most one or two per note (the student reviewer
  treats every underline as one more AMBOSS look-alike), only a qualifier that
  flips the meaning if misread (`<u>not</u>`, `<u>only</u>`, `<u>most
  common</u>`) or the source's hedge. **Never filler words** (`and`, `both`,
  `the`, `all`). In Anki, the AMBOSS add-on also underlines medical terms in
  teal, so underlines pile up quickly.
- `<i>` for the source's own emphasis. `<sub>`/`<sup>` for chemistry and units
  (`K<sup>+</sup>`, `HCO<sub>3</sub><sup>−</sup>`), never "K+" or "CO2".
- **Disease name bold, abbreviation not:** `<b>Acute kidney injury</b> (AKI)`.
- **No full stop at the end of a card.** Capitals only for names and the start
  of a sentence ("type II pneumocytes", not "Type II Pneumocytes").
- Numbers carry their units, in the source's units.
- **Keep things that mustn't break on one line:** wrap formulas, hyphenated
  terms and multi-word answers in `<span class="nw">…</span>`:
  `<span class="nw">(–COOH)</span>`, `<span class="nw">D-alanine</span>`,
  `{{c1::<span class="nw">glutamic acid</span>}}`. Otherwise phones break
  "(– / COOH)" and "D- / alanine" across lines.
- Mnemonics: bold the mnemonic word (`<b>PVT TIM HaLL</b>`). Don't underline
  letters: in testing, underlined letters looked like AMBOSS links.

**Extra** (shown after answering, never needed to answer)

- **At most three lines, about 200 characters.** In this order, only if useful:
  the one-line *why*; a mnemonic or contrasting look-alike; then the citation
  (`L3, slide 14` / `Kaplan Biochemistry, Ch. 1`) and `Vault: <note name>` if
  the understanding lives there. No "clinical pearls" or rules of thumb the
  source didn't give. A second fact is a second card, not more Extra.
- **Lines are separated with `<br>`, never raw newlines.** HTML collapses
  newlines, so `- a\n- b\n\nSource` renders as one run-on paragraph.
- Capitalise each line. Content lines start with `- ` only when there are
  two or more; a single content line has no dash.
- **The citation is its own block, last:** `<div class="src">Kaplan
  Biochemistry, Ch. 1</div>`. Don't put a `<br>` before it. The note type
  sets it smaller and upright, so it never reads as another bullet. An
  Extra with nothing to add is just the citation block.
- No `<i>`: the ColdRecall note type already sets Extra in muted italics.
  Bold only a named thing being contrasted.

**Images**

- Image shown *before* the answer, text answer → reveal the text **above** the
  image. Image is the answer → reveal it below.
- Image only useful *after* answering → it goes in Extra, not a cloze.

**One-by-one** (sequential reveal) only for items recalled **in a fixed order**
— a mnemonic or a sequence (steps of a pathway, order of treatment). Never for
a 2–3 cloze note unless it is a mnemonic, and never for a set whose members
can't be told apart by order.

| Knowledge shape | Note type |
|---|---|
| Anything that sits in a sentence — terms, values, facts, sequences, enumerations, compare/contrast | **ColdRecall Cloze** (fields `Text`, `Extra`) |
| A labelled figure | **Image Occlusion** |
| A synonym pair tested both ways; a question that genuinely won't become a sentence | Basic (and reversed card) / Basic — rare |

**ColdRecall Cloze** is the house note type. It is a lean clone of the AnKing
MCAT note type's look: slate background, green answer, purple bold, teal
underline, and Extra in muted italics under a rule. It adds review-panel fixes:
a phone gutter, a soft highlight behind the revealed answer (so it doesn't
differ from other bold names by colour alone), left-aligned Extra, the `.src`
citation block, and the `.nw` no-wrap class. It has no AnkiHub hooks,
so AnkiHub updates never touch it. If it's missing (new computer, new profile),
create it once from `assets/coldrecall-cloze/` before writing (see **Setting up the note type**). Don't create any other note
types. Don't write into a shared deck's own note types (AnKingOverhaul, AnKing
MCAT and similar), because those belong to that deck. Existing notes on the
plain `Cloze` type stay where they are unless the user moves them (Browse →
Notes → Change Note Type, mapping `Back Extra` → `Extra`).

---
