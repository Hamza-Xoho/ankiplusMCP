"""PDF text in column order, plus figure placement exports."""
import pymupdf as fitz
from .figures import export
from .ocr import extract as labels
from ..common.errors import CardsError

def read(path, build, selected=None):
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise CardsError('E21', f'{path}: line 1 field PDF unreadable', 'make it available offline and supply a valid PDF') from exc
    with doc:
        if doc.needs_pass:
            raise CardsError('E21',f'{path}: line 1 field PDF encrypted','supply an unencrypted copy')
        from ..common.source_data import selection
        numbers = selection(selected,range(1,len(doc)+1))
        for n in numbers:
            p = doc[n-1]
            blocks = [b for b in p.get_text('dict')['blocks'] if b['type']==0]
            lines = []
            for b in blocks:
                for l in b['lines']:
                    text = ''.join(s['text'] for s in l['spans']).strip()
                    if text:
                        lines.append((l['bbox'],text,max(s['size'] for s in l['spans'])))
            ordered = sorted(lines,key=lambda l:(l[0][1],l[0][0]))
            title_parts = ordered[:1]
            for line in ordered[1:]:
                prev = title_parts[-1]
                if not prev[1].endswith((':','?')) and abs(line[2]-title_parts[0][2]) < 1 and line[0][1]-prev[0][3] < line[2]*.6:
                    title_parts.append(line)
                else:
                    break
            title = ' '.join(l[1] for l in title_parts)
            # Full-width header/footer, then left-column body before right.
            top = [l for l in lines if l[0][1]<p.rect.height*.2]
            rest = [l for l in lines if l not in top]
            left = [l for l in rest if l[0][0]<p.rect.width*.5]
            right = [l for l in rest if l[0][0]>=p.rect.width*.5]
            text = '\n'.join(l[1] for part in (top,left,right) for l in sorted(part,key=lambda l:(l[0][1],l[0][0])))
            flags = []
            figures = export(p, build)
            if not text.strip():
                flags += ['image_only','scan']
                # A scan is already a whole-page figure; use all OCR words,
                # before label filtering, to preserve even short title words.
                from .ocr import _binarise, _words, merge_line_words
                from PIL import Image
                pix = p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
                image = Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                words = _words(_binarise(image),6,20,1)
                text = '\n'.join(w['text'] for w in merge_line_words(words))
                title = text.splitlines()[0] if text else ''
                if not text:
                    raise CardsError('E21',f'{path}: page {n} field text empty','supply a readable text layer or install Tesseract OCR')
            yield {'n':n,'title':title,'text':text,'speaker_notes':'',
                           'figures':figures,'flags':flags}
