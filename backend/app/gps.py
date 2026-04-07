"""
RescueVision Edge — GPS Utilities
Reads EXIF GPS from DJI photos and calculates victim ground coordinates
"""

import math
import logging
from typing import Optional, Dict
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)


def extract_exif_gps(image_path: str) -> Optional[Dict]:
    """
    Extract GPS metadata from DJI drone photo EXIF.
    Returns dict with lat, lon, altitude, and focal length.
    """
    logger.debug("[EXIF] Opening file: %s", image_path)
    try:
        img = Image.open(image_path)
        logger.debug("[EXIF] Image format=%s mode=%s size=%s", img.format, img.mode, img.size)

        exif_data = img._getexif()
        if not exif_data:
            logger.warning("[EXIF] No EXIF data found in file — image may have been stripped by gallery/browser")
            return None

        decoded = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            decoded[tag] = value

        all_tags = [k for k in decoded.keys()]
        logger.debug("[EXIF] All EXIF tags present (%d): %s", len(all_tags), all_tags)

        gps_info_raw = decoded.get("GPSInfo")
        if not gps_info_raw:
            logger.warning(
                "[EXIF] GPSInfo tag missing — file has EXIF but no GPS block. "
                "Likely stripped by mobile gallery or privacy setting. "
                "Tags found: %s", all_tags
            )
            return None

        gps = {}
        for key, val in gps_info_raw.items():
            gps[GPSTAGS.get(key, key)] = val

        logger.debug("[EXIF] Raw GPS tags: %s", {k: str(v) for k, v in gps.items()})

        # Parse latitude and longitude
        lat_raw = gps.get("GPSLatitude")
        lat_ref = gps.get("GPSLatitudeRef", "N")
        lon_raw = gps.get("GPSLongitude")
        lon_ref = gps.get("GPSLongitudeRef", "E")

        logger.debug("[EXIF] GPSLatitude=%s ref=%s | GPSLongitude=%s ref=%s",
                     lat_raw, lat_ref, lon_raw, lon_ref)

        lat = _dms_to_decimal(lat_raw, lat_ref)
        lon = _dms_to_decimal(lon_raw, lon_ref)

        if lat is None or lon is None:
            logger.warning("[EXIF] DMS parse failed — lat=%s lon=%s (raw: %s %s)", lat, lon, lat_raw, lon_raw)
            return None

        # Parse altitude
        altitude = None
        alt_raw = gps.get("GPSAltitude")
        if alt_raw:
            try:
                altitude = float(alt_raw)
                logger.debug("[EXIF] GPSAltitude parsed: %.2f m", altitude)
            except Exception as e:
                logger.warning("[EXIF] Could not parse GPSAltitude (%s): %s — using default 80m", alt_raw, e)
                altitude = 80.0
        else:
            logger.debug("[EXIF] GPSAltitude not present — using default 80m")

        # Focal length (optional, for GSD calculation)
        focal_length = decoded.get("FocalLength", 4.5)
        if isinstance(focal_length, tuple):
            focal_length = float(focal_length[0]) / float(focal_length[1])

        result = {
            "lat": lat,
            "lon": lon,
            "altitude": altitude or 80.0,
            "focal_length": float(focal_length)
        }
        logger.info("[EXIF] GPS extracted successfully: lat=%.6f lon=%.6f alt=%.1fm focal=%.2fmm",
                    lat, lon, result["altitude"], result["focal_length"])
        return result

    except Exception as e:
        logger.error("[EXIF] Unexpected error reading EXIF from %s: %s", image_path, e, exc_info=True)
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
