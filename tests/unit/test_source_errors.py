import json
import subprocess
import sys

def run(*args,env=None):
    return subprocess.run([sys.executable,'-m','cards',*map(str,args)],capture_output=True,text=True,env=env)

def test_page_image_changed_pdf(tmp_path):
    b=tmp_path/'b'
    (b/'source').mkdir(parents=True)
    p=tmp_path/'bad.pdf'
    p.write_bytes(b'broken PDF')
    (b/'build.json').write_text(json.dumps({'source':{'path':str(p)}}))
    (b/'source/slides.json').write_text(json.dumps({'slides':[{'n':1,'title':'One','text':'Body','figures':[]}]}))
    r=run('source','--build',b,'--page-image','1')
    assert r.returncode==2 and r.stdout.startswith('ERROR\n') and 'E2' in r.stdout
    assert 'Traceback' not in r.stderr

def test_invalid_slides_root(tmp_path):
    (tmp_path/'source').mkdir()
    (tmp_path/'source/slides.json').write_text('[]')
    r=run('source','--build',tmp_path,'--all')
    assert r.returncode==2 and r.stdout.startswith('ERROR\n')

def test_invalid_slide_record(tmp_path):
    (tmp_path/'source').mkdir()
    (tmp_path/'source/slides.json').write_text('{"slides":[{}]}')
    r=run('source','--build',tmp_path,'--all')
    assert r.returncode==2 and r.stdout.startswith('ERROR\n')

def test_ocr_missing_engine_is_structured(tmp_path):
    import os
    from cards.extract.ocr import _words
    from cards.common.errors import CardsError
    from PIL import Image
    import pytest
    old=os.environ.get('PATH')
    try:
        os.environ['PATH']=str(tmp_path)
        with pytest.raises(CardsError,match='Tesseract'):
            _words(Image.new('RGB',(20,20),'white'),6,20,1)
    finally:
        if old is None: os.environ.pop('PATH',None)
        else: os.environ['PATH']=old

def test_corrupt_cache_root_recovers(tmp_path):
    b=tmp_path/'b'
    (b/'source').mkdir(parents=True)
    p=tmp_path/'lecture.txt'
    p.write_text('Actual lecture content')
    (b/'build.json').write_text(json.dumps({'source':{'path':str(p)}}))
    (b/'source/slides.json').write_text('[]')
    r=run('extract','--build',b)
    assert r.returncode in (0,1),r.stdout+r.stderr
    assert json.loads((b/'source/slides.json').read_text())['slides'][0]['text']=='Actual lecture content'
