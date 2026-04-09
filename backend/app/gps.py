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

        # Detect GPS method — 'network' means cell tower/WiFi (ASL altitude, not AGL)
        gps_method = gps.get("GPSProcessingMethod", "")
        if isinstance(gps_method, bytes):
            gps_method = gps_method.decode("utf-8", errors="ignore")
        gps_method = gps_method.strip().lower()
        is_network_gps = gps_method in ("network", "wlan", "wifi", "cell")

        if is_network_gps:
            logger.warning(
                "[EXIF] GPSProcessingMethod='%s' — altitude from EXIF is ASL (above sea level), "
                "NOT flight altitude (AGL). Will NOT use for GSD calculation to avoid wrong coordinates.",
                gps_method
            )

        # Parse altitude
        altitude = None
        altitude_is_agl = not is_network_gps  # network GPS = ASL, drone GPS = AGL
        alt_raw = gps.get("GPSAltitude")
        if alt_raw is not None:
            parsed_alt = _convert_to_float(alt_raw)
            if parsed_alt is not None:
                altitude = parsed_alt
                if is_network_gps:
                    logger.debug(
                        "[EXIF] GPSAltitude raw=%.2f m (ASL — ignored for GSD, fallback to manual/default)",
                        altitude
                    )
                else:
                    logger.debug("[EXIF] GPSAltitude parsed: %.2f m (AGL — will use for GSD)", altitude)
            else:
                logger.warning("[EXIF] Could not parse GPSAltitude (%s) — using default 80m", alt_raw)
                altitude = 80.0
        else:
            logger.debug("[EXIF] GPSAltitude not present — using default 80m")

        # Focal length (optional, for GSD calculation)
        focal_length = decoded.get("FocalLength", 4.5)
        if isinstance(focal_length, tuple):
            focal_length = float(focal_length[0]) / float(focal_length[1])

        # Heading (GPSImgDirection)
        heading = _convert_to_float(gps.get("GPSImgDirection"))
        if heading is None:
            # Try to find DJI specific FlightYawDegree in all tags (often as a string)
            for k, v in decoded.items():
                if "FlightYawDegree" in str(k) or "GimbalYawDegree" in str(k):
                    try:
                        heading = float(v)
                        break
                    except:
                        continue

        result = {
            "lat": lat,
            "lon": lon,
            "altitude": altitude or 80.0,
            "altitude_is_agl": altitude_is_agl,
            "gps_method": gps_method or "gps",
            "focal_length": float(focal_length),
            "heading": heading
        }
        logger.info(
            "[EXIF] GPS extracted: lat=%.6f lon=%.6f alt=%.1fm (agl=%s method=%s) focal=%.2fmm heading=%s",
            lat, lon, result["altitude"], altitude_is_agl, result["gps_method"], result["focal_length"], heading
        )
        return result

    except Exception as e:
        logger.error("[EXIF] Unexpected error reading EXIF from %s: %s", image_path, e, exc_info=True)
        return None


def _convert_to_float(val) -> Optional[float]:
    """Helper to convert Pillow Rational or tuple to float."""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if hasattr(val, "numerator") and hasattr(val, "denominator"):
            return float(val.numerator) / float(val.denominator)
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return float(val[0]) / float(val[1])
        return float(val)
    except (ZeroDivisionError, TypeError, ValueError):
        return None


def _dms_to_decimal(dms, ref) -> Optional[float]:
    """Convert DMS (degrees, minutes, seconds) to decimal degrees."""
    if dms is None or not isinstance(dms, (list, tuple)) or len(dms) < 3:
        return None
    try:
        degrees = _convert_to_float(dms[0])
        minutes = _convert_to_float(dms[1])
        seconds = _convert_to_float(dms[2])
        
        if degrees is None or minutes is None or seconds is None:
            return None
            
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
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
    sensor_width: float = 6.17,
    heading: Optional[float] = None
) -> Dict:
    """
    Calculate victim coordinates using GSD and optional rotation from heading.
    """
    # 1. GSD Calculation (meters per pixel)
    gsd = (sensor_width * altitude_m) / (focal_length * img_width)

    # 2. Pixel Offset from image center
    # Image center is (img_width/2, img_height/2)
    # dx_px: right is positive
    # dy_px: up is positive (image Y increases downwards, so we negate)
    dx_px = bbox_cx - (img_width / 2.0)
    dy_px = (img_height / 2.0) - bbox_cy

    # 3. Offsets in Meters (relative to drone heading)
    # If heading=0, dx_m is East, dy_m is North
    dx_m_local = dx_px * gsd
    dy_m_local = dy_px * gsd

    # 4. Global Rotation based on Heading
    # Most drone heading is degrees from True North (0=N, 90=E, 180=S, 270=W)
    if heading is not None:
        theta = math.radians(heading)
        # Rotation Matrix:
        # dx_global = dx_local*cos(theta) + dy_local*sin(theta)
        # dy_global = -dx_local*sin(theta) + dy_local*cos(theta)
        # Wait, if heading 0=North, dx_local=0, dy_local=1 => dx_global=0, dy_global=1 (Correct)
        # If heading 90=East, dx_local=0, dy_local=1 => dx_global=1, dy_global=0 (Correct)
        # Standard 2D rotation for East/North offsets:
        dx_m = dx_m_local * math.cos(theta) + dy_m_local * math.sin(theta)
        dy_m = -dx_m_local * math.sin(theta) + dy_m_local * math.cos(theta)
    else:
        dx_m = dx_m_local
        dy_m = dy_m_local

    # 5. Final GPS Coordinate
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
