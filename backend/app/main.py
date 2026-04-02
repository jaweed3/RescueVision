"""
RescueVision Edge — FastAPI Backend
Tahap 3: Model → API → App

Run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import os
from pathlib import Path
from typing import Optional
import tempfile
import shutil

from app.inference import RescueVisionInference
from app.gps import extract_exif_gps, calculate_victim_coordinates
from app.models import DetectionResult, BatchResult, InjectConfig

# ─────────────────────────────────────────────
# App initialization
# ─────────────────────────────────────────────
app = FastAPI(
    title="RescueVision Edge API",
    description="Lightweight on-device victim detection for post-disaster SAR",
    version="1.0.0"
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Config (Dynamic Injection ready)
# ─────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent.parent / "config.json"

DEFAULT_CONFIG = {
    "conf_threshold": 0.25,
    "iou_threshold": 0.45,
    "input_size": 640,
    "grid_zone_size_m": 50,
    "export_format": ["csv", "json"],
    "max_batch_size": 100,
}

def load_config():
    config = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                loaded = json.load(f) or {}
            if isinstance(loaded, dict):
                config.update(loaded)
        except Exception:
            pass
    return config

config = load_config()

# ─────────────────────────────────────────────
# Model initialization
# ─────────────────────────────────────────────
MODEL_PATH = Path(__file__).parent.parent.parent / "model.onnx"
inference_engine = None

@app.on_event("startup")
async def startup_event():
    global inference_engine
    if not MODEL_PATH.exists():
        print(f"WARNING: model.onnx not found at {MODEL_PATH}")
        print("Place model.onnx in the repo root directory")
        return
    inference_engine = RescueVisionInference(
        model_path=str(MODEL_PATH),
        conf_threshold=config["conf_threshold"],
        iou_threshold=config["iou_threshold"],
        input_size=config["input_size"]
    )
    print(f"Model loaded: {MODEL_PATH}")
    print(f"Provider: {inference_engine.providers}")

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """System health check — includes model status and active config."""
    return {
        "status": "ok",
        "model_loaded": inference_engine is not None,
        "model_path": str(MODEL_PATH),
        "config": config,
        "providers": inference_engine.providers if inference_engine else None
    }


@app.post("/detect", response_model=DetectionResult)
async def detect_single(
    file: UploadFile = File(...),
    manual_lat: Optional[float] = None,
    manual_lon: Optional[float] = None,
    manual_altitude: Optional[float] = 80.0
):
    """
    Detect victims in a single drone image.
    
    - Reads GPS EXIF from DJI photos automatically
    - Falls back to manual_lat/manual_lon if no EXIF found
    - Returns bounding boxes + GPS coordinates per victim
    """
    if inference_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Check model.onnx path.")

    # Save uploaded file to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Run inference
        detections, inference_ms, img_w, img_h = inference_engine.run(tmp_path)

        # Extract GPS from EXIF (DJI photos)
        exif_gps = extract_exif_gps(tmp_path)

        # Determine reference GPS point
        if exif_gps:
            ref_lat = exif_gps["lat"]
            ref_lon = exif_gps["lon"]
            ref_alt = exif_gps.get("altitude", manual_altitude or 80.0)
            gps_source = "exif"
        elif manual_lat and manual_lon:
            ref_lat = manual_lat
            ref_lon = manual_lon
            ref_alt = manual_altitude or 80.0
            gps_source = "manual"
        else:
            ref_lat = None
            ref_lon = None
            ref_alt = None
            gps_source = "none"

        # Calculate victim coordinates
        enriched = []
        for i, det in enumerate(detections):
            victim = {
                "id": i + 1,
                "confidence": round(det["confidence"], 3),
                "bbox": det["box"],
                "cx_rel": det["cx_rel"],
                "cy_rel": det["cy_rel"],
            }
            if ref_lat and ref_lon:
                coords = calculate_victim_coordinates(
                    ref_lat, ref_lon, ref_alt,
                    det["cx_rel"], det["cy_rel"],
                    img_w, img_h
                )
                victim["lat"] = round(coords["lat"], 7)
                victim["lon"] = round(coords["lon"], 7)
                victim["accuracy_m"] = coords["accuracy_m"]
            else:
                victim["lat"] = None
                victim["lon"] = None
                victim["accuracy_m"] = None
            enriched.append(victim)

        return DetectionResult(
            filename=file.filename,
            total_victims=len(enriched),
            detections=enriched,
            inference_ms=round(inference_ms, 1),
            image_size={"width": img_w, "height": img_h},
            gps_source=gps_source,
            ref_coords={"lat": ref_lat, "lon": ref_lon, "altitude": ref_alt}
        )

    finally:
        os.unlink(tmp_path)


@app.post("/detect/batch", response_model=BatchResult)
async def detect_batch(
    files: list[UploadFile] = File(...),
    manual_lat: Optional[float] = None,
    manual_lon: Optional[float] = None
):
    """Process multiple drone images in batch."""
    if len(files) > config["max_batch_size"]:
        raise HTTPException(
            status_code=400,
            detail=f"Max batch size is {config['max_batch_size']} images"
        )

    results = []
    total_victims = 0

    for f in files:
        result = await detect_single(f, manual_lat, manual_lon)
        results.append(result)
        total_victims += result.total_victims

    return BatchResult(
        total_images=len(files),
        total_victims=total_victims,
        results=results
    )


@app.post("/inject")
async def dynamic_injection(inject: InjectConfig):
    """
    Dynamic Injection endpoint — Tahap 3 mechanism.
    Panitia can update any config parameter at runtime.
    """
    global config, inference_engine

    updated = {}
    for key, value in inject.parameters.items():
        if key in config:
            old_val = config[key]
            config[key] = value
            updated[key] = {"from": old_val, "to": value}

    # Re-initialize inference engine if threshold changed
    if any(k in updated for k in ["conf_threshold", "iou_threshold", "input_size"]):
        if inference_engine:
            inference_engine.update_config(
                conf_threshold=config["conf_threshold"],
                iou_threshold=config["iou_threshold"],
                input_size=config["input_size"]
            )

    # Persist config
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    return {
        "status": "updated",
        "updated_params": updated,
        "current_config": config
    }


@app.get("/export/csv")
async def export_csv():
    """Export all detected victim coordinates as CSV."""
    # In production, this reads from session storage
    # For demo, returns sample format
    csv_path = Path("detections_export.csv")
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="No detections to export yet")
    return FileResponse(csv_path, media_type="text/csv", filename="rescuevision_detections.csv")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
