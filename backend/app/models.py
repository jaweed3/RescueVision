"""
RescueVision Edge — Pydantic Models
Request/Response schemas for FastAPI
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AppConfig(BaseModel):
    conf_threshold: float = 0.25
    iou_threshold: float = 0.45
    input_size: int = 640
    grid_zone_size_m: int = 50
    export_format: List[str] = ["csv", "json"]
    max_batch_size: int = 100


class ImageSize(BaseModel):
    width: int
    height: int


class RefCoords(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    altitude: Optional[float] = None


class VictimDetection(BaseModel):
    id: int
    confidence: float
    bbox: List[float]
    cx_rel: float
    cy_rel: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    accuracy_m: Optional[float] = None


class DetectionResult(BaseModel):
    filename: str
    total_victims: int
    detections: List[VictimDetection]
    inference_ms: float
    image_size: ImageSize
    gps_source: str
    ref_coords: RefCoords


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
