"""Read precisely the requested portion of extracted source."""
from pathlib import Path
from .common.paths import Build
from .common.output import Result
from .common.source_data import slides_data, source_path, selection
from .common.errors import CardsError

def slice_text(data, numbers):
    return '\n\n'.join(f"## Slide {s['n']} — {s['title']}\n{s['text']}"
                       for s in data['slides'] if s['n'] in numbers)

def page_image(pdf: Path, out: Path, page: int) -> Path:
    """Render one PDF page to `out` (1,000 pixels on its longest side) and return `out`."""
    pdf, out = Path(pdf), Path(out)
    if pdf.suffix.lower()!='.pdf':
        raise CardsError('E23','source: field page-image requires PDF','use --slides for text sources')
    import pymupdf as fitz
    out.parent.mkdir(parents=True,exist_ok=True)
    try:
        doc = fitz.open(pdf)
        if doc.needs_pass or page > len(doc):
            doc.close()
            raise ValueError("encrypted or changed PDF")
    except Exception as exc:
        raise CardsError("E23", f"{pdf}: field PDF unreadable or changed", "restore the extracted source PDF") from exc
    try:
        with doc:
            p = doc[page-1]
            scale = 1000/max(p.rect.width,p.rect.height)
            p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(out)
    except Exception as exc:
        raise CardsError('E23',f'{pdf}: field page-image render failed',
                         'restore a readable PDF and writable build folder') from exc
    return out

def run(args):
    build = Build(args.build)
    data = slides_data(build)
    slides = data['slides']
    available = [s['n'] for s in slides]
    if args.page_image is not None:
        selection(str(args.page_image),available)
        path,_ = source_path(build)
        return Result(files=[page_image(path,build.path(f'source/pages/p{args.page_image:02d}.png'),args.page_image)])
    if args.figure:
        for s in slides:
            for f in s['figures']:
                if f['fig_id']==args.figure:
                    return Result(lines=[x['text'] for x in f['ocr_labels']],files=[build.path('source/'+f['file'])],unlimited=True)
        raise CardsError('E23',f'{args.figure}: field figure unknown','choose a figure ID in slides.json')
    if args.grep is not None:
        hits = [f"Slide {s['n']}: {line}" for s in slides for line in s['text'].splitlines()
                if args.grep.casefold() in line.casefold()]
        return Result(lines=hits[:20],unlimited=True)
    numbers = selection(args.slides,available) if not args.all else available
    return Result(lines=[slice_text(data,numbers)],unlimited=True)
