"""
verify_split.py — Proves zero data leakage between train_data/ and test_data/.
Run before submitting. Output: docs/leakage_report.txt

Usage: python scripts/verify_split.py
"""
import hashlib, os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent

def file_hash(p):
    h = hashlib.md5()
    with open(p,'rb') as f: h.update(f.read())
    return h.hexdigest()

def collect(d, exts=('.jpg','.png')):
    files = {}
    for e in exts:
        for p in Path(d).rglob(f'*{e}'): files[p.name] = p
    return files

def main():
    train_dir = ROOT / 'train_data' / 'images'
    test_dir  = ROOT / 'test_data'  / 'images'
    print(f'Train: {train_dir}\nTest:  {test_dir}\n')
    
    tf = collect(train_dir); qf = collect(test_dir)
    name_overlap = set(tf) & set(qf)
    print(f'[Check 1] Filename overlap: {len(name_overlap)}')
    
    print('[Check 2] Hashing files...')
    th = {file_hash(p):n for n,p in tf.items()}
    qh = {file_hash(p):n for n,p in qf.items()}
    hash_overlap = set(th) & set(qh)
    print(f'          Hash overlap: {len(hash_overlap)}')
    
    passed = len(name_overlap)==0 and len(hash_overlap)==0
    verdict = 'PASS — Zero data leakage confirmed' if passed else 'FAIL — Leakage detected!'
    print(f'\nVERDICT: {verdict}')
    
    (ROOT/'docs').mkdir(exist_ok=True)
    with open(ROOT/'docs'/'leakage_report.txt','w') as f:
        f.write(f'Leakage Report — {datetime.now().isoformat()}\n')
        f.write(f'Train images: {len(tf)}\nTest images: {len(qf)}\n')
        f.write(f'Name overlap: {len(name_overlap)}\nHash overlap: {len(hash_overlap)}\n')
        f.write(f'VERDICT: {verdict}\n')
    print('Saved: docs/leakage_report.txt')

if __name__ == '__main__': main()
