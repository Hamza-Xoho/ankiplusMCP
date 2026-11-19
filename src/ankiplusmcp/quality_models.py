"""Supported captured model semantics, independent of draft labels."""
import re
from html.parser import HTMLParser
from .store import DomainError


def refuse_css_dependencies(css):
    # No CSS parser/loader is part of the supported inert render path. Refuse
    # escapes as well as literal resource syntax, so escapes cannot hide a URL.
    if re.search(r'url\s*\(|@import|\\',css,re.I):
        raise DomainError('UNSUPPORTED','CSS resource dependencies or escapes require a supported self-contained note type before review/application.')


def refuse_markup_dependencies(markup):
    class Styles(HTMLParser):
        in_style=False
        def handle_starttag(self,tag,attrs):
            if tag=='style':self.in_style=True
            if tag=='link' and dict(attrs).get('rel','').lower()=='stylesheet':raise DomainError('UNSUPPORTED','CSS stylesheet resources are unsupported for quality rendering.')
            for key,value in attrs:
                if key=='style':refuse_css_dependencies(value or '')
        def handle_endtag(self,tag):
            if tag=='style':self.in_style=False
        def handle_data(self,data):
            if self.in_style:refuse_css_dependencies(data)
    parser=Styles();parser.feed(markup);parser.close()


def captured_kind(model,fields):
    templates=model['tmpls']
    cloze=any('{{cloze:' in t[k] for t in templates for k in ('qfmt','afmt'))
    native='Occlusion' in fields and 'Image' in fields
    if native:
        if model.get('type')!=1 or model.get('name')!='Image Occlusion' or set(fields)!={'Occlusion','Image','Header','Back Extra','Comments'} or len(templates)!=1 or any('{{cloze:Occlusion}}' not in templates[0][k] for k in ('qfmt','afmt')):
            raise DomainError('UNSUPPORTED','Only the canonical native Image Occlusion model with fractional rectangle masks is supported.')
        return 'io'
    if model.get('type') not in (None,0,1):raise DomainError('UNSUPPORTED','Unknown captured note type semantics.')
    return 'cloze' if model.get('type')==1 or cloze else 'basic'
