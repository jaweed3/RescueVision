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
import logging
import os
from collections import deque
from pathlib import Path
from typing import Optional
import tempfile
import shutil

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

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

# CORS — allow all origins for Edge tool accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        except json.JSONDecodeError as e:
            logger.warning("config.json is invalid JSON (%s) — using defaults", e)
        except OSError as e:
            logger.warning("Could not read config.json (%s) — using defaults", e)
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
    logger.info("[STARTUP] RescueVision Edge backend starting up")
    logger.info("[STARTUP] Config: %s", config)
    if not MODEL_PATH.exists():
        logger.error("[STARTUP] model.onnx NOT FOUND at %s — inference disabled", MODEL_PATH)
        return
    inference_engine = RescueVisionInference(
        model_path=str(MODEL_PATH),
        conf_threshold=config["conf_threshold"],
        iou_threshold=config["iou_threshold"],
        input_size=config["input_size"]
    )
    logger.info("[STARTUP] Model loaded: %s", MODEL_PATH)
    logger.info("[STARTUP] ONNX providers: %s", inference_engine.providers)

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# Storage for export
# ─────────────────────────────────────────────
DETECTIONS_LOG: deque = deque(maxlen=10_000)

@app.get("/health")
async def health_check():
    """System health check — exactly as requested."""
    return {
        "status": "ok",
        "model_loaded": inference_engine is not None,
        "provider": inference_engine.providers if inference_engine else ["CPUExecutionProvider"]
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
    """
    if inference_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    file_size_bytes = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
        file_size_bytes = tmp.tell()

    logger.info(
        "[DETECT] Incoming upload — filename=%r content_type=%r size=%.1f KB",
        file.filename, file.content_type, file_size_bytes / 1024
    )
    logger.debug(
        "[DETECT] Manual GPS params — manual_lat=%s manual_lon=%s manual_altitude=%s",
        manual_lat, manual_lon, manual_altitude
    )

    try:
        detections, inference_ms, img_w, img_h = inference_engine.run(tmp_path)
        logger.info(
            "[DETECT] Inference done — %.1f ms | image=%dx%d | raw detections=%d",
            inference_ms, img_w, img_h, len(detections)
        )

        exif_gps = extract_exif_gps(tmp_path)

        if exif_gps:
            ref_lat = exif_gps["lat"]
            ref_lon = exif_gps["lon"]
            focal = exif_gps.get("focal_length", 4.5)
            gps_source = "exif"

            altitude_is_agl = exif_gps.get("altitude_is_agl", True)
            gps_method = exif_gps.get("gps_method", "gps")

            if altitude_is_agl:
                # Drone GPS — altitude is height above ground, safe to use for GSD
                ref_alt = exif_gps.get("altitude", manual_altitude or 80.0)
                logger.info(
                    "[GPS] Source=EXIF (method=%s) | lat=%.6f lon=%.6f alt=%.1fm (AGL) focal=%.2fmm",
                    gps_method, ref_lat, ref_lon, ref_alt, focal
                )
            else:
                # Network/WiFi GPS — altitude is ASL, would break GSD calculation
                # Use manual_altitude if provided, else default 80m
                ref_alt = manual_altitude if manual_altitude and manual_altitude != 80.0 else 80.0
                logger.warning(
                    "[GPS] Source=EXIF (method=%s) | lat=%.6f lon=%.6f | "
                    "EXIF altitude=%.1fm is ASL — using %.1fm for GSD instead. "
                    "Set manual_altitude for accurate results.",
                    gps_method, ref_lat, ref_lon, exif_gps.get("altitude", 0), ref_alt
                )
        elif manual_lat and manual_lon:
            ref_lat = manual_lat
            ref_lon = manual_lon
            ref_alt = manual_altitude or 80.0
            focal = 4.5
            gps_source = "manual"
            logger.info(
                "[GPS] Source=MANUAL | lat=%.6f lon=%.6f alt=%.1fm",
                ref_lat, ref_lon, ref_alt
            )
        else:
            ref_lat, ref_lon, ref_alt, focal = None, None, None, 4.5
            gps_source = "none"
            logger.warning(
                "[GPS] Source=NONE — no EXIF GPS and no manual coords provided. "
                "Map will be empty. filename=%r content_type=%r size=%.1f KB",
                file.filename, file.content_type, file_size_bytes / 1024
            )

        enriched = []
        for i, det in enumerate(detections):
            victim = {
                "id": len(DETECTIONS_LOG) + i + 1,
                "confidence": round(det["confidence"], 3),
                "bbox": det["box"],
                "cx_rel": det["cx_rel"],
                "cy_rel": det["cy_rel"],
            }
            if ref_lat and ref_lon:
                coords = calculate_victim_coordinates(
                    ref_lat, ref_lon, ref_alt,
                    det["cx_rel"] * img_w, det["cy_rel"] * img_h,
                    img_w, img_h,
                    focal_length=focal
                )
                victim["lat"] = round(coords["lat"], 7)
                victim["lon"] = round(coords["lon"], 7)
                victim["accuracy_m"] = coords["accuracy_m"]
                logger.debug(
                    "[VICTIM #%d] conf=%.3f bbox=%s → lat=%.6f lon=%.6f acc=%.1fm",
                    victim["id"], victim["confidence"], det["box"],
                    victim["lat"], victim["lon"], victim["accuracy_m"]
                )
                # Log for export
                DETECTIONS_LOG.append({
                    "filename": file.filename,
                    "lat": victim["lat"],
                    "lon": victim["lon"],
                    "confidence": victim["confidence"]
                })
            else:
                victim["lat"] = None
                victim["lon"] = None
                victim["accuracy_m"] = None
                logger.debug(
                    "[VICTIM #%d] conf=%.3f bbox=%s → NO GPS COORDS (gps_source=none)",
                    victim["id"], victim["confidence"], det["box"]
                )
            enriched.append(victim)

        logger.info(
            "[DETECT] Result — file=%r victims=%d gps_source=%s",
            file.filename, len(enriched), gps_source
        )

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
    manual_lon: Optional[float] = None,
    manual_altitude: Optional[float] = 80.0
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
        result = await detect_single(f, manual_lat, manual_lon, manual_altitude)
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
    Changes are persisted to config.json so they survive restarts.
    """
    global config, inference_engine

    updated = {}
    for key, value in inject.parameters.items():
        if key in config:
            old_val = config[key]
            config[key] = value
            updated[key] = {"from": old_val, "to": value}

    if any(k in updated for k in ["conf_threshold", "iou_threshold", "input_size"]):
        if inference_engine:
            inference_engine.update_config(
                conf_threshold=config["conf_threshold"],
                iou_threshold=config["iou_threshold"],
                input_size=config["input_size"]
            )

    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        logger.warning("Could not persist config.json (%s) — changes are in-memory only", e)

    return {
        "status": "updated",
        "updated_params": updated,
        "current_config": config
    }


@app.get("/export/csv")
async def export_csv():
    """Export all detected victim coordinates."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["filename", "lat", "lon", "confidence"])
    writer.writeheader()
    writer.writerows(DETECTIONS_LOG)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=victims.csv"}
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
