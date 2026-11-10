"""Technical cloze and native image-occlusion validation for every deletion."""
import re
from cards.check.lint import CLOZE
from cards.render.occlusion import ImageSource
from .models import Region


def cloze_errors(text):
    matches=list(CLOZE.finditer(text))
    errors=[]
    if not matches: errors.append('No valid cloze deletion found.')
    if any(int(m[1])<1 or not m[2].strip() for m in matches):
        errors.append('Every cloze needs a positive number and nonempty answer.')
    if '{{c' in CLOZE.sub('',text): errors.append('Malformed or unclosed cloze deletion.')
    return errors


def io_errors(fields):
    errors=cloze_errors(fields.get('Occlusion',''))
    image=ImageSource(); image.feed(fields.get('Image',''))
    if not image.source or re.search(r'[/\\\x00]|^[a-zA-Z][a-zA-Z0-9+.-]*:',image.source):
        errors.append('Image must contain an img element referencing an Anki media filename.')
    markup=fields.get('Occlusion','')
    if re.sub(r'<br\s*/?>|\s','',CLOZE.sub('',markup),flags=re.I):
        errors.append('Occlusion contains unsupported non-mask markup.')
    for match in CLOZE.finditer(markup):
        try:
            tokens=match[2].split(':')
            if tokens[:2]!=['image-occlusion','rect']: raise ValueError()
            pairs=[token.split('=',1) for token in tokens[2:]]
            values=dict(pairs)
            if len(pairs)!=5 or set(values)!={'left','top','width','height','oi'} or values['oi'] not in ('0','1'): raise ValueError()
            Region.model_validate({key:float(values[key]) for key in ('left','top','width','height')})
        except (ValueError,KeyError):
            errors.append('Every native occlusion mask needs valid fractional rectangle geometry and oi=0 or oi=1.')
    return errors
