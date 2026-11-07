"""Build the Tokachi Subprefecture outline from MLIT National Land Numerical
Information (N03, administrative areas).

Usage:
    python scripts/build_boundary.py path/to/N03-20240101_01_subprefecture.geojson

Writes:
    site/data/tokachi.geojson         outline for display
    site/data/hokkaido.geojson        land outline of Hokkaido (context only)
    scripts/tokachi_bpolys.geojson    simplified polygon sent to the ohsome API
"""
import json
import sys
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
NAME = "十勝総合振興局"


def rounded(geom, nd):
    def r(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], nd), round(c[1], nd)]
        return [r(x) for x in c]
    g = mapping(geom)
    return {"type": g["type"], "coordinates": r(g["coordinates"])}


def main(src):
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    polys = [shape(f["geometry"]) for f in data["features"]
             if f["properties"].get("N03_002") == NAME]
    merged = unary_union([p.buffer(0) for p in polys])
    parts = list(merged.geoms) if merged.geom_type == "MultiPolygon" else [merged]
    # keep the mainland area; drop tiny coastal islets
    main_part = max(parts, key=lambda p: p.area)
    outline = main_part.simplify(0.0004, preserve_topology=True)
    query = main_part.simplify(0.004, preserve_topology=True)
    query = type(query)(query.exterior)  # no holes for the API query

    out = {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "properties": {"name": "Tokachi", "name_ja": "十勝総合振興局",
                       "source": "MLIT National Land Numerical Information N03 (2024)"},
        "geometry": rounded(outline, 5)}]}
    (ROOT / "site/data/tokachi.geojson").write_text(json.dumps(out, separators=(",", ":")))
    q = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"id": "tokachi"},
        "geometry": rounded(query, 4)}]}
    (ROOT / "scripts/tokachi_bpolys.geojson").write_text(json.dumps(q, separators=(",", ":")))
    land = unary_union([shape(f["geometry"]).buffer(0) for f in data["features"]])
    land = [p for p in land.geoms if p.area > 0.002]
    land = [p.simplify(0.003, preserve_topology=True) for p in land]
    h = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": rounded(p, 4)} for p in land]}
    (ROOT / "site/data/hokkaido.geojson").write_text(json.dumps(h, separators=(",", ":")))
    print("parts", len(parts), "outline vertices", len(outline.exterior.coords),
          "query vertices", len(query.exterior.coords), "bounds", main_part.bounds)


if __name__ == "__main__":
    main(sys.argv[1])
