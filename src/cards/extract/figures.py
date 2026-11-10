"""Render embedded and vector figure placements at measured 4x resolution."""
import pymupdf as fitz

def export(page, build):
    area = page.rect.get_area() or 1
    rects = []
    for info in page.get_image_info():
        r = fitz.Rect(info['bbox']) & page.rect
        if r.get_area()/area >= .05 and tuple(r) not in [tuple(x) for x in rects]:
            rects.append(r)
    # Vector diagrams have no image placement: retain a whole-slide crop.
    if not rects and len(page.get_drawings()) >= 5:
        rects = [page.rect]
    rects.sort(key=lambda r: (-r.get_area(), r.y0, r.x0))
    result = []
    for i,r in enumerate(rects,1):
        ident = f'p{page.number+1:02d}_f{i}'
        relative = f'figures/{ident}.png'
        path = build.path('source/'+relative)
        path.parent.mkdir(parents=True,exist_ok=True)
        page.get_pixmap(clip=r,matrix=fitz.Matrix(4,4),alpha=False).pil_save(path, format='PNG', compress_level=1)
        result.append({'fig_id':ident,'file':relative,
                       'bbox':[r.x0/page.rect.width,r.y0/page.rect.height,r.x1/page.rect.width,r.y1/page.rect.height],
                       'ocr_labels':[], 'repeated_labels':[]})
    return result
