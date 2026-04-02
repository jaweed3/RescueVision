"""
RescueVision Edge — Pydantic Models
Request/Response schemas for FastAPI
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class VictimDetection(BaseModel):
    id: int
    confidence: float
    bbox: List[float]       # [x1, y1, x2, y2] in pixels
    cx_rel: float           # relative center X (0-1)
    cy_rel: float           # relative center Y (0-1)
    lat: Optional[float]    # GPS latitude
    lon: Optional[float]    # GPS longitude
    accuracy_m: Optional[float]  # coordinate accuracy estimate


class DetectionResult(BaseModel):
    filename: str
    total_victims: int
    detections: List[VictimDetection]
    inference_ms: float
    image_size: Dict[str, int]
    gps_source: str         # "exif" | "manual" | "none"
    ref_coords: Dict[str, Optional[float]]


class BatchResult(BaseModel):
    total_images: int
    total_victims: int
    results: List[DetectionResult]


class InjectConfig(BaseModel):
    """Dynamic Injection payload — Tahap 3 mechanism."""
    parameters: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "parameters": {
                    "conf_threshold": 0.4,
                    "grid_zone_size_m": 30
                }
            }
        }
