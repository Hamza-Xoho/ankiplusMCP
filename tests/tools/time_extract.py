"""Time the extraction steps on a synthetic 12-page lecture.

    time_extract.py <empty folder>

Prints seconds per figure for rendering and for OCR (one worker, no cache), then the wall
time of a full `extract_source` with an empty OCR cache, and again into a new output
folder with the same cache. Page content is synthetic, so the numbers say how fast the
code is, not how long a real lecture takes.
"""
import io
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))

PAGES = 12
LABELS = ['Nucleus', 'Ribosome', 'Golgi', 'Lysosome', 'Vesicle', 'Membrane', 'Cytoplasm', 'Mitochondrion']


def make_pdf(path: Path) -> None:
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont
    doc = pymupdf.open()
    font = ImageFont.load_default(size=28)
    for n in range(PAGES):
        page = doc.new_page(width=960, height=540)
        page.insert_text((40, 60), f'Synthetic slide {n + 1}', fontsize=32)
        image = Image.new('RGB', (1400, 900), 'white')
        draw = ImageDraw.Draw(image)
        for i, label in enumerate(LABELS):
            x, y = 80 + (i % 2) * 650, 60 + (i // 2) * 200
            draw.rectangle([x - 10, y - 10, x + 330, y + 60], outline='black', width=3)
            draw.text((x, y), f'{label} {n + 1}', fill='black', font=font)
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        page.insert_image(pymupdf.Rect(80, 100, 880, 514), stream=buffer.getvalue())
    doc.save(path)
    doc.close()


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    root = Path(argv[0])
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        print(f'{root} is not empty')
        return 2
    import pymupdf
    from cards.common.paths import Build
    from cards.extract import default_workers, extract_source, ocr_figures
    from cards.extract.figures import export
    from cards.extract.ocr import tesseract_version

    pdf = root / 'synthetic.pdf'
    make_pdf(pdf)
    print(f'cores {os.cpu_count()}, default workers {default_workers()}, {tesseract_version()}')

    build = Build(root / 'render')
    start = time.perf_counter()
    figures = []
    with pymupdf.open(pdf) as doc:
        for page in doc:
            figures += export(page, build)
    render = (time.perf_counter() - start) / len(figures)
    print(f'render: {render:.2f} s per figure ({len(figures)} figures)')

    paths = [build.path('source/' + f['file']) for f in figures]
    start = time.perf_counter()
    ocr_figures(paths, workers=1)
    ocr = (time.perf_counter() - start) / len(paths)
    print(f'ocr: {ocr:.2f} s per figure (one worker, no cache)')

    cache = root / 'ocr-cache'
    cache.mkdir()
    start = time.perf_counter()
    extract_source(pdf, root / 'cold', ocr_cache=cache)
    print(f'extract_source cold: {time.perf_counter() - start:.1f} s')
    start = time.perf_counter()
    extract_source(pdf, root / 'repeat', ocr_cache=cache)
    print(f'extract_source repeated, same cache: {time.perf_counter() - start:.1f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
