#!/usr/bin/env python3
"""
Pre-download OSM tiles for offline demo.
Downloads tiles around a bounding box at specified zoom levels.

Usage:
  python scripts/precache_tiles.py --lat -7.34 --lon 110.45 --radius 5 --zoom 14-17
  python scripts/precache_tiles.py --lat -6.20 --lon 106.82 --radius 3 --zoom 10-16  # Jakarta
"""

import argparse
import math
import os
import sys
import time
import urllib.request
from pathlib import Path


TILE_CACHE_DIR = Path(__file__).parent.parent / "backend" / "tile_cache"
USER_AGENT = "RescueVision-Edge/1.0 (offline-tile-precache)"
TILE_SERVERS = ["a", "b", "c"]


def latlon_to_tile(lat, lon, zoom):
    """Convert lat/lon to tile x/y at given zoom level."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_latlon(x, y, zoom):
    """Convert tile x/y to NW corner lat/lon."""
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))
    return lat, lon


def download_tile(z, x, y, cache_dir, dry_run=False):
    """Download a single tile and save to cache."""
    cache_path = cache_dir / f"{z}_{x}_{y}.png"
    if cache_path.exists():
        return "cached"

    if dry_run:
        return "would_download"

    server = TILE_SERVERS[(x + y + z) % len(TILE_SERVERS)]
    url = f"https://{server}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        cache_path.write_bytes(data)
        return "ok"
    except Exception as e:
        return f"fail: {e}"


def main():
    parser = argparse.ArgumentParser(description="Pre-cache OSM tiles for offline use")
    parser.add_argument("--lat", type=float, required=True, help="Center latitude")
    parser.add_argument("--lon", type=float, required=True, help="Center longitude")
    parser.add_argument("--radius", type=float, default=3, help="Radius in km")
    parser.add_argument("--zoom", type=str, default="13-17", help="Zoom range, e.g. 10-16")
    parser.add_argument("--dry-run", action="store_true", help="Count tiles without downloading")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (seconds)")
    args = parser.parse_args()

    zoom_min, zoom_max = map(int, args.zoom.split("-"))
    cache_dir = TILE_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Approximate bounding box from center + radius
    lat_delta = args.radius / 111.32
    lon_delta = args.radius / (111.32 * math.cos(math.radians(args.lat)))

    lat_min = args.lat - lat_delta
    lat_max = args.lat + lat_delta
    lon_min = args.lon - lon_delta
    lon_max = args.lon + lon_delta

    print(f"Region: lat [{lat_min:.4f}, {lat_max:.4f}] lon [{lon_min:.4f}, {lon_max:.4f}]")
    print(f"Zoom range: {zoom_min}–{zoom_max}")
    print(f"Cache dir: {cache_dir}")
    if args.dry_run:
        print("DRY RUN — no downloads")
    print()

    total = 0
    downloaded = 0
    cached = 0
    failed = 0

    for zoom in range(zoom_min, zoom_max + 1):
        x_min, y_max = latlon_to_tile(lat_min, lon_min, zoom)
        x_max, y_min = latlon_to_tile(lat_max, lon_max, zoom)

        x_range = range(min(x_min, x_max), max(x_min, x_max) + 1)
        y_range = range(min(y_min, y_max), max(y_min, y_max) + 1)
        n_tiles = len(x_range) * len(y_range)
        total += n_tiles

        print(f"Zoom {zoom}: {len(x_range)}×{len(y_range)} = {n_tiles} tiles")

        if not args.dry_run:
            for y in y_range:
                for x in x_range:
                    result = download_tile(zoom, x, y, cache_dir, dry_run=False)
                    if result == "ok":
                        downloaded += 1
                    elif result == "cached":
                        cached += 1
                    else:
                        failed += 1
                    if downloaded % 50 == 0 and downloaded > 0:
                        print(f"  ... {downloaded} downloaded, {cached} cached, {failed} failed")
                    time.sleep(args.delay)

    print()
    print(f"Total tiles: {total}")
    print(f"Downloaded: {downloaded}")
    print(f"Already cached: {cached}")
    print(f"Failed: {failed}")
    if not args.dry_run:
        print(f"Cache size: ~{sum(f.stat().st_size for f in cache_dir.glob('*.png')) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
