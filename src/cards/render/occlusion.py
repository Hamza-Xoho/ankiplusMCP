"""Static native IO masks: rasterize fractional rectangles without template JS."""
import base64
from html.parser import HTMLParser
import io
import math

from PIL import Image, ImageDraw, UnidentifiedImageError

from cards.common.errors import CardsError
from .templates import CLOZE, InertHTML


class ImageSource(HTMLParser):
    source = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and self.source is None:
            self.source = dict(attrs).get('src')


def bodies(build, fields, media):
    image_html = ImageSource()
    image_html.feed(fields['Image'])
    source = InertHTML(build, media).image(image_html.source or '')
    if not source:
        raise CardsError('E50', 'drafts.jsonl: line 1 field Image missing', 'supply build-contained IO media')
    try:
        with Image.open(io.BytesIO(base64.b64decode(source.split(',', 1)[1]))) as original:
            image = original.convert('RGB')
    except (ValueError, UnidentifiedImageError) as exc:
        raise CardsError('E50', 'drafts.jsonl: line 1 field Image invalid', 'supply a readable IO image') from exc
    regions = []
    try:
        for match in CLOZE.finditer(fields['Occlusion']):
            tokens = match[2].split(':')
            if tokens[:2] != ['image-occlusion', 'rect']:
                raise ValueError()
            values = dict(token.split('=', 1) for token in tokens[2:])
            geometry = [float(values[key]) for key in ('left', 'top', 'width', 'height')]
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in geometry):
                raise ValueError()
            left, top, width, height = geometry
            if width <= 0 or height <= 0 or left+width > 1.0001 or top+height > 1.0001 or values['oi'] not in ('0', '1'):
                raise ValueError()
            regions.append((int(match[1]), geometry, values['oi']))
        if not regions:
            raise ValueError()
    except (ValueError, KeyError) as exc:
        raise CardsError('E50', 'drafts.jsonl: line 1 field Occlusion invalid', 'supply native fractional rectangle masks') from exc
    header = fields.get('Header', '')
    def body(active=None):
        masked = image.copy()
        draw = ImageDraw.Draw(masked)
        for index, (left, top, width, height), hide_one in regions:
            if active is None or (hide_one == '1' and index != active):
                continue
            box = [left*image.width, top*image.height, (left+width)*image.width, (top+height)*image.height]
            draw.rectangle(box, fill=(255, 220, 110) if index == active else (143, 190, 255), outline=(90, 90, 90))
        buffer = io.BytesIO()
        masked.save(buffer, format='PNG')
        encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
        ordinal = f' data-ordinal="{active}"' if active is not None else ''
        return f'{header}<div{ordinal}><img src="data:image/png;base64,{encoded}"></div>'
    fronts = [(index, body(index)) for index in sorted({r[0] for r in regions})]
    back = body()
    extra = fields.get('Back Extra', '')
    if extra:
        back += '<div id="extra">' + extra + '</div>'
    return fronts, back
