from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent.parent / "model.onnx"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"
TILE_CACHE_DIR = Path(__file__).parent.parent / "tile_cache"
TILE_USER_AGENT = "RescueVision-Edge/1.0 (offline SAR system)"
TILE_SERVERS = ["a", "b", "c"]

DEFAULT_CONFIG = {
    "conf_threshold": 0.25,
    "iou_threshold": 0.45,
    "input_size": 640,
    "grid_zone_size_m": 50,
    "export_format": ["csv", "json"],
    "max_batch_size": 100,
}
