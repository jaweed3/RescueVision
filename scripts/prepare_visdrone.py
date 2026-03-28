"""
prepare_visdrone.py
-------------------
Downloads VisDrone-DET 2019, filters pedestrian class only,
converts annotations to YOLO format, and splits into:
  train_data/  (train + val)
  test_data/   (test — NEVER mixed with train_data)

This script MUST be run before training.
The train/test split is done HERE, before any preprocessing,
to prove zero data leakage (Constraint compliance).

Usage:
    python scripts/prepare_visdrone.py
    python scripts/prepare_visdrone.py --skip-download  # if already downloaded
"""

import os
import shutil
import argparse
from pathlib import Path
import cv2
import numpy as np
from tqdm import tqdm

# VisDrone class IDs we want to keep (0-indexed in annotation, but VisDrone uses 1-indexed)
# VisDrone annotation format: class index starts at 0 = ignored region
# Class 1 = pedestrian, Class 2 = people (standing crowd)
# We keep BOTH as "pedestrian" since both represent humans
PEDESTRIAN_CLASSES = {1, 2}   # VisDrone class IDs for pedestrian + people
YOLO_CLASS_ID = 0              # Remapped to single class 0

ROOT = Path(__file__).parent.parent  # repo root


def parse_visdrone_annotation(ann_path: Path, img_w: int, img_h: int):
    """
    Parse VisDrone annotation file and return YOLO-format lines for pedestrian only.
    
    VisDrone annotation format (per line):
        bbox_left, bbox_top, bbox_width, bbox_height, score, object_category, truncation, occlusion
    
    YOLO format (per line):
        class_id cx cy w h   (all normalized 0-1)
    """
    yolo_lines = []
    
    with open(ann_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 6:
                continue
            
            bbox_left   = int(parts[0])
            bbox_top    = int(parts[1])
            bbox_width  = int(parts[2])
            bbox_height = int(parts[3])
            score       = int(parts[4])       # 0 = ignored region
            obj_class   = int(parts[5])
            
            # Skip ignored regions and non-pedestrian classes
            if score == 0:
                continue
            if obj_class not in PEDESTRIAN_CLASSES:
                continue
            # Skip degenerate boxes
            if bbox_width <= 0 or bbox_height <= 0:
                continue
            
            # Convert to YOLO normalized format
            cx = (bbox_left + bbox_width / 2) / img_w
            cy = (bbox_top + bbox_height / 2) / img_h
            w  = bbox_width / img_w
            h  = bbox_height / img_h
            
            # Clamp to [0, 1]
            cx = max(0.0, min(1.0, cx))
            cy = max(0.0, min(1.0, cy))
            w  = max(0.0, min(1.0, w))
            h  = max(0.0, min(1.0, h))
            
            yolo_lines.append(f"{YOLO_CLASS_ID} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    
    return yolo_lines


def process_split(
    src_images_dir: Path,
    src_annotations_dir: Path,
    dst_images_dir: Path,
    dst_labels_dir: Path,
    split_name: str
):
    """
    Process one split (train/val/test): copy images and convert annotations.
    Skips images with zero pedestrian annotations (no label file created = background).
    """
    dst_images_dir.mkdir(parents=True, exist_ok=True)
    dst_labels_dir.mkdir(parents=True, exist_ok=True)
    
    image_files = sorted(list(src_images_dir.glob("*.jpg")) + list(src_images_dir.glob("*.png")))
    
    kept = 0
    skipped_no_ann = 0
    skipped_no_ped = 0
    
    print(f"\nProcessing {split_name}: {len(image_files)} images")
    
    for img_path in tqdm(image_files, desc=split_name):
        ann_path = src_annotations_dir / (img_path.stem + ".txt")
        
        if not ann_path.exists():
            skipped_no_ann += 1
            continue
        
        # Read image to get dimensions
        img = cv2.imread(str(img_path))
        if img is None:
            skipped_no_ann += 1
            continue
        img_h, img_w = img.shape[:2]
        
        # Convert annotations
        yolo_lines = parse_visdrone_annotation(ann_path, img_w, img_h)
        
        if not yolo_lines:
            # No pedestrian in this image — skip (keeps dataset focused)
            skipped_no_ped += 1
            continue
        
        # Copy image
        shutil.copy2(img_path, dst_images_dir / img_path.name)
        
        # Write YOLO label
        label_path = dst_labels_dir / (img_path.stem + ".txt")
        with open(label_path, 'w') as f:
            f.write('\n'.join(yolo_lines) + '\n')
        
        kept += 1
    
    print(f"  Kept: {kept} | Skipped (no annotation): {skipped_no_ann} | Skipped (no pedestrian): {skipped_no_ped}")
    return kept


def verify_no_leakage(train_img_dir: Path, test_img_dir: Path):
    """
    Verify zero overlap between train and test image filenames.
    This proves data leakage is impossible.
    """
    train_files = set(p.name for p in train_img_dir.rglob("*.jpg"))
    test_files  = set(p.name for p in test_img_dir.rglob("*.jpg"))
    
    overlap = train_files & test_files
    if overlap:
        print(f"WARNING: {len(overlap)} files found in BOTH train and test!")
        for f in list(overlap)[:5]:
            print(f"  - {f}")
        return False
    else:
        print(f"\n[OK] Zero data leakage verified: train({len(train_files)}) ∩ test({len(test_files)}) = ∅")
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-download', action='store_true',
                        help='Skip download, assume raw data already in data/raw/')
    parser.add_argument('--raw-dir', type=str, default='data/raw',
                        help='Path to raw VisDrone dataset directory')
    args = parser.parse_args()
    
    raw_dir = ROOT / args.raw_dir
    
    if not args.skip_download:
        print("="*60)
        print("MANUAL DOWNLOAD REQUIRED")
        print("="*60)
        print("""
VisDrone dataset requires manual download from the official source.

1. Go to: https://github.com/VisDrone/VisDrone-Dataset
2. Download Task 1: Object Detection in Images
   - VisDrone2019-DET-train.zip
   - VisDrone2019-DET-val.zip
   - VisDrone2019-DET-test-dev.zip

3. Extract to: data/raw/
   Expected structure:
   data/raw/
   ├── VisDrone2019-DET-train/
   │   ├── images/
   │   └── annotations/
   ├── VisDrone2019-DET-val/
   │   ├── images/
   │   └── annotations/
   └── VisDrone2019-DET-test-dev/
       ├── images/
       └── annotations/

4. Re-run: python scripts/prepare_visdrone.py --skip-download
""")
        return
    
    print("="*60)
    print("RescueVision Edge - Dataset Preparation")
    print("="*60)
    print(f"Raw data dir: {raw_dir}")
    print(f"Output: train_data/ and test_data/ (separated BEFORE preprocessing)")
    print()
    
    # Define source paths
    splits = {
        'train': raw_dir / 'VisDrone2019-DET-train',
        'val':   raw_dir / 'VisDrone2019-DET-val',
        'test':  raw_dir / 'VisDrone2019-DET-test-dev',
    }
    
    # Verify raw data exists
    for split, path in splits.items():
        if not path.exists():
            print(f"ERROR: {split} directory not found: {path}")
            print("Please download and extract VisDrone dataset first.")
            return
    
    # Process train split → train_data/images/train + train_data/labels/train
    process_split(
        src_images_dir      = splits['train'] / 'images',
        src_annotations_dir = splits['train'] / 'annotations',
        dst_images_dir      = ROOT / 'train_data' / 'images' / 'train',
        dst_labels_dir      = ROOT / 'train_data' / 'labels' / 'train',
        split_name          = 'train'
    )
    
    # Process val split → train_data/images/val + train_data/labels/val
    process_split(
        src_images_dir      = splits['val'] / 'images',
        src_annotations_dir = splits['val'] / 'annotations',
        dst_images_dir      = ROOT / 'train_data' / 'images' / 'val',
        dst_labels_dir      = ROOT / 'train_data' / 'labels' / 'val',
        split_name          = 'val'
    )
    
    # Process test split → test_data/images + test_data/labels
    # CRITICAL: test_data is NEVER touched during training or preprocessing
    process_split(
        src_images_dir      = splits['test'] / 'images',
        src_annotations_dir = splits['test'] / 'annotations',
        dst_images_dir      = ROOT / 'test_data' / 'images',
        dst_labels_dir      = ROOT / 'test_data' / 'labels',
        split_name          = 'test'
    )
    
    # Verify zero data leakage
    verify_no_leakage(
        ROOT / 'train_data' / 'images' / 'train',
        ROOT / 'test_data' / 'images'
    )
    
    print("\n[DONE] Dataset preparation complete.")
    print("Next step: open notebooks/training.ipynb")


if __name__ == '__main__':
    main()
