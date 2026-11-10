<!-- Updated 2026-11-02 to match SKILL.md: bold outside cloze braces, sparing underlines, Extra/citation format. SKILL.md still wins on any conflict. -->
# Card quality — AnKing-style, with worked rewrites

Read this before authoring the first batch in a session. It is the difference
between cards that feel like a well-made shared deck and cards that feel
machine-written.

The conventions below were taken from real AnKing notes, not from memory of
what AnKing "probably" does. The example cards are original — written for this
file — so nothing here is copied from the AnKing deck itself.

---

## 1. The house style

**Cloze is the default for everything textual.** One sentence, one
relationship, with enough visible context that exactly one answer fits. Basic
is the rare exception (see §4). Labelled figures are Image Occlusion.

**Formatting carries meaning — use it the same way every time.** Fields are
HTML, so write the tags directly:

| Mark | Used for | Example |
|---|---|---|
| `<b>bold</b>` | The main subject: the named drug, disease, structure, cell or enzyme. **Outside** the cloze braces: `<b>{{c1::x}}</b>` | `<b>Thiazide diuretics</b>` |
| `<u>underline</u>` | At most one or two per note: the qualifier that flips the meaning if misread. Never filler words | `<u>not</u>`, `<u>only</u>`, `<u>most common</u>` |
| `<i>italic</i>` | Emphasis the source itself gives (*directly*, *only*, *class*) | `acts <i>directly</i> on` |
| `<sub>`/`<sup>` | Chemistry and units — never "K+" or "CO2" | `K<sup>+</sup>`, `HCO<sub>3</sub><sup>−</sup>` |

**Two or three clozes per note is the norm.** Each distinct number is one card.

```
<b>Thiazide diuretics</b> {{c3::increase::increase/decrease}} <b>{{c1::calcium}}</b> reabsorption
in the {{c2::distal convoluted tubule::location}}
```

**Blanks that together form one answer share a number.** They hide and reveal
as a unit:

```
Severe <b>vomiting</b> causes <b>{{c1::hypokalaemic}}</b> <b>{{c1::metabolic alkalosis}}</b>
```

**Cloze both sides of a relationship on one note** instead of making a
reversed card. The drug and its effect, the structure and its function:

```
<b>{{c2::Ondansetron}}</b> is a(n) <b>{{c1::5-HT<sub>3</sub> antagonist::drug class}}</b>
used for {{c3::chemotherapy-induced nausea}}
```

c1 asks the class from the drug; c2 asks the drug from the class; c3 asks the use.

**Hints name the category, never the answer.** Add `::hint` only when the blank
could reasonably be answered at the wrong level — a location when you want a
mechanism, a class when you want a drug:
`<b>{{c1::parotid::gland}}</b>`, `<b>{{c2::proximal tubule::location}}</b>`.
A hint that narrows it to one word ("starts with P") is leakage.

**`a(n)` before a blank**, so the article doesn't give away the first letter.

**Context stays visible, in the source's words.** The patient group, the
"e.g.", the condition under which the fact holds — these are what make the
card unambiguous, and they are what the exam question will show you.

**Numbers go in with their units, in the source's units:**
`Normal serum <b>K<sup>+</sup></b> is {{c1::3.5–5.0 mmol/L}}`.

**Extra** (the `Extra` field of ColdRecall Cloze). It shows after you answer and is
never tested. Put there, in this order and only if useful:

1. the one-line *why* (the mechanism, in a phrase, not a paragraph),
2. a mnemonic or a contrasting look-alike ("vs. loop diuretics: ↓ Ca²⁺"),
3. if the understanding lives in the vault, the note's name — `Vault: Renal handling of calcium`,
4. where it came from, last, in its own block — `<div class="src">L3, slide 14</div>` — so a doubtful card can be checked.

Lines are joined with `<br>`, never raw newlines; at most three lines.

Nothing on the front should depend on Back Extra to be answerable.

---

## 2. The failure patterns — and the fix for each

When a card feels "AI-generated", it matches one of these. Check every draft
against the list.

### Paraphrasing away the source's language

The lecturer's exact term is what the exam uses and what you recognise under
pressure.

- ✗ `A pulse with a rapid upstroke and sudden collapse is seen in {{c1::aortic regurgitation}}`
- ✓ `<b>Aortic regurgitation</b> classically produces a <b>{{c1::water-hammer (Corrigan's)}}</b> pulse`

### The list card

- ✗ Front: *List the four cardinal signs of inflammation* / Back: *rubor, calor, tumor, dolor*
- ✗ `The cardinal signs are {{c1::rubor, calor, tumor and dolor}}` — a list card wearing a cloze costume
- ✓ `The cardinal signs of <b>inflammation</b> are {{c1::rubor}}, {{c2::calor}}, {{c3::tumor}} and {{c4::dolor}}`

Four cards, each failing on its own. A comma inside a deletion is almost always
this mistake.

### Answer leakage through the count

- ✗ `Name the 3 branches of the aortic arch`
- ✓ `From proximal to distal, the <b>aortic arch</b> gives off the {{c1::brachiocephalic trunk}}, the {{c2::left common carotid}} and the {{c3::left subclavian}} arteries`

The exam won't tell you when to stop. The order is the source's order.

### Ambiguous blank

- ✗ `{{c1::Lysis}} means breakdown` — or worse, `-lysis → ?` with no frame
- ✓ `The suffix <b>{{c2::-lysis}}</b> means {{c1::breakdown / destruction}}`

If two answers are defensible, add the discriminating context or a category hint.

### Two facts in one blank

- ✗ `Hyperkalaemia is {{c1::a raised serum K⁺, most often caused by renal failure and ACE inhibitors}}`
- ✓ Two notes: the threshold (one cloze, with units) and the causes (one cloze per cause).

### Clozing a word that carries no information

- ✗ `Surfactant is produced {{c1::mainly}} by type II pneumocytes`
- ✓ `Surfactant is produced mainly by <b>{{c1::type II pneumocytes}}</b>`

If deleting the word doesn't change what a student must know, it isn't a blank.

### Deleting a whole clause

- ✗ `Protein kinase A {{c1::phosphorylates target proteins on serine and threonine residues after activation by cAMP}}`
- ✓ `<b>Protein kinase A</b> is activated by <b>{{c1::cAMP}}</b> and phosphorylates {{c2::serine}} / {{c2::threonine}} residues`

Where the slide highlights an operative word (*Protect*, *Regulate*), cloze
exactly that word.

### Multiple-choice scaffolding

Anki trains production, not recognition.

- ✗ `Which of the following is an ACE inhibitor? a) atenolol b) lisinopril c) …`
- ✓ `Drugs ending in <b>{{c2::-pril}}</b> are <b>{{c1::ACE inhibitors::drug class}}</b>`

An MCQ in the slides becomes a production card that keeps its clinical framing
and drops the options.

### Hedge padding

- ✗ `It is important to note that, generally speaking, the liver is the primary site of gluconeogenesis`
- ✓ `The primary site of <b>gluconeogenesis</b> is the <b>{{c1::liver}}</b>`

### Losing the source's hedge

The opposite failure: *"associated with"* silently becoming *"causes"*, or
*"typically"* disappearing. Keep the source's strength of claim, underlined:
`<b>Smoking</b> is <u>associated with</u> <b>{{c1::squamous cell}}</b> carcinoma of the lung`.

### Compare/contrast as one card

- ✗ `What are the differences between type 1 and type 2 diabetes?`
- ✓ One note per axis — onset, mechanism, body habitus, insulin dependence —
  each sentence naming both sides: `<b>Type 1</b> diabetes is due to {{c1::autoimmune β-cell destruction}}, <b>type 2</b> to {{c2::insulin resistance}}`

### A mechanism turned into an essay card

- ✗ `Explain how a buffer resists a change in pH` → paragraph answer
- ✓ The explanation belongs in the vault as a concept note. The exam-facing
  *facts* that fall out of it can be clozes: `The main extracellular <b>buffer</b> is <b>{{c1::bicarbonate}}</b>`.

---

## 3. Enumerations and syndromes

For a set the source presents as a unit (a triad, a named sequence), make two
notes:

```
Forward:  <b>Horner syndrome</b> = {{c1::ptosis}}, {{c2::miosis}} and {{c3::anhidrosis}}
Reverse:  Unilateral <b>ptosis</b>, <b>miosis</b> and <b>anhidrosis</b> → <b>{{c1::Horner syndrome}}</b>
```

The forward note tests each member; the reverse note tests recognition of the
whole pattern, which is how a vignette presents it.

For a long list (12 cranial nerves), one deletion per member in source order
is fine even past the ~5-per-note cap — the cap is for sentences, not for
enumerations the source itself lists.

---

## 4. When Basic is right (rarely)

- The source poses a genuine question with a short answer that won't sit in a
  sentence — an image with "Identify:" and the answer. Even then, AnKing writes
  it as a cloze: `Identify: <img …> {{c1::S3 gallop}}`.
- A pure synonym pair the exam asks in both directions (`anterior ↔ ventral`):
  `Basic (and reversed card)`. For almost everything else, clozing both sides
  of one sentence (§1) does the same job with one note.

---

## 5. Interference

Near-identical cards compete and produce *"I know it's one of these two"*.
Keep the discriminating word visible and underlined on each, and don't write
them into the same batch if they can be split across sessions:

```
<b>Loop diuretics</b> {{c1::<u>increase</u>}} urinary <b>calcium</b> excretion
<b>Thiazides</b> {{c1::<u>decrease</u>}} urinary <b>calcium</b> excretion
```

Here the discriminator *is* the direction, so the direction is the blank.
Better still, one compare note that forces the contrast every time:
`<b>Loops</b> {{c1::lose}} calcium; <b>thiazides</b> {{c2::retain}} it`.

---

## 6. Final check, per note

- [ ] Could a classmate who knows the fact answer it without guessing what I meant?
- [ ] Is every blank one item — no commas, no clauses?
- [ ] Does the article, count, or grammar leak the answer?
- [ ] Are the named things bold and the direction words underlined?
- [ ] Is the wording the source's, including its hedges?
- [ ] Is Back Extra short, and is the front answerable without it?
- [ ] Tags: source, tier, and subject/system where they apply?
