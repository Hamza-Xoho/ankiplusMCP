"""Deterministic external OCR boundary for the synthetic CLI baseline only.

This is not a substitute for real OCR quality tests. No production code loads it.
"""
import sys

if sys.argv[1:] == ['--version']:
    print('tesseract fixture-1')
elif sys.argv[1:3] == ['stdin', 'stdout'] and sys.argv[-1:] == ['tsv']:
    sys.stdin.buffer.read()
    print('level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext')
    for number, text in enumerate(('Nucleus', 'Ribosome', 'Golgi', 'Lysosome'), 1):
        print(f'5\t1\t{number}\t1\t1\t1\t200\t{number * 240}\t400\t80\t95\t{text}')
else:
    raise SystemExit('unsupported baseline OCR invocation')
