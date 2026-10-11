"""Local Sovereign Air-Gapped Tactical Tile Service for Project Rakshak 2.0.

Provides 100% offline, zero-network-egress map tiles for Leaflet.
Generates dynamic 256x256 C4ISR seamless tactical basemap tiles:
  1. 'basemap' (alias 'satellite', 'offline'):
     Dark navy ocean, muted green-brown land, subtle coastline glow.
  2. 'dark' (alias 'tactical'):
     Near-black ocean, grey land, thin cyan graticule.
  3. 'terrain' (alias 'bathymetry'):
     Light slate-blue ocean, tan-to-green land with soft elevation-style shading
     (labeled: "(synthetic, not real elevation)").

Zero external network calls (no ArcGIS, no OSM, no Mapbox, no CDN).
"""
from __future__ import annotations
import io
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def _tile_to_bbox(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Convert Web Mercator tile (z, x, y) to (lon_min, lat_min, lon_max, lat_max)."""
    n = 2.0 ** z
    lon_min = (x / n) * 360.0 - 180.0
    lon_max = ((x + 1) / n) * 360.0 - 180.0

    lat_rad_top = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    lat_max = math.degrees(lat_rad_top)

    lat_rad_bot = math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y + 1) / n)))
    lat_min = math.degrees(lat_rad_bot)

    return (lon_min, lat_min, lon_max, lat_max)


def _latlon_to_tile_px(lat: float, lon: float, z: int, x: int, y: int) -> Tuple[float, float]:
    """Project (lat, lon) to tile-local pixel coordinate (px, py) in [0, 256]."""
    n = 2.0 ** z
    world_x = ((lon + 180.0) / 360.0) * n
    px = (world_x - x) * 256.0

    lat_clamped = min(85.0511, max(-85.0511, lat))
    lat_rad = math.radians(lat_clamped)
    merc_y = (1.0 - math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0)) / math.pi) / 2.0
    world_y = merc_y * n
    py = (world_y - y) * 256.0
    return (px, py)


# Peninsular India Coastline points [lat, lon] from offlineGeoData.ts
INDIA_COASTLINE: List[Tuple[float, float]] = [
    (23.85, 68.10), (23.50, 68.30), (23.10, 68.70), (22.80, 69.10), (22.50, 69.80),
    (22.40, 70.30), (22.90, 70.60), (22.50, 70.90), (21.80, 70.20), (21.10, 70.80),
    (20.75, 71.50), (21.50, 72.20), (21.75, 72.50), (21.20, 72.85),
    (20.50, 72.75), (19.80, 72.70), (19.35, 72.80), (18.95, 72.82), (18.50, 72.95),
    (17.80, 73.10), (17.00, 73.25), (16.50, 73.35),
    (15.80, 73.65), (15.25, 73.90), (14.80, 74.12), (14.20, 74.35), (13.60, 74.65),
    (13.00, 74.80), (12.50, 74.95),
    (11.80, 75.30), (11.20, 75.80), (10.50, 76.00), (9.95, 76.25), (9.30, 76.50),
    (8.80, 76.65), (8.40, 76.95),
    (8.08, 77.55),
    (8.40, 78.10), (8.80, 78.15), (9.20, 79.15), (9.45, 79.30), (9.90, 79.20),
    (10.30, 79.85), (10.80, 79.85), (11.50, 79.80), (12.20, 80.00), (13.08, 80.28),
    (13.50, 80.20),
    (14.20, 80.10), (15.20, 80.05), (15.80, 80.40), (16.30, 81.30), (16.80, 82.20),
    (17.20, 82.70), (17.70, 83.30), (18.30, 84.00), (19.00, 84.80),
    (19.70, 85.80), (20.20, 86.70), (20.80, 87.00), (21.50, 87.40), (21.80, 88.00),
    (21.60, 88.80), (21.80, 89.20)
]

# Sri Lanka Coastline [lat, lon] from offlineGeoData.ts
SRI_LANKA_COASTLINE: List[Tuple[float, float]] = [
    (9.80, 80.20), (9.30, 79.90), (8.80, 79.80), (8.20, 79.80), (7.50, 79.85),
    (6.95, 79.85), (6.40, 80.00), (5.92, 80.45), (5.95, 80.60), (6.25, 81.10),
    (6.80, 81.85), (7.70, 81.70), (8.55, 81.25), (9.20, 80.90), (9.60, 80.40),
    (9.80, 80.20)
]

# Closed Peninsular India polygon
INDIA_LAND_POLYGON: List[Tuple[float, float]] = list(INDIA_COASTLINE) + [
    (24.0, 89.0), (26.0, 89.0), (27.5, 88.5), (28.5, 84.0), (30.5, 81.0),
    (32.5, 76.0), (34.5, 75.0), (35.0, 74.0), (32.0, 74.0), (30.0, 72.0),
    (27.0, 70.0), (24.5, 68.8), (23.85, 68.10)
]

# Preloaded Land Polygons with Bounding Boxes
_LAND_POLYGONS: List[Dict] = []

def _init_land_polygons():
    """Load world land geometry and high-resolution sovereign coastlines."""
    global _LAND_POLYGONS
    if _LAND_POLYGONS:
        return

    # 1. High-resolution sovereign Indian Peninsula and Sri Lanka
    for poly_pts in [INDIA_LAND_POLYGON, SRI_LANKA_COASTLINE]:
        lats = [pt[0] for pt in poly_pts]
        lons = [pt[1] for pt in poly_pts]
        _LAND_POLYGONS.append({
            'bbox': (min(lons), min(lats), max(lons), max(lats)),
            'coords': poly_pts
        })

    # 2. Continental world land polygons from world_land.json
    possible_paths = [
        Path(__file__).resolve().parent.parent.parent / 'frontend' / 'src' / 'world_land.json',
        Path('frontend/src/world_land.json'),
        Path('DEF/frontend/src/world_land.json')
    ]
    for p in possible_paths:
        if p.exists():
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for feat in data.get('features', []):
                    coords = feat.get('geometry', {}).get('coordinates', [])
                    if coords:
                        ring = coords[0]
                        poly_lats = [pt[1] for pt in ring]
                        poly_lons = [pt[0] for pt in ring]
                        _LAND_POLYGONS.append({
                            'bbox': (min(poly_lons), min(poly_lats), max(poly_lons), max(poly_lats)),
                            'coords': [(pt[1], pt[0]) for pt in ring]
                        })
                break
            except Exception:
                pass

_init_land_polygons()


# In-memory LRU cache holding pre-rendered PNG tiles
_TILE_CACHE: Dict[Tuple[str, int, int, int], bytes] = {}
_MAX_CACHE_SIZE = 4096

# Hypsometric elevation color bands for 'terrain' (lowland green to upland warm tan/buff)
_HYPSO_PALETTE = np.array([
    [78, 108, 74],    # Band 0: Coastal plains & delta lowlands (soft muted green)
    [106, 126, 82],   # Band 1: River basins & agricultural plains (olive/sage green)
    [142, 138, 98],   # Band 2: Deccan plateau & semi-arid uplands (light olive-tan)
    [165, 148, 112],  # Band 3: Ghats & central highlands (warm tan)
    [180, 158, 126],  # Band 4: Mountain slopes & escarpments (golden/sand tan)
    [195, 178, 152]   # Band 5: High altitude peaks & passes (light buff-stone)
], dtype=np.uint8)


def get_offline_tile(style: str, z: int, x: int, y: int) -> bytes:
    """Generate or retrieve a cached 256x256 sovereign C4ISR tactical map tile."""
    raw_style = style.lower().strip()
    # Normalize style aliases
    if raw_style in ('satellite', 'offline', 'basemap', 'default'):
        normalized_style = 'basemap'
    elif raw_style in ('dark', 'tactical'):
        normalized_style = 'dark'
    elif raw_style in ('terrain', 'bathymetry'):
        normalized_style = 'terrain'
    else:
        normalized_style = 'basemap'

    cache_key = (normalized_style, z, x, y)
    if cache_key in _TILE_CACHE:
        return _TILE_CACHE[cache_key]

    # Validate coordinate boundaries
    max_idx = (2 ** z) - 1
    x = max(0, min(x, max_idx))
    y = max(0, min(y, max_idx))

    bbox = _tile_to_bbox(z, x, y)
    lon_min, lat_min, lon_max, lat_max = bbox

    # 1. Determine base styling parameters
    coast_glow_stroke = None
    if normalized_style == 'basemap':
        # Style 1: Satellite-style (synthetic basemap)
        # Dark navy ocean, muted green-brown land, subtle coastline glow
        bg_color = (10, 24, 42)          # Dark navy ocean
        land_color = (50, 62, 42)        # Muted green-brown land
        coast_stroke = (72, 135, 148)    # Core coastline boundary stroke
        coast_glow_stroke = (28, 70, 85) # Subtle coastline glow
        grid_color = (18, 36, 58)        # Geodetic MGRS graticule
        coast_width = 1
    elif normalized_style == 'dark':
        # Style 2: Dark tactical (synthetic)
        # Near-black ocean, grey land, thin cyan graticule
        bg_color = (6, 8, 12)            # Near-black ocean
        land_color = (34, 38, 44)        # Grey land
        coast_stroke = (0, 230, 255)     # Thin tactical cyan coastline
        grid_color = (0, 175, 200)       # Thin cyan graticule
        coast_width = 1
    else:
        # Style 3: Offline terrain (synthetic)
        # Light slate-blue ocean, tan-to-green land with soft elevation-style shading
        bg_color = (52, 82, 110)         # Light slate-blue ocean
        land_color = (106, 126, 82)      # Base tan-to-green lowland tint
        coast_stroke = (75, 105, 125)    # Soft shelf boundary stroke
        grid_color = (65, 96, 124)       # Muted slate coordinate mesh
        coast_width = 1

    # 2. Render Land Polygons into Mask
    mask_img = Image.new('L', (256, 256), 0)
    mask_draw = ImageDraw.Draw(mask_img)

    margin = 2.0  # degrees margin for polygon bounding box intersection
    has_land = False
    coastal_lines: List[List[Tuple[float, float]]] = []

    for poly in _LAND_POLYGONS:
        p_lon_min, p_lat_min, p_lon_max, p_lat_max = poly['bbox']
        if not (p_lon_max < lon_min - margin or p_lon_min > lon_max + margin or
                p_lat_max < lat_min - margin or p_lat_min > lat_max + margin):
            pts = [_latlon_to_tile_px(lat, lon, z, x, y) for lat, lon in poly['coords']]
            if len(pts) >= 3:
                mask_draw.polygon(pts, fill=255)
                has_land = True
                coastal_lines.append(pts)

    land_mask = np.array(mask_img) > 0

    # 3. Assemble RGB Tile Canvas
    if normalized_style == 'terrain' and has_land:
        # Compute procedural continuous hypsometric elevation bands on land
        n = 2.0 ** z
        px_idx = np.arange(256, dtype=np.float32)
        py_idx = np.arange(256, dtype=np.float32)
        lons = lon_min + (px_idx / 256.0) * (lon_max - lon_min)
        merc_y = (y + py_idx / 256.0) / n
        lats = np.degrees(2.0 * np.arctan(np.exp(np.pi * (1.0 - 2.0 * merc_y))) - np.pi / 2.0)

        lon_grid, lat_grid = np.meshgrid(lons, lats)

        # Procedural elevation function (continuous across adjacent tiles)
        h = (0.45 * (lat_grid - 6.0) / 28.0 +
             0.30 * (np.sin(lat_grid * 0.3) * np.cos(lon_grid * 0.25) + 1.0) / 2.0 +
             0.25 * (np.sin(lat_grid * 1.1 + lon_grid * 0.7) + 1.0) / 2.0)
        h = np.clip(h, 0.0, 0.999)
        band_indices = (h * 6).astype(np.int32)
        hypso_colors = _HYPSO_PALETTE[band_indices]

        tile_rgb = np.full((256, 256, 3), bg_color, dtype=np.uint8)
        tile_rgb[land_mask] = hypso_colors[land_mask]
        img = Image.fromarray(tile_rgb)
    else:
        img = Image.new('RGB', (256, 256), color=bg_color)
        if has_land:
            # Fill landmass with style's distinct tone
            land_img = Image.new('RGB', (256, 256), color=land_color)
            img.paste(land_img, mask=mask_img)

    draw = ImageDraw.Draw(img)

    # 4. Draw Coastline Strokes
    if has_land and coastal_lines:
        for pts in coastal_lines:
            if coast_glow_stroke:
                draw.line(pts, fill=coast_glow_stroke, width=3)
            draw.line(pts, fill=coast_stroke, width=coast_width)

    # 5. Draw Geodetic Graticule Lines (MGRS Military Grid) seamlessly
    if z <= 3:
        deg_step = 20.0
    elif z <= 6:
        deg_step = 10.0
    elif z <= 9:
        deg_step = 2.0
    elif z <= 12:
        deg_step = 0.5
    else:
        deg_step = 0.1

    # Longitude vertical grid lines
    first_lon = math.floor(lon_min / deg_step) * deg_step
    curr_lon = first_lon
    while curr_lon <= lon_max + deg_step:
        if lon_min <= curr_lon <= lon_max and lon_max > lon_min:
            px = ((curr_lon - lon_min) / (lon_max - lon_min)) * 256.0
            draw.line([(px, 0), (px, 256)], fill=grid_color, width=1)
        curr_lon += deg_step

    # Latitude horizontal grid lines
    n = 2.0 ** z
    first_lat = math.floor(lat_min / deg_step) * deg_step
    curr_lat = first_lat
    while curr_lat <= lat_max + deg_step:
        if lat_min <= curr_lat <= lat_max:
            lat_clamped = min(85.0511, max(-85.0511, curr_lat))
            lat_rad = math.radians(lat_clamped)
            merc_y = (1.0 - math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0)) / math.pi) / 2.0
            py = (merc_y * n - y) * 256.0
            if 0 <= py <= 256:
                draw.line([(0, py), (256, py)], fill=grid_color, width=1)
        curr_lat += deg_step

    # 6. Watermark for synthetic terrain
    if normalized_style == 'terrain' and z <= 6:
        try:
            font = ImageFont.load_default()
            draw.text((6, 242), "(synthetic, not real elevation)", fill=(190, 215, 230), font=font)
        except Exception:
            pass

    # 7. Encode to PNG buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    tile_bytes = buf.getvalue()

    # Cache management
    if len(_TILE_CACHE) >= _MAX_CACHE_SIZE:
        to_del = list(_TILE_CACHE.keys())[:1024]
        for k in to_del:
            _TILE_CACHE.pop(k, None)

    _TILE_CACHE[cache_key] = tile_bytes
    return tile_bytes
