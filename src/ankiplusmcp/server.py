"""Typed stdio facade; guarded student operations use the explicit companion adapter."""
import base64
from functools import wraps
import importlib.metadata
import inspect
import json
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import unquote, urlparse
import anyio
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ImageContent, ToolAnnotations
from pydantic import Field, ValidationError
from cards.common.errors import CardsError
from .models import Card, CardPatch, Region, Finding, ExternalResult
from .evidence import EvidenceRef, EvidenceResolver
from .store import DomainError
from .service import Service
from . import settings, doctor

Workspace = Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')]
Offset = Annotated[int, Field(ge=0)]
Limit = Annotated[int, Field(ge=1,le=100)]
Revision = Annotated[int, Field(ge=0)]
Ids = list[Annotated[str,Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')]] | None

class API:
    def __init__(self, service): self.s=service

    def capabilities(self) -> dict:
        """Inspect supported helpers, installed prerequisites and the separate Anki MCP dependency."""
        dependencies={}
        for name in ('mcp','PyMuPDF','pillow','playwright'):
            try: dependencies[name]=importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError: dependencies[name]=None
        browser=doctor.resolve_browser(self.s.browser)
        return {'server':'ankiplusmcp','version':importlib.metadata.version('ankiplusmcp'),'transport':'stdio',
                'anki_connection':'configured_companion' if self.s.companion_connection else 'separate_host_dependency',
                'anki_operations':self.s.companion_connection is not None,'authorization_required':True,
                'dependencies':dependencies,'tesseract_available':doctor.have('tesseract'),'chromium_available':browser is not None,'browser':browser,
                'guidance_topics':['overview','quality','maintainer','student'],
                'source_roots':[str(p) for p in (self.s.store.source_roots or ())],
                'source_roots_origin':self.s.store.source_roots_origin,
                'profile':{'name':self.s.profile.name,'note_type':self.s.profile.note_type,'tag_root':self.s.profile.tag_root},
                'long_operations':'extract_source, ocr_image and render_cards return jobs; use get_job.',
                'missing_dependency_remedy':doctor.FIXES}

    def _student_config(self):
        return self._coordinator().config

    def get_student_setup(self) -> dict:
        """Resume saved student preferences and show remaining verified setup requirements."""
        from .onboarding import Onboarding
        status=Onboarding(self.s).status()
        value=status.model_dump()
        value['ready_to_apply']=status.onboarding_complete
        return value

    async def advance_student_setup(self, step: Literal['preferences','storage','connection','interactive_review','quality_runtime','guide'], evidence: dict) -> dict:
        """Run a required setup check or validate actual trusted host evidence. Caller completion assertions are refused."""
        from .onboarding import Onboarding
        status=await Onboarding(self.s).advance(step,evidence)
        return {**status.model_dump(),'ready_to_apply':status.onboarding_complete}

    def propose_preferences(self, changes: dict, expected_version: Annotated[int,Field(ge=1)]) -> dict:
        """Show a lasting preference diff without saving it. Run-only choices need no saved change."""
        from .run_preferences import preference_diff
        change=self._student_config().propose(changes,expected_version)
        return {**change.model_dump(),'scope':'future_preferences','diff':preference_diff(change.before.model_dump(),change.after.model_dump(),change.changed_keys)}

    def confirm_preferences(self, change_id: str) -> dict:
        """Explicitly save a shown preference change and refresh the tailored guide, preserving personal notes."""
        from .onboarding import Onboarding
        status=Onboarding(self.s).confirm_choices(change_id)
        config=status.configuration
        self.s.store.set_source_roots([Path(p) for p in config.source_roots],'preferences')
        return {**status.model_dump(),'ready_to_apply':status.onboarding_complete}

    def propose_student_setup(self, choices: dict) -> dict:
        """Show complete setup choices for explicit confirmation, including keeping defaults. No premade deck is required."""
        from .onboarding import Onboarding
        return Onboarding(self.s).propose_choices(choices)

    async def get_collection_choices(self, offset: Offset=0, limit: Limit=20) -> dict:
        """Inspect own or premade decks for setup. Filtered decks are identified; no collection changes."""
        from .run_responses import page
        async with self._coordinator()._connection() as adapter:binding,decks=await adapter.list_decks()
        values=[{**row,'eligible_for_scope':not row['is_filtered']} for row in decks]
        rows,next_offset=page(values,offset,limit)
        return {'binding':binding,'decks':rows,'total':len(values),'next_offset':next_offset,'premade_deck_required':False}

    async def search_collection_coverage(self, query: Annotated[str,Field(min_length=1,max_length=2000)]) -> dict:
        """Search complete bounded note/card coverage from an explicitly configured companion. Never mutates Anki."""
        if self.s.companion_connection is None:
            raise DomainError('UNSUPPORTED','Configure an explicit companion endpoint and intended profile/path first.')
        from .coordinator import scoped_query
        query=scoped_query(query,self._student_config().read())
        async with self.s.companion_connection() as adapter:
            binding=await adapter.collection_identity()
            ids=await adapter.search_notes(query)
            notes=await adapter.read_notes(ids)
            card_ids=[c for n in notes for c in n.card_ids]
            cards=[]
            for offset in range(0,len(card_ids),100):
                cards.extend(await adapter.read_cards(card_ids[offset:offset+100]))
            by_id={c['id']:c for c in cards}
            for note in notes:
                if any(by_id[c]['nid']!=note.note_id or by_id[c]['note_fields']!=note.fields
                        or by_id[c]['sibling_card_ids']!=sorted(note.card_ids) for c in note.card_ids):
                    raise DomainError('CONFLICT','Card ownership changed during coverage search.')
                note.suspended_card_ids=[c for c in note.card_ids if by_id[c]['queue']==-1]
            if await adapter.collection_identity()!=binding:
                raise DomainError('CONFLICT','Companion session changed during coverage search.')
        return {'binding':binding,'query':query,'notes':[n.model_dump() for n in notes],
                'evidence_origin':'companion_readback','semantic_completeness_verified':False}

    def _coordinator(self):
        from .coordinator import Coordinator
        return Coordinator(self.s)

    def start_student_run(self, workspace: Workspace, pages: list[Annotated[int,Field(ge=1)]] | None=None) -> dict:
        """Start a durable run for this source selection, preserving all earlier runs."""
        return self._coordinator().start(workspace,pages).model_dump()

    async def record_run_coverage(self, run_id: str, query: str, decisions: list[dict]) -> dict:
        """Read complete approved-scope collection coverage and retain source-linked decisions durably."""
        result=await self._coordinator().coverage(run_id,query,decisions)
        return {'batch_id':result['batch_id'],'recorded':len(result['decisions']),'query':result['query']}

    async def stage_run(self, run_id: str) -> dict:
        """Capture an immutable exact proposal and its conditional collection preconditions. Does not approve or write."""
        p=await self._coordinator().stage(run_id)
        return {'run_id':run_id,'digest':p.digest,'content_digest':p.content_digest,'operations':len(p.operations),
                'pending':sum(d['disposition']=='pending' for d in p.decisions),'quality_required':bool(p.operations) and len(p.quality)!=2}

    def get_run_proposal(self, run_id: str, offset: Offset=0, limit: Limit=10) -> dict:
        """Read a bounded page of proposed cards, actions, source evidence and unresolved findings."""
        from .review_session import ReviewSession
        from .run_responses import page
        p=self._coordinator()._latest(run_id)
        previews=[]
        for card in p.cards:
            fields,truncated=ReviewSession._fields(card['fields'],budget=4000)
            previews.append({k:card[k] for k in ('id','kind','action','tier','note_id')} | {'fields':fields,'truncated_fields':truncated})
        cards,next_offset=page(previews,offset,limit,budget=16000)
        return {'run_id':run_id,'digest':p.digest,'content_digest':p.content_digest,'source':p.source,
                'cards':cards,'total':len(previews),'next_offset':next_offset,
                'findings_total':len(p.findings),'exact_records':'get_run_history then read_run_record'}

    def get_run_results(self, run_id: str, offset: Offset=0, limit: Limit=10) -> dict:
        """Read cumulative per-item outcomes without losing partial results to a response limit."""
        from .run_responses import application_summary
        c=self._coordinator()
        return application_summary(c._summary(run_id,c._latest(run_id)),offset,limit)

    def get_run_history(self, run_id: str, offset: Offset=0, limit: Limit=100) -> dict:
        """Read permanent event summaries; read_run_record returns exact evidence in bounded slices."""
        from .run_responses import page
        run=self._coordinator().runs.read(run_id)
        rows=[{'sequence':e.sequence,'kind':e.kind,'timestamp':e.timestamp} for e in run.events]
        events,next_offset=page(rows,offset,limit)
        return {'run_id':run_id,'events':events,'total':len(rows),'next_offset':next_offset}

    def read_run_record(self, run_id: str, sequence: Annotated[int,Field(ge=1)], offset: Offset=0) -> dict:
        """Read exact retained JSON evidence in 4,000-character slices. Never accesses arbitrary paths."""
        if type(sequence) is not int or sequence<1 or type(offset) is not int or offset<0:raise DomainError('LIMIT','Invalid record slice.')
        run=self._coordinator().runs.read(run_id)
        event=next((e for e in run.events if e.sequence==sequence),None)
        if event is None:raise DomainError('RUN','Unknown event sequence.')
        text=json.dumps(event.model_dump(),ensure_ascii=False,sort_keys=True)
        return {'run_id':run_id,'sequence':sequence,'text':text[offset:offset+4000],
                'next_offset':offset+4000 if offset+4000<len(text) else None}

    def list_student_runs(self, offset: Offset=0, limit: Limit=20) -> dict:
        """Resume durable runs by source label/workspace, with bounded summaries and corruption notices."""
        from .run_responses import page
        catalog=self._coordinator().runs.catalog()
        rows=[{'id':p.snapshot.id,'workspace':p.snapshot.workspace,'source':p.snapshot.selection.label,
               'last_event':p.snapshot.events[-1].kind,'updated_at':p.snapshot.events[-1].timestamp} for p in catalog.changed]
        rows.sort(key=lambda row:(row['updated_at'],row['id']),reverse=True)
        runs,next_offset=page(rows,offset,limit)
        return {'runs':runs,'total':len(rows),'next_offset':next_offset,'errors':dict(list(catalog.errors.items())[:20]),'error_count':len(catalog.errors)}

    def authorize_run(self, run_id: str, proposal_digest: str, mode: Literal['user','config']='user') -> dict:
        """Authorize this exact validated proposal; quality checks apply to both user and configuration authorization."""
        return self._coordinator().authorize(run_id,proposal_digest,mode).model_dump()

    def prepare_run_quality(self, run_id: str, content_digest: str, role: Literal['maintainer','student']) -> dict:
        """Prepare unchanged reviewer instructions and exact source/render inputs. Never claims reviewer execution."""
        from .quality import QualityGate
        return QualityGate(self._coordinator()).prepare(run_id,content_digest,role)

    def release_review_backs(self, run_id: str, content_digest: str, ticket_id: str, attempts: dict) -> dict:
        """Durably commit every front attempt before releasing student back images. Does not establish host budget support."""
        from .quality import QualityGate
        return QualityGate(self._coordinator()).release(run_id,content_digest,ticket_id,attempts)

    def submit_run_quality(self, run_id: str, content_digest: str, receipt: dict) -> dict:
        """Validate a trusted host-verifier attested execution receipt. Caller pass assertions are never accepted."""
        from .quality import QualityGate
        return QualityGate(self._coordinator()).submit(run_id,content_digest,receipt)

    async def apply_run(self, run_id: str, proposal_digest: str) -> dict:
        """Apply only an exactly authorized, quality-validated proposal with durable per-item intent and readback."""
        from .run_responses import application_summary
        return application_summary(await self._coordinator().apply(run_id,proposal_digest))

    async def reconcile_run(self, run_id: str) -> dict:
        """Read back uncertain intents by known identities; never resend creates or roll back collection data."""
        from .run_responses import application_summary
        return application_summary(await self._coordinator().reconcile(run_id))

    async def open_run_review(self, run_id: str) -> dict:
        """Open the production source-linked review App for this exact run. No collection writes."""
        from .review_session import ReviewSession
        return await ReviewSession(self._coordinator()).open(run_id)

    def read_run_review(self, run_id: str, session_token: str, offset: Offset=0) -> dict:
        """Read one bounded source-linked review item using its run/session binding."""
        from .review_session import ReviewSession
        return ReviewSession(self._coordinator()).read(run_id,session_token,offset)

    def read_run_review_field(self, run_id: str, session_token: str, concept_id: str, name: str,
                              note_id: int | None=None, offset: Offset=0) -> dict:
        """Read a complete field in bounded slices before editing it; never substitute a truncated preview."""
        from .review_session import ReviewSession
        return ReviewSession(self._coordinator()).field(run_id,session_token,concept_id,name,note_id,offset)

    async def save_run_review(self, run_id: str, session_token: str, expected_proposal_digest: str, decisions: list[dict]) -> dict:
        """Save run-only review decisions, invalidate affected approval/quality, and revalidate the proposal."""
        from .review_session import ReviewSession
        return await ReviewSession(self._coordinator()).decide(run_id,session_token,expected_proposal_digest,decisions)

    def approve_run_review(self, run_id: str, session_token: str, expected_proposal_digest: str) -> dict:
        """Explicit user approval from a current bound review session; existing quality gates remain mandatory."""
        from .review_session import ReviewSession
        return ReviewSession(self._coordinator()).approve(run_id,session_token,expected_proposal_digest)

    def propose_run_preferences(self, run_id: str, changes: dict) -> dict:
        """Show a plain-language preference diff for this run only; future defaults stay unchanged."""
        return self._coordinator().propose_run_preferences(run_id,changes)

    def confirm_run_preferences(self, run_id: str, change_id: str) -> dict:
        """Explicitly confirm a shown run-only choice and invalidate affected staged authorization."""
        return self._coordinator().confirm_run_preferences(run_id,change_id)

    def get_guidance(self, topic: Literal['overview','quality','maintainer','student']='overview') -> dict:
        """Read optional workflow examples or card/reviewer guidance. No prescribed tool sequence."""
        from cards.review.packets import TEMPLATES
        if topic=='overview': text=(Path(__file__).parent/'guidance'/'SKILL.md').read_text()
        elif topic=='quality': text=(TEMPLATES/'house-style.md').read_text()
        else: text=(TEMPLATES/topic/'rubric.md').read_text()
        return {'topic':topic,'text':text[:24000],'optional':True}

    def create_workspace(self, mode: Literal['lecture','cards']='cards', source_path: str | None=None,
                         text: Annotated[str,Field(max_length=1000000)] | None=None,
                         cards: Annotated[list[Card],Field(max_length=500)] | None=None) -> dict:
        """Create an isolated workspace from a local source, pasted text, or existing cards supplied by Anki MCP. Returns its explicit ID."""
        w=self.s.store.create(mode,source_path,text)
        if cards: self.s.save_cards(w['id'],[c.model_dump() for c in cards],0)
        return self.s.store.get(w['id'])

    def list_workspaces(self, offset: Offset=0, limit: Limit=20) -> dict:
        """List resumable workspaces; no global active-workspace pointer is used."""
        return self.s.store.list(offset,limit)

    def get_workspace(self, workspace: Workspace) -> dict:
        """Read workspace mode, source provenance and revision for mutation preconditions."""
        return self.s.store.get(workspace)

    def extract_source(self, workspace: Workspace, slides: str | None=None) -> dict:
        """Extract a PDF/text/Markdown source and OCR embedded figures. Optional slides use 1-based ranges such as 2-5,8. Returns a job ID."""
        return self.s.extract_source(workspace,slides)

    def read_source(self, workspace: Workspace, slides: str | None=None, offset: Offset=0,
                    limit: Annotated[int,Field(ge=1,le=24000)]=12000) -> dict:
        """Read bounded extracted source slices with slide references. Extract the source first; use next_offset to continue."""
        return self.s.read_source(workspace,slides,offset,limit)

    def search_source(self, workspace: Workspace, query: Annotated[str,Field(min_length=1,max_length=200)], offset: Offset=0, limit: Limit=20) -> dict:
        """Search extracted text case-insensitively; return matching lines and slide numbers."""
        return self.s.search_source(workspace,query,offset,limit)

    def get_source_evidence(self, workspace: Workspace, refs: Annotated[list[EvidenceRef],Field(min_length=1,max_length=20)]) -> dict:
        """Resolve source-hash/page citations to exact stored quotations, with OCR and physical-page labels. Text sections are not PDF pages."""
        return {'evidence':[item.model_dump() for item in EvidenceResolver(self.s.source_catalog).resolve(workspace,refs)],
                'source_accuracy_verified':False}

    def get_page_image(self, workspace: Workspace, page: Annotated[int,Field(ge=1,le=500)]) -> dict:
        """Rasterize one source PDF page as an artifact. Fetch it with get_image to inspect it."""
        return self.s.get_page_image(workspace,page)

    def list_figures(self, workspace: Workspace, offset: Offset=0, limit: Limit=20) -> dict:
        """List extracted figure IDs, crop artifacts, OCR labels and slide provenance."""
        return self.s.list_figures(workspace,offset,limit)

    def get_figure(self, workspace: Workspace, figure_id: str) -> dict:
        """Resolve an exact figure ID from list_figures; use get_image on the returned artifact."""
        return self.s.get_figure(workspace,figure_id)

    def import_image(self, workspace: Workspace, path: str) -> dict:
        """Copy an image from a configured source root into workspace media for OCR, occlusion or card previews."""
        return self.s.import_image(workspace,path)

    def ocr_image(self, workspace: Workspace, artifact: str, min_conf: Annotated[float,Field(ge=0,le=100)]=20,
                  min_len: Annotated[int,Field(ge=1,le=100)]=2, group: bool=True,
                  pad: Annotated[float,Field(ge=0,le=.1)]=.004) -> dict:
        """OCR a workspace image into fractional label regions, grouping repeated labels by default. Returns a job; inspect its JSON artifact and the image."""
        return self.s.ocr_image(workspace,artifact,min_conf,min_len,group,pad)

    def build_occlusion(self, workspace: Workspace, artifact: str,
                        regions: Annotated[list[Region],Field(min_length=1,max_length=500)],
                        mode: Literal['one','all']='one', keep: list[int] | None=None) -> dict:
        """Build Anki image-occlusion fields and a mask preview from selected fractional rectangles. Does not save a card or write to Anki."""
        return self.s.build_occlusion(workspace,artifact,[r.model_dump(exclude_none=True) for r in regions],mode,keep)

    def export_figures(self, workspace: Workspace, pages: str | None=None,
                       zoom: Annotated[float,Field(ge=.5,le=6)]=4,
                       min_frac: Annotated[float,Field(ge=0,le=1)]=.05, whole_page: bool=False) -> dict:
        """Export PDF image placements at OCR resolution, or whole pages for vector diagrams. Adjustable zoom/area threshold; returns a job."""
        return self.s.export_figures(workspace,pages,zoom,min_frac,whole_page)

    def measure_usage(self, workspace: Workspace, transcript: str) -> dict:
        """Optional Claude Code JSONL usage/waste diagnostic from an explicitly supplied allowed path. No history auto-discovery; not needed for card work."""
        return self.s.measure_usage(workspace,transcript)

    def resolve_target(self, filename: str='', course: str | None=None, number: Annotated[int,Field(ge=1,le=999)] | None=None,
                       title: str | None=None, subject: str | None=None, system: str | None=None,
                       existing_decks: list[str] | None=None, legacy: bool=False) -> dict:
        """Suggest lecture deck identity/tags from filename or explicit course/number/title. Supply deck names from Anki MCP to detect reuse. No deck is created."""
        return self.s.resolve_target(filename,course,number,title,subject,system,existing_decks,legacy)

    def save_cards(self, workspace: Workspace, cards: Annotated[list[Card],Field(min_length=1,max_length=500)], expected_revision: Revision) -> dict:
        """Atomically replace workspace cards with typed drafts or existing-note snapshots. Supply current revision; existing-note updates require note_id."""
        return self.s.save_cards(workspace,[c.model_dump() for c in cards],expected_revision)

    def patch_cards(self, workspace: Workspace, patches: Annotated[list[CardPatch],Field(min_length=1,max_length=500)], expected_revision: Revision) -> dict:
        """Edit selected drafts by stable ID without resending the card set. Field maps merge; other supplied properties replace their values. Never writes to Anki."""
        return self.s.patch_cards(workspace,[patch.model_dump() for patch in patches],expected_revision)

    def get_cards(self, workspace: Workspace, ids: Ids=None, offset: Offset=0, limit: Limit=20) -> dict:
        """Read a bounded card selection and current revision. For large fields use smaller pages or read_artifact on cards.json."""
        return self.s.get_cards(workspace,ids,offset,limit)

    def save_omissions(self, workspace: Workspace, omissions: Annotated[list[dict],Field(max_length=500)], expected_revision: Revision) -> dict:
        """Record deliberate lecture omissions as objects with positive slide and reason. Coverage checking may account for them."""
        return self.s.save_omissions(workspace,omissions,expected_revision)

    def check_cards(self, workspace: Workspace, ids: Ids=None, house_style: bool=False, coverage: bool=False) -> dict:
        """Check technical card validity independently; optionally check ColdRecall style or extracted lecture coverage. Does not judge factual truth."""
        return self.s.check_cards(workspace,ids,house_style,coverage)

    def render_cards(self, workspace: Workspace, ids: Ids=None,
                     front: Annotated[str,Field(max_length=30000)] | None=None,
                     back: Annotated[str,Field(max_length=30000)] | None=None,
                     css: Annotated[str,Field(max_length=50000)] | None=None,
                     per_sheet: Annotated[int,Field(ge=1,le=16)]=8,
                     desktop_sample: Annotated[int,Field(ge=0,le=10)]=0, light: bool=False) -> dict:
        """Render selected cards into inert previews/contact sheets. Accept supplied note-type templates/CSS or card question/answer HTML. Returns a job."""
        return self.s.render_cards(workspace,ids,front,back,css,per_sheet,desktop_sample,light)

    def prepare_review(self, workspace: Workspace, scope: Literal['content','visual']='content', ids: Ids=None) -> dict:
        """Prepare an optional content or visual-only bundle. Visual bundles omit fields and sources and require current previews. Host chooses reviewers."""
        return self.s.prepare_review(workspace,scope,ids)

    def submit_review(self, workspace: Workspace, reviewer: str,
                      findings: Annotated[list[Finding],Field(max_length=1000)], expected_revision: Revision) -> dict:
        """Save typed reviewer findings and proposed field rewrites without changing cards. Reviewer identity is caller-supplied, not verified."""
        return self.s.submit_review(workspace,reviewer,[f.model_dump() for f in findings],expected_revision)

    def apply_changes(self, workspace: Workspace, review_id: Workspace, expected_revision: Revision, ids: Ids=None, apply: bool=False) -> dict:
        """Preview selected review rewrites as a diff; set apply=true to save them against current revision. Rejects stale reviews and conflicting fields."""
        return self.s.apply_changes(workspace,review_id,expected_revision,ids,apply)

    def prepare_write(self, workspace: Workspace, expected_revision: Revision, ids: Ids=None) -> dict:
        """Prepare validated create/update batches, media/import files and suspension intentions for the official Anki MCP. Performs zero collection operations."""
        return self.s.prepare_write(workspace,expected_revision,ids)

    def record_external_results(self, workspace: Workspace, plan_id: Workspace,
                                results: Annotated[list[ExternalResult],Field(max_length=1000)], expected_revision: Revision) -> dict:
        """Record actual responses/evidence supplied by the host after official Anki MCP calls. Replaces this plan's supplied results; does not verify independently."""
        return self.s.record_external_results(workspace,plan_id,[r.model_dump() for r in results],expected_revision)

    def get_report(self, workspace: Workspace) -> dict:
        """Summarize planned actions, caller-reported results, ambiguity and stale plans. Never claims AnkiPlus performed collection writes."""
        return self.s.get_report(workspace)

    def cleanup_derived(self, workspace: Workspace, apply: bool=False, expected_digest: str | None=None) -> dict:
        """Preview explicit removal of reproducible workspace previews; apply only the exact shown digest. Permanent evidence is protected."""
        from .cleanup import DerivedCleanup
        return DerivedCleanup(self.s).run(workspace,apply,expected_digest)

    def list_artifacts(self, workspace: Workspace, offset: Offset=0, limit: Limit=50) -> dict:
        """List workspace-local source, preview, review and payload artifacts with pagination."""
        return self.s.artifacts(workspace,offset,limit)

    def read_artifact(self, workspace: Workspace, artifact: str, offset: Offset=0,
                      limit: Annotated[int,Field(ge=1,le=24000)]=12000) -> dict:
        """Read a bounded text/JSON artifact by its relative ID; use next_offset for continuation. Does not read arbitrary host files."""
        return self.s.read_artifact(workspace,artifact,offset,limit)

    def get_image(self, workspace: Workspace, artifact: str) -> CallToolResult:
        """Return a workspace preview, figure or page as an MCP image block, resized to at most 1600 pixels per side."""
        data=self.s.image_bytes(workspace,artifact)
        return CallToolResult(content=[ImageContent(type='image',mimeType='image/png',data=base64.b64encode(data).decode())])

    def get_job(self, workspace: Workspace, job_id: Workspace) -> dict:
        """Read persistent queued/running/completed/failed/cancelled/interrupted job state and result artifact references."""
        return self.s.jobs.get(workspace,job_id)

    def list_jobs(self, workspace: Workspace, status: Literal['queued','running','completed','cancelled','failed','interrupted'] | None=None, offset: Offset=0, limit: Limit=20) -> dict:
        """Rediscover resumable jobs after losing an ID. Returns bounded summaries without repeating large result artifacts."""
        return self.s.jobs.list(workspace,status,offset,limit)

    def cancel_job(self, workspace: Workspace, job_id: Workspace) -> dict:
        """Request cooperative cancellation of extraction/OCR/rendering; native work stops at its next safe boundary."""
        return self.s.jobs.cancel(workspace,job_id)


async def resolve_roots(server, store):
    """Settle unresolved source roots: folders the client offers, else a safe working directory, else none."""
    roots=[]
    try:
        session=server.get_context().session
        if session.client_params and session.client_params.capabilities.roots is not None:
            with anyio.move_on_after(5):
                listed=await session.list_roots()
                roots=[Path(unquote(urlparse(str(r.uri)).path)) for r in listed.roots if str(r.uri).startswith('file://')]
    except Exception:  # a client that cannot answer simply offers no roots
        roots=[]
    if roots:
        store.set_source_roots(roots,'client'); return
    fallback=settings.safe_cwd_root(Path.cwd(),Path.home())
    store.set_source_roots([fallback] if fallback else [],'cwd' if fallback else 'none')


def create_server(service):
    server=FastMCP('ankiplusmcp', instructions='AnkiPlus student workflows with source evidence and permanent run history. Use the durable student run tools for collection application: approved-scope coverage, immutable stage, independent quality evidence, exact authorization, conditional apply and read-only reconciliation. Setup must be verified. Mechanical workspace tools remain available. Caller-supplied legacy receipts never establish verified application. Companion access requires explicit connection configuration.')
    server._mcp_server.version=importlib.metadata.version('ankiplusmcp')
    read_only={'get_collection_choices','get_run_results','get_run_history','read_run_record','list_student_runs','read_run_review','read_run_review_field','get_run_proposal','get_student_setup','search_collection_coverage','capabilities','get_guidance','list_workspaces','get_workspace','read_source','search_source','get_source_evidence','list_figures','get_figure','resolve_target','get_cards','check_cards','prepare_review','get_report','list_artifacts','read_artifact','get_image','get_job','list_jobs'}
    for name,method in inspect.getmembers(API(service),predicate=inspect.ismethod):
        if name.startswith('_'): continue
        def wrap(method):
            @wraps(method)
            async def invoke(**kwargs):
                try:
                    if service.store.source_roots is None: await resolve_roots(server,service.store)
                    result=(await method(**kwargs) if inspect.iscoroutinefunction(method)
                            else await anyio.to_thread.run_sync(lambda: method(**kwargs)))
                    if isinstance(result,CallToolResult): return result
                    encoded=json.dumps(result,ensure_ascii=False,allow_nan=False)
                    if len(encoded)>64000:
                        raise DomainError('RESULT_LIMIT','Result exceeds 64,000 characters.','Reduce limit/select fewer cards, or use paginated read_artifact on the named artifact.')
                    return CallToolResult(content=[TextContent(type='text',text=encoded)],structuredContent=result)
                except (DomainError,CardsError,ValidationError,OSError,ValueError,KeyError) as exc:
                    if isinstance(exc,ValidationError): message=str(exc.errors(include_input=False))[:2000]
                    else: message=str(exc)[:2000]
                    error={'code':getattr(exc,'code','INPUT'),'message':message,'remedy':getattr(exc,'remedy','Check the input and available artifacts; retry with corrected values.')}
                    data={'status':'error','error':error}
                    return CallToolResult(isError=True,content=[TextContent(type='text',text=json.dumps(data))],structuredContent=data)
            return invoke
        from .review_app import URI
        meta=({'ui/resourceUri':URI,'ui':{'resourceUri':URI,**({'visibility':['app']} if name!='open_run_review' else {})}}
              if name in ('open_run_review','save_run_review','read_run_review','read_run_review_field','approve_run_review') else None)
        server.tool(name=name,meta=meta,annotations=ToolAnnotations(readOnlyHint=name in read_only,destructiveHint=False,openWorldHint=False),structured_output=False)(wrap(method))
    from .review_app import URI,MIME,html
    @server.resource(URI,name='AnkiPlus source-linked review',mime_type=MIME,meta={'ui':{'csp':{'connectDomains':[],'resourceDomains':[]}}})
    def review_resource():return html()
    return server
