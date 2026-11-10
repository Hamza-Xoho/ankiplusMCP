"""Anki's native text import format (headers must precede provenance)."""
import csv
import io
from cards.common.files import _write
from cards.common.errors import CardsError


def validate_header(deck,model):
    if any(c in value for value in (deck,model) for c in ('\n','\r')):
        raise CardsError('E73','import deck/notetype contains a line break','use a single-line deck and note type')

def emit(path, notes, deck, model):
    validate_header(deck,model)
    fields=list(notes[0]['fields'])
    # Anki accepts quoted multiline TSV; preserve HTML and tabs verbatim.
    stream=io.StringIO(newline='')
    stream.write(f'#separator:tab\n#html:true\n#notetype:{model}\n#deck:{deck}\n#tags column:{len(fields)+1}\n')
    writer=csv.writer(stream,delimiter='\t',lineterminator='\n')
    for n in notes:
        writer.writerow([n['fields'].get(f,'') for f in fields]+[' '.join(n['tags'])])
    text=stream.getvalue()
    if not path.exists() or path.read_text()!=text: _write(path,text)
