"""
RescueVision Edge — GPS Utilities
Reads EXIF GPS from DJI photos and calculates victim ground coordinates
"""

import math
from typing import Optional, Dict
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def extract_exif_gps(image_path: str) -> Optional[Dict]:
    """
    Extract GPS metadata from DJI drone photo EXIF.
    Returns dict with lat, lon, altitude, and focal length.
    """
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return None

        decoded = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            decoded[tag] = value

        gps_info_raw = decoded.get("GPSInfo")
        if not gps_info_raw:
            return None

        gps = {}
        for key, val in gps_info_raw.items():
            gps[GPSTAGS.get(key, key)] = val

        # Parse latitude and longitude
        lat = _dms_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef", "N"))
        lon = _dms_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef", "E"))

        if lat is None or lon is None:
            return None

        # Parse altitude
        altitude = None
        alt_raw = gps.get("GPSAltitude")
        if alt_raw:
            try:
                # Pillow might return a Rational or float
                altitude = float(alt_raw)
            except Exception:
                altitude = 80.0

        # Focal length (optional, for GSD calculation)
        focal_length = decoded.get("FocalLength", 4.5)
        if isinstance(focal_length, tuple):
            focal_length = float(focal_length[0]) / float(focal_length[1])

        return {
            "lat": lat,
            "lon": lon,
            "altitude": altitude or 80.0,
            "focal_length": float(focal_length)
        }

    except Exception:
        return None


def _dms_to_decimal(dms, ref) -> Optional[float]:
    """Convert DMS (degrees, minutes, seconds) to decimal degrees."""
    if dms is None or not isinstance(dms, (list, tuple)) or len(dms) < 3:
        return None
    try:
        degrees = float(dms[0])
        minutes = float(dms[1])
        seconds = float(dms[2])
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in ["S", "W"]:
            decimal = -decimal
        return decimal
    except Exception:
        return None


def calculate_victim_coordinates(
    drone_lat: float,
    drone_lon: float,
    altitude_m: float,
    bbox_cx: float,
    bbox_cy: float,
    img_width: int,
    img_height: int,
    focal_length: float = 4.5,
    sensor_width: float = 6.17
) -> Dict:
    """
    Calculate victim coordinates using the formula from Proposal Bab 4.1.3:
    GSD = (sensor_width * altitude) / (focal_length * image_width)
    dx_m = (bbox_cx - img_width/2) * GSD
    dy_m = (img_height/2 - bbox_cy) * GSD
    Target Lat = drone_lat + (dy_m / 111320)
    Target Lon = drone_lon + (dx_m / (111320 * cos(drone_lat)))
    """
    # 1. GSD Calculation
    gsd = (sensor_width * altitude_m) / (focal_length * img_width)

    # 2. Pixel Offset to Meters
    dx_m = (bbox_cx - img_width / 2.0) * gsd
    dy_m = (img_height / 2.0 - bbox_cy) * gsd

    # 3. Final GPS Coordinate
    # 1 degree latitude ≈ 111,320 m
    # 1 degree longitude ≈ 111,320 × cos(lat) m
    victim_lat = drone_lat + (dy_m / 111320.0)
    victim_lon = drone_lon + (dx_m / (111320.0 * math.cos(math.radians(drone_lat))))

    # Accuracy estimate based on GSD
    accuracy_m = round(gsd * 10, 2)  # Assuming 10px detection uncertainty

    return {
        "lat": victim_lat,
        "lon": victim_lon,
        "accuracy_m": accuracy_m
    }
