"""Manual characterization, collected only with -o python_functions=char_*.

Ground truth: {"fig_id":"p03_f1","labels":["Pectoralis major", ...]}.
The owner supplies labels by eye; do not derive this file from OCR output.
"""
import json
import re
import subprocess
import sys

def char_fr3_l007_label_recall(private_fixture, tmp_path):
    labels_path = private_fixture('l007_labels.json')
    pdf = private_fixture('MED241_L007_2026-09-14_anatomy-of-the-pectoral-region.pdf')
    truth = json.loads(labels_path.read_text())
    assert truth['labels'] and all(isinstance(t,str) and t.strip() for t in truth['labels'])
    build = tmp_path/'build'
    build.mkdir()
    (build/'build.json').write_text(json.dumps({'source':{'path':str(pdf)}}))
    run = subprocess.run([sys.executable,'-m','cards','extract','--build',str(build)],
                         capture_output=True,text=True)
    assert run.returncode in (0,1),run.stdout+run.stderr
    slides = json.loads((build/'source/slides.json').read_text())['slides']
    figures = {f['fig_id']:f for s in slides for f in s['figures']}
    figure = figures[truth['fig_id']]
    def normalize(text):
        return ' '.join(re.findall(r'\w+',text.casefold()))
    found = [normalize(r['text']) for r in figure['ocr_labels']]
    missed = [label for label in truth['labels']
              if not any(normalize(label) in region for region in found)]
    recall = (len(truth['labels'])-len(missed))/len(truth['labels'])
    assert recall >= .85, f'label recall {recall:.1%}; missed: {missed}'
