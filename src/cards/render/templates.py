"""The v1 cloze/template expansion, with inert HTML for the browser."""
import base64
import html
from html.parser import HTMLParser
import re

from cards.common.errors import CardsError

CLOZE = re.compile(r'\{\{c(\d+)::(.*?)(?:::((?:(?!\}\}).)*?))?\}\}', re.S)
SCRIPT = re.compile(r'<script\b[^>]*>.*?</script\s*>', re.S | re.I)


def cloze_field(text, n, side):
    def sub(m):
        number, answer, hint = int(m[1]), m[2], m[3]
        if n is None:
            return f'<span class="cloze" data-ordinal="{number}">{answer}</span>'
        if number != n:
            return f'<span class="cloze-inactive" data-ordinal="{number}">{answer}</span>'
        value = f'[{html.escape(hint) if hint else "..."}]' if side == 'front' else answer
        return f'<span class="cloze" data-ordinal="{n}">{value}</span>'
    return CLOZE.sub(sub, text)


def fill(template, fields, tags, n, side, front_html=''):
    text = re.sub(r'<!--.*?-->', '', SCRIPT.sub('', template), flags=re.S)
    def section(match):
        negated, name, body = match[1] == '^', match[2].strip(), match[3]
        present = bool(re.sub(r'<[^>]+>|\s|&nbsp;', '', fields.get(name, '')))
        return body if present != negated else ''
    for _ in range(3):
        text = re.sub(r'\{\{([#^])([^}]+)\}\}(.*?)\{\{/\2\}\}', section, text, flags=re.S)
    def field(match):
        spec = match[1].strip()
        if spec == 'FrontSide':
            return front_html
        parts, name = spec.split(':'), spec.split(':')[-1]
        if name == 'Tags':
            return html.escape(' '.join(tags))
        if 'cloze' in parts[:-1]:
            return cloze_field(fields.get(name, ''), n, side)
        return fields.get(name, '')
    return re.sub(r'\{\{(.*?)\}\}', field, text)


class InertHTML(HTMLParser):
    """Remove active elements and inline only build-contained image files."""
    suppressed = {'script', 'iframe', 'object', 'embed', 'applet', 'svg', 'math'}
    omitted = {'link', 'base', 'meta'}
    void = {'area', 'br', 'col', 'hr', 'img', 'input', 'source', 'track', 'wbr'}

    def __init__(self, build, media):
        super().__init__(convert_charrefs=False)
        self.build, self.media, self.parts, self.depth = build, media, [], 0

    def image(self, value):
        value = value.strip()
        if re.match(r'^data:image/(?:png|jpeg|gif|webp);base64,[a-z0-9+/=\s]+$', value, re.I):
            return value
        if re.match(r'^[a-z][a-z0-9+.-]*:|^//', value, re.I):
            return ''
        relative = self.media.get(value, value)
        path = self.build.path(relative)
        if not path.is_file():
            return ''
        mime = {'.png':'png', '.jpg':'jpeg', '.jpeg':'jpeg', '.gif':'gif', '.webp':'webp'}.get(path.suffix.lower())
        if not mime:
            raise CardsError('E50', f'{path}: line 1 field image unsupported', 'use a PNG, JPEG, GIF or WebP inside --build')
        return f'data:image/{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')

    def handle_starttag(self, tag, attrs):
        if self.depth:
            if tag in self.suppressed and tag not in {'embed'}:
                self.depth += 1
            return
        if tag in self.suppressed:
            if tag != 'embed':
                self.depth = 1
            return
        if tag in self.omitted:
            return
        safe = []
        for name, value in attrs:
            if name.startswith('on') or name in {'srcdoc', 'srcset', 'href', 'action', 'formaction', 'poster', 'background', 'data', 'xlink:href'}:
                continue
            if name == 'src':
                value = self.image(value or '') if tag == 'img' else ''
                if not value:
                    continue
            safe.append(name if value is None else f'{name}="{html.escape(value, quote=True)}"')
        self.parts.append('<' + tag + (' ' + ' '.join(safe) if safe else '') + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.depth:
            if tag in self.suppressed:
                self.depth -= 1
        elif tag not in self.suppressed | self.omitted | self.void:
            self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        if not self.depth:
            self.parts.append(data)

    def handle_entityref(self, name):
        if not self.depth:
            self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        if not self.depth:
            self.parts.append('&#' + name + ';')


def page(css, body, build, media):
    cleaner = InertHTML(build, media)
    cleaner.feed(body)
    cleaner.close()
    # Keep original CSS bytes; CSP and disabled browser JS block active resources.
    return ("<!doctype html><html class='mobile iphone night_mode'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            "style-src 'unsafe-inline'; img-src data:; font-src data:; script-src 'none'; frame-src 'none'\">"
            f"<style>{css.replace('</style', '< /style')}</style></head>"
            "<body class='card card1 nightMode night_mode'><div id='qa'>" + ''.join(cleaner.parts) + '</div></body></html>')
