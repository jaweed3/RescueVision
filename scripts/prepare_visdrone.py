"""
prepare_visdrone.py
Konversi VisDrone-DET 2019 annotation ke YOLO format.
Filter hanya kelas 'pedestrian' (VisDrone class ID = 1).

VisDrone annotation format per baris:
  bbox_left, bbox_top, bbox_width, bbox_height, score, object_category, truncation, occlusion

YOLO format per baris:
  class_id cx cy w h  (semua dinormalisasi 0-1 terhadap image size)

Jalankan SETELAH download dataset, SEBELUM split_dataset.py
"""

import os
import shutil
from pathlib import Path
from tqdm import tqdm

# ============================================================
# KONFIGURASI — sesuaikan path ke lokasi download VisDrone
# ============================================================
RAW_TRAIN_IMAGES = Path("data/raw/VisDrone2019-DET-train/images")
RAW_TRAIN_ANNOTS = Path("data/raw/VisDrone2019-DET-train/annotations")
RAW_VAL_IMAGES = Path("data/raw/VisDrone2019-DET-val/images")
RAW_VAL_ANNOTS = Path("data/raw/VisDrone2019-DET-val/annotations")
RAW_TEST_IMAGES = Path("data/raw/VisDrone2019-DET-test-dev/images")
RAW_TEST_ANNOTS = Path("data/raw/VisDrone2019-DET-test-dev/annotations")

OUTPUT_TRAIN_IMG = Path("train_data/images/train")
OUTPUT_TRAIN_LBL = Path("train_data/labels/train")
OUTPUT_VAL_IMG = Path("train_data/images/val")
OUTPUT_VAL_LBL = Path("train_data/labels/val")
OUTPUT_TEST_IMG = Path("test_data/images")
OUTPUT_TEST_LBL = Path("test_data/labels")

# VisDrone class IDs yang kita ambil
# 0=ignored, 1=pedestrian, 2=people, 3=bicycle, 4=car, ...
# Kita ambil pedestrian (1) dan people (2) → remap ke class 0
PEDESTRIAN_CLASSES = {1, 2}

# Minimum visibility — skip objek yang sangat ter-occlude
# occlusion: 0=no, 1=partial, 2=heavy. Kita skip heavy occlusion (2)
MAX_OCCLUSION = 1

# ============================================================


def convert_bbox_visdrone_to_yolo(bbox_left, bbox_top, bbox_w, bbox_h, img_w, img_h):
    """Konversi dari absolute pixel ke YOLO normalized cx,cy,w,h"""
    cx = (bbox_left + bbox_w / 2) / img_w
    cy = (bbox_top + bbox_h / 2) / img_h
    w = bbox_w / img_w
    h = bbox_h / img_h
    # Clamp ke [0, 1]
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))
    w = max(0.0, min(1.0, w))
    h = max(0.0, min(1.0, h))
    return cx, cy, w, h


def get_image_size(img_path: Path):
    """Ambil resolusi gambar tanpa load full pixel"""
    import struct, imghdr

    # Fast path untuk JPEG dan PNG
    with open(img_path, "rb") as f:
        head = f.read(24)
    if imghdr.what(img_path) == "png":
        w = struct.unpack(">I", head[16:20])[0]
        h = struct.unpack(">I", head[12:16])[0]
        return w, h
    # Fallback via opencv
    import cv2

    img = cv2.imread(str(img_path))
    if img is None:
        raise ValueError(f"Cannot read image: {img_path}")
    return img.shape[1], img.shape[0]


def process_split(
    img_src: Path, ann_src: Path, img_dst: Path, lbl_dst: Path, split_name: str
):
    """
    Proses satu split (train/val/test).
    Returns: (n_images_processed, n_annotations_written, n_skipped_no_pedestrian)
    """
    if not img_src.exists():
        print(
            f"  [SKIP] {img_src} tidak ditemukan — pastikan VisDrone sudah didownload"
        )
        return 0, 0, 0

    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    image_files = sorted(img_src.glob("*.jpg")) + sorted(img_src.glob("*.png"))
    n_images = 0
    n_annots = 0
    n_skipped = 0

    print(f"\nProcessing {split_name}: {len(image_files)} images")

    for img_path in tqdm(image_files, desc=split_name):
        ann_path = ann_src / (img_path.stem + ".txt")
        if not ann_path.exists():
            n_skipped += 1
            continue

        try:
            img_w, img_h = get_image_size(img_path)
        except Exception as e:
            print(f"  [WARN] Cannot read {img_path.name}: {e}")
            n_skipped += 1
            continue

        yolo_lines = []
        with open(ann_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) < 8:
                    continue

                bbox_left = int(parts[0])
                bbox_top = int(parts[1])
                bbox_w = int(parts[2])
                bbox_h = int(parts[3])
                score = int(parts[4])  # 0=ignored
                obj_cat = int(parts[5])
                truncation = int(parts[6])
                occlusion = int(parts[7])

                # Skip ignored regions
                if score == 0:
                    continue

                # Skip non-pedestrian classes
                if obj_cat not in PEDESTRIAN_CLASSES:
                    continue

                # Skip heavily occluded
                if occlusion > MAX_OCCLUSION:
                    continue

                # Skip invalid bbox
                if bbox_w <= 0 or bbox_h <= 0:
                    continue

                cx, cy, w, h = convert_bbox_visdrone_to_yolo(
                    bbox_left, bbox_top, bbox_w, bbox_h, img_w, img_h
                )

                # Skip extremely small objects (noise)
                if w * img_w < 2 or h * img_h < 2:
                    continue

                # class_id = 0 (pedestrian)
                yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

        # Hanya copy gambar yang punya minimal 1 pedestrian annotation
        if len(yolo_lines) == 0:
            n_skipped += 1
            continue

        # Copy image
        shutil.copy2(img_path, img_dst / img_path.name)

        # Write label
        lbl_file = lbl_dst / (img_path.stem + ".txt")
        with open(lbl_file, "w") as f:
            f.write("\n".join(yolo_lines) + "\n")

        n_images += 1
        n_annots += len(yolo_lines)

    return n_images, n_annots, n_skipped


def main():
    print("=" * 60)
    print("RescueVision Edge — VisDrone Dataset Preparation")
    print("=" * 60)
    print(f"Filter: pedestrian classes {PEDESTRIAN_CLASSES} → YOLO class 0")
    print(f"Max occlusion: {MAX_OCCLUSION} (0=none, 1=partial, 2=heavy)")

    splits = [
        (
            RAW_TRAIN_IMAGES,
            RAW_TRAIN_ANNOTS,
            OUTPUT_TRAIN_IMG,
            OUTPUT_TRAIN_LBL,
            "train",
        ),
        (RAW_VAL_IMAGES, RAW_VAL_ANNOTS, OUTPUT_VAL_IMG, OUTPUT_VAL_LBL, "val"),
        (RAW_TEST_IMAGES, RAW_TEST_ANNOTS, OUTPUT_TEST_IMG, OUTPUT_TEST_LBL, "test"),
    ]

    total_images = 0
    total_annots = 0

    for img_src, ann_src, img_dst, lbl_dst, name in splits:
        n_img, n_ann, n_skip = process_split(img_src, ann_src, img_dst, lbl_dst, name)
        print(f"  → {name}: {n_img} images, {n_ann} annotations, {n_skip} skipped")
        total_images += n_img
        total_annots += n_ann

    print("\n" + "=" * 60)
    print(f"DONE. Total: {total_images} images, {total_annots} annotations")
    print("Struktur output:")
    print("  train_data/images/train  + train_data/labels/train")
    print("  train_data/images/val    + train_data/labels/val")
    print("  test_data/images         + test_data/labels")
    print("\nLanjut: python src/split_dataset.py  (opsional, jika perlu re-split)")
    print("=" * 60)


if __name__ == "__main__":
    main()
