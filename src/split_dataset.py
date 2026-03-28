"""
split_dataset.py
Re-split dataset jika diperlukan.
CATATAN: prepare_visdrone.py sudah menggunakan VisDrone official train/val/test split.
Script ini hanya diperlukan jika ingin custom split dari VisDrone train saja.

Pemisahan dilakukan SEBELUM preprocessing apapun — sesuai constraint umum.
"""

import shutil
import random
from pathlib import Path

def verify_no_leakage():
    train = set(p.stem for p in Path('train_data/images/train').glob('*.jpg'))
    val   = set(p.stem for p in Path('train_data/images/val').glob('*.jpg'))
    test  = set(p.stem for p in Path('test_data/images').glob('*.jpg'))
    
    assert len(train & test) == 0, f"LEAK: {len(train & test)} train-test overlaps"
    assert len(val & test)   == 0, f"LEAK: {len(val & test)} val-test overlaps"
    assert len(train & val)  == 0, f"LEAK: {len(train & val)} train-val overlaps"
    print(f"✅ No data leakage. Train={len(train)}, Val={len(val)}, Test={len(test)}")

if __name__ == "__main__":
    verify_no_leakage()
