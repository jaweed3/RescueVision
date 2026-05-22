"""
Inspect saved YOLOv8 checkpoint files (epoch, fitness).
Usage: python scripts/check_run.py
"""
import torch
from pathlib import Path

BASE = Path(__file__).parent.parent

for p in [
    "model/best.pt",
    "runs/detect/runs/train/rescuevision_v12/weights/best.pt",
    "runs/detect/runs/train/rescuevision_v13/weights/best.pt",
]:
    path = BASE / p
    if path.exists():
        ckpt = torch.load(path, map_location="cpu")
        fitness = ckpt.get("fitness", "N/A")
        epoch = ckpt.get("epoch", "N/A")
        print(f"{p}: epoch={epoch}, fitness={fitness}")
    else:
        print(f"{p}: NOT FOUND")
