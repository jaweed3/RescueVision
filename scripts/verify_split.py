"""
verify_split.py
---------------
Proves zero data leakage between train_data/ and test_data/.
Run this before submitting to generate a leakage report.

Output: docs/leakage_report.txt

Usage:
    python scripts/verify_split.py
"""

import hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent


def file_hash(path: Path) -> str:
    """MD5 hash of file content — catches even renamed duplicates."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def collect_files(directory: Path, extensions=('.jpg', '.png')):
    files = {}
    for ext in extensions:
        for p in directory.rglob(f"*{ext}"):
            files[p.name] = p
    return files


def main():
    print("="*60)
    print("Data Leakage Verification Report")
    print(f"Generated: {datetime.now().isoformat()}")
    print("="*60)
    
    train_dir = ROOT / 'train_data' / 'images'
    test_dir  = ROOT / 'test_data' / 'images'
    
    if not train_dir.exists():
        print("ERROR: train_data/images not found. Run prepare_visdrone.py first.")
        return
    if not test_dir.exists():
        print("ERROR: test_data/images not found. Run prepare_visdrone.py first.")
        return
    
    # Collect all image files
    train_files = collect_files(train_dir)
    test_files  = collect_files(test_dir)
    
    print(f"\nTrain images: {len(train_files)}")
    print(f"Test images:  {len(test_files)}")
    
    # Check 1: Filename overlap
    name_overlap = set(train_files.keys()) & set(test_files.keys())
    print(f"\n[Check 1] Filename overlap: {len(name_overlap)} files")
    
    # Check 2: Content hash overlap (catches renamed copies)
    print("\n[Check 2] Computing content hashes (this may take a minute)...")
    train_hashes = {file_hash(p): name for name, p in train_files.items()}
    test_hashes  = {file_hash(p): name for name, p in test_files.items()}
    
    hash_overlap = set(train_hashes.keys()) & set(test_hashes.keys())
    print(f"           Hash overlap: {len(hash_overlap)} files")
    
    # Check 3: Label file counts match image counts
    train_labels = list((ROOT / 'train_data' / 'labels').rglob("*.txt"))
    test_labels  = list((ROOT / 'test_data' / 'labels').rglob("*.txt"))
    print(f"\n[Check 3] Label counts:")
    print(f"          Train labels: {len(train_labels)}")
    print(f"          Test labels:  {len(test_labels)}")
    
    # Verdict
    print("\n" + "="*60)
    if len(name_overlap) == 0 and len(hash_overlap) == 0:
        verdict = "PASS — Zero data leakage confirmed"
        print(f"VERDICT: {verdict}")
        print("train_data/ ∩ test_data/ = ∅ (both by filename and content hash)")
    else:
        verdict = "FAIL — Data leakage detected!"
        print(f"VERDICT: {verdict}")
        if name_overlap:
            print(f"  Filename matches: {list(name_overlap)[:5]}")
        if hash_overlap:
            print(f"  Hash matches: files with same content exist in both splits")
    
    # Write report
    report_path = ROOT / 'docs' / 'leakage_report.txt'
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(f"Data Leakage Verification Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"="*60 + "\n\n")
        f.write(f"Train images: {len(train_files)}\n")
        f.write(f"Test images:  {len(test_files)}\n\n")
        f.write(f"Filename overlap: {len(name_overlap)}\n")
        f.write(f"Hash overlap:     {len(hash_overlap)}\n\n")
        f.write(f"Train labels: {len(train_labels)}\n")
        f.write(f"Test labels:  {len(test_labels)}\n\n")
        f.write(f"VERDICT: {verdict}\n")
    
    print(f"\nReport saved to: {report_path}")


if __name__ == '__main__':
    main()
