# Completed-product engineering review and material fix pass

Review candidate: primary7523cd0f0533cf48e1c9aeb2b0a63994edcb26df,
companionacdff9329f38c856edeabd6ae572ebe4a1f8dec0. Review covered the whole
primary branch from b0f4233 and companion branch from278f5e9, with the approved
spec/plans, source and connected tests. Reviewer: fresh native
`/root/completed_product_engineering_review`, gpt-6.1-sol/high. Disposition:
**With fixes**. This was the single final engineering review of the completed new
implementation; historical adapter reviews do not stand in for it. Root alone
implemented one material fix pass. There is no engineering re-review.

| Finding / root grade | Reproduction and final implementation |
| --- | --- |
| P1 contradiction cleared by citation edit | `test_contradiction_survives_a_shorter_valid_citation` failed first. Scope is concept/source version, independent of quote/page. Old events fold original refs without rewriting history; exact token resolution remains required. |
| P1 CSS media missing from guard/render | Companion six literal/escaped/inline/style/link cases failed first; primary render refusals failed first. CSS resource dependencies explicitly refuse before dispatchable state/render. They cannot silently become a missing image. |
| P1 update quality uses draft tags | `test_update_quality_renders_retained_actual_tags` failed first. Captured retained tags/model and requested full fields produce the reviewed post-update content, including `{{Tags}}`. A related failed-first `{{Deck}}` case now explicitly refuses unsupported metadata instead of silently rendering it empty. |
| P1 existing native IO rendered as cloze | `test_existing_native_io_quality_masks_front` failed first. Actual captured model semantics select native IO masking; pixel assertion verifies hidden region. Unsupported native variants refuse. A600px source regression also failed first against the new layout bound; inert native mask images now fit the phone viewport while retaining source bytes/mask resolution. |
| P1 saved ordinary profile blocks native IO/mixed runs | `test_native_io_create_allowed_with_normal_saved_profile` failed first. Canonical native IO is an explicit supported special case, actual fields/model still validated. Installed real-Anki acceptance additionally exercises a mixed Basic/native IO run. |
| P1 persisted launcher flags restore revoked folders | `test_serve_restart_cannot_restore_confirmed_revoked_roots` failed first through the actual serve entry point. Confirmed preferences govern restart; historical flags/env seed only unconfirmed setup. |
| P2 already-target card states counted as writes | Active-before-stage and mixed selection regressions failed first. Staging partitions exact unchanged/changed requests; readback independently recognizes desired state before any send. Counts include only confirmed changed card IDs. Tier child selection uses verified generated identities. |
| P2 quality expansion/render bounds applied late | 1001-deletion expansion failed first; packet/file count now preflight before allocation. Layout test failed first on missing bound interface; huge CSS height now refuses before screenshot allocation. Embedded-image dimension tests failed first, including whitespace, template sources and independent field parsing; image headers and expanded mask pixels are checked before decode/masks/browser. |

All engineering findings were accepted as executable defects after source/repro
verification. None was waived as a Mac gate. Regression filenames above live in
`tests/mcp/test_final_review_fixes.py`; companion cases are in
`tests/unit/test_conditional_student_operation.py`. Raw RED/GREEN/full outputs are
retained ignored under `.artifacts/` in each repository. Final source revisions,+test counts and runtime image evidence are in [Mac packet](macos-acceptance.md).

The reviewer declined actual Mac embedding/lifecycle/private production model
fidelity, actual prescribed reviewer runtime controls, semantic source-to-card
quality, dishonest trusted operator/stdio host evidence, unrelated platforms,
publication/deployment, and forced interruption of native work. Ruling: these
are the documented acceptance/trust/scope boundaries. Cooperative cancellation
is implemented and tested; force-kill behavior is not promised. This ruling does
not defer any of the eight executable defects.

The separate impeccable UI finish reviewer, fresh native
`/root/review_surface_finish` (gpt-6.1-terra/high), found three material issues:
unsaved field loss on existing-note switch, absent run identity, missing
PRODUCT.md. Root fixed them with a failed-first actual SDK browser regression,
responsive captures and restored product context. The same UI reviewer scored
only these listed fixes: **all resolved; ship for the scored fixes**. This is not
a second engineering review or independent Anki card-quality/Mac acceptance.
Full UI evidence remains in the preserved production integration ledger.

Final full regression also reproduced existing coverage retry contention: two
identical concurrent batches raced on the nonblocking configuration lock. A new
deterministic held-read regression failed first, then a bounded separate per-run
coverage lock made the retry reuse the committed winner before configuration
read. Focused coverage/coordinator/workflow concurrency32passed, including the
existing requirement that configuration reads remain BUSY during dispatch. This
is a root regression repair in the same material fix pass, not a new review.
