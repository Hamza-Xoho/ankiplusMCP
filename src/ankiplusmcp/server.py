"""Typed stdio MCP facade. Collection operations stay in the official Anki MCP."""
import base64
from functools import wraps
import importlib.metadata
import inspect
import json
from pathlib import Path
import shutil
from typing import Annotated, Literal
import anyio
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ImageContent, ToolAnnotations
from pydantic import Field, ValidationError
from cards.common.errors import CardsError
from .models import Card, Region, Finding, ExternalResult
from .store import DomainError
from .service import Service

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
        for name in ('mcp','PyMuPDF','pillow','playwright','pytesseract'):
            try: dependencies[name]=importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError: dependencies[name]=None
        return {'server':'ankiplusmcp','version':importlib.metadata.version('ankiplusmcp'),'transport':'stdio',
                'anki_connection':'separate_host_dependency','anki_operations':False,
                'dependencies':dependencies,'tesseract_available':bool(shutil.which('tesseract')),
                'guidance_topics':['overview','quality','maintainer','student'],
                'source_roots':[str(p) for p in self.s.store.source_roots],
                'long_operations':'extract_source, ocr_image and render_cards return jobs; use get_job.',
                'missing_dependency_remedy':'Install the project dependencies, tesseract-ocr and run python -m playwright install chromium.'}

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

    def cancel_job(self, workspace: Workspace, job_id: Workspace) -> dict:
        """Request cooperative cancellation of extraction/OCR/rendering; native work stops at its next safe boundary."""
        return self.s.jobs.cancel(workspace,job_id)


def create_server(service):
    server=FastMCP('ankiplusmcp', instructions='Mechanical helper toolkit. Choose tools according to the user request. The official Anki MCP is a separate host dependency for all collection reads/writes. Optional get_guidance explains examples; no mandatory pipeline.')
    read_only={'capabilities','get_guidance','list_workspaces','get_workspace','read_source','search_source','list_figures','get_figure','resolve_target','get_cards','check_cards','prepare_review','get_report','list_artifacts','read_artifact','get_image','get_job'}
    for name,method in inspect.getmembers(API(service),predicate=inspect.ismethod):
        if name.startswith('_'): continue
        def wrap(method):
            @wraps(method)
            async def invoke(**kwargs):
                try:
                    result=await anyio.to_thread.run_sync(lambda: method(**kwargs))
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
        server.tool(name=name,annotations=ToolAnnotations(readOnlyHint=name in read_only,destructiveHint=False,openWorldHint=False),structured_output=False)(wrap(method))
    return server
