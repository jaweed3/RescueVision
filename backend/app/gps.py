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
    Returns dict with lat, lon, altitude or None if not found.
    """
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return None

        # Decode EXIF tags
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

        # Parse latitude
        lat = _dms_to_decimal(
            gps.get("GPSLatitude"),
            gps.get("GPSLatitudeRef", "N")
        )
        lon = _dms_to_decimal(
            gps.get("GPSLongitude"),
            gps.get("GPSLongitudeRef", "E")
        )

        if lat is None or lon is None:
            return None

        # Parse altitude (DJI stores as rational)
        altitude = None
        alt_raw = gps.get("GPSAltitude")
        if alt_raw:
            try:
                altitude = float(alt_raw)
            except Exception:
                altitude = 80.0  # default 80m

        return {
            "lat": lat,
            "lon": lon,
            "altitude": altitude or 80.0
        }

    except Exception:
        return None


def _dms_to_decimal(dms, ref) -> Optional[float]:
    """Convert DMS (degrees, minutes, seconds) to decimal degrees."""
    if dms is None:
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
    cx_rel: float,
    cy_rel: float,
    img_width: int,
    img_height: int,
    focal_length_mm: float = 4.5,
    sensor_width_mm: float = 6.17
) -> Dict:
    """
    Calculate approximate GPS coordinates of a detected victim.

    Uses Ground Sampling Distance (GSD) estimation:
    GSD = (sensor_width × altitude) / (focal_length × image_width)

    Default focal_length and sensor_width are for DJI Mini 2.
    Adjust for other drone models.

    Args:
        drone_lat/lon : GPS coordinates where photo was taken
        altitude_m    : Flight altitude in meters
        cx_rel/cy_rel : Relative position of victim (0–1) in image
        img_width/height : Image dimensions in pixels
        focal_length_mm  : Camera focal length (DJI Mini 2: 4.5mm)
        sensor_width_mm  : Camera sensor width (DJI Mini 2: 6.17mm)

    Returns:
        dict with lat, lon, accuracy_m
    """
    # Ground Sampling Distance in m/px
    gsd_x = (sensor_width_mm * altitude_m) / (focal_length_mm * img_width)
    gsd_y = gsd_x * (img_height / img_width)  # approximate

    # Pixel offset from image center to victim
    dx_px = (cx_rel - 0.5) * img_width
    dy_px = (cy_rel - 0.5) * img_height

    # Convert to meters
    dx_m = dx_px * gsd_x
    dy_m = dy_px * gsd_y

    # Convert to geographic offset
    # 1 degree latitude ≈ 111,320 m
    # 1 degree longitude ≈ 111,320 × cos(lat) m
    dlat = dy_m / 111320.0
    dlon = dx_m / (111320.0 * math.cos(math.radians(drone_lat)))

    victim_lat = drone_lat + dlat
    victim_lon = drone_lon + dlon

    # Accuracy estimate: ~GSD × detection box uncertainty (±5px)
    accuracy_m = round(gsd_x * 5, 1)

    return {
        "lat": victim_lat,
        "lon": victim_lon,
        "accuracy_m": accuracy_m
    }
