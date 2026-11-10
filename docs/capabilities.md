# Capability mapping

AnkiPlus tools operate independently; these mappings do not prescribe a workflow.

| Existing capability | MCP exposure |
| --- | --- |
| State init/get/resume | create_workspace, list_workspaces, get_workspace; explicit IDs/revisions replace .current |
| State set/phase/next | Internal prerequisites and tool errors; arbitrary legacy phase advancement is intentionally not exposed |
| State record-write/report | record_external_results, get_report; caller evidence is explicitly labelled |
| cards build | Intentionally not exposed: model chooses the individual operations |
| cards extract | extract_source with optional slide ranges; includes objectives/map/summary and figure OCR |
| cards source --slides/--all/--grep | read_source, search_source with pagination |
| cards source --page-image/--figure | get_page_image, get_figure, get_image |
| cards target / deck_name.py | resolve_target, explicit course/number/title/subject/system, supplied existing decks; legacy naming option |
| extract_figures.py | export_figures with pages/all, zoom, min_frac and whole_page |
| ocr_regions.py | import_image, ocr_image with confidence/length/padding/grouping, returned regions; get_image and build_occlusion previews |
| build_occlusion.py / cards figures | build_occlusion with regions/keep/one/all, repeated-label groups, media and preview; save_cards is explicit |
| render_cards.py / cards render | render_cards, supplied model templates/CSS or Anki HTML, selected IDs, per_sheet, contact sheets; get_image |
| Legacy desktop/light renderer options | render_cards desktop_sample adds 1024px front samples; light adds phone samples without night-mode classes. Standard contact sheets use 390px phone previews. |
| cards check | check_cards; technical rules independent of lecture mode; optional house_style and coverage |
| cards packets | prepare_review with content or visual scope; no automatic reviewer spawning |
| cards apply | submit_review typed findings, apply_changes preview/apply with revision checks |
| cards gate | Existing CLI unchanged; new toolkit reports validation/review evidence without manufacturing a legacy gate pass |
| cards write | prepare_write; create batches, updates, imports, media and suspension intentions; no collection operations |
| cards meter | measure_usage on an explicitly supplied allowed Claude Code transcript; no host-history discovery |
| Manual draft/report file creation | save_cards, save_omissions, submit_review and record_external_results |

Collection search, note retrieval, media storage in Anki, additions, updates and
suspension/unsuspension remain in the separately configured official Anki MCP.
A request needing only those operations need not call AnkiPlus.

Scope limits: local stdio only, at most 500 source pages and 500 cards per workspace,
64 MiB input files, 20 million decoded image pixels. Long native operations cancel
at safe boundaries. Remote HTTP/authentication and legacy-build migration are
not included. A failed/cancelled job may retain cache files, but is never reported
as completed and does not mark partially generated previews current.
