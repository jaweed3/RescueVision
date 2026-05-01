import torch
from pathlib import Path

for p in [
    "model/best.pt",
    "runs/detect/runs/train/rescuevision_v12/weights/best.pt",
    "runs/detect/runs/train/rescuevision_v13/weights/best.pt",
]:
    path = Path(p)
    if path.exists():
        ckpt = torch.load(path, map_location="cpu")
        fitness = ckpt.get("fitness", "N/A")
        epoch = ckpt.get("epoch", "N/A")
        print(f"{p}: epoch={epoch}, fitness={fitness}")
    else:
        print(f"{p}: NOT FOUND")
