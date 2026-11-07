"""Fetch yearly OpenStreetMap history for Tokachi from the ohsome API (HeiGIT)
and write the data files used by the web map.

Usage:
    python scripts/fetch_ohsome.py            # everything
    python scripts/fetch_ohsome.py stats      # yearly statistics only
    python scripts/fetch_ohsome.py layers     # map layers only
    python scripts/fetch_ohsome.py roads      # one layer (roads, farmland or woods)

Requires: shapely. Responses are cached in scripts/.cache so the script can be
re-run without querying the API again (delete the folder to refresh).
"""
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape, mapping, box
from shapely.prepared import prep

API = "https://api.ohsome.org/v1"
ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "scripts/.cache"
OUT = ROOT / "site/data"
BPOLYS = (ROOT / "scripts/tokachi_bpolys.geojson").read_text()
AREA = shape(json.loads(BPOLYS)["features"][0]["geometry"])
AREA_P = prep(AREA)
# display outline (finer than the query polygon), used to clip map layers
OUTLINE = shape(json.loads((ROOT / "site/data/tokachi.geojson").read_text())["features"][0]["geometry"])
OUTLINE_P = prep(OUTLINE)

START = "2007-10-08"  # first timestamp of the ohsome history database

# chunk size (degrees) used to split history requests per layer
STEP = {"roads": 0.2, "buildings": 0.1, "farmland": 0.25, "woods": 0.25}

LAYERS = {
    "roads": "highway=* and type:way",
    "buildings": "building=* and geometry:polygon",
    "farmland": "landuse in (farmland, meadow, orchard) and geometry:polygon",
    "woods": "natural=tree_row or ((landuse=forest or natural=wood) and geometry:polygon)",
}


def post(endpoint, params, timeout=900, retries=4):
    key = hashlib.sha1((endpoint + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    body = urllib.parse.urlencode(params).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(f"{API}/{endpoint}", data=body, method="POST",
                                         headers={"User-Agent": "who-mapped-tokachi/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            CACHE.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data))
            return data
        except Exception as e:  # network errors, 5xx, timeouts
            wait = 10 * 2 ** i
            print(f"  ! {endpoint} failed ({e}); retry in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {endpoint}")


def latest_timestamp():
    req = urllib.request.Request(f"{API}/metadata", headers={"User-Agent": "who-mapped-tokachi/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        meta = json.loads(r.read())
    return meta["extractRegion"]["temporalExtent"]["toTimestamp"][:10]


def frames(latest):
    years = list(range(2008, int(latest[:4]) + 1))
    ts = [f"{y}-01-01" for y in years]
    if latest > ts[-1]:
        ts.append(latest)
    return ts


# ---------------------------------------------------------------- statistics

def stats(ts):
    tlist = ",".join(ts)
    out = {"timestamps": ts}
    r = post("elements/length", {"bpolys": BPOLYS, "time": tlist, "filter": LAYERS["roads"]})
    out["roadKm"] = [round(x["value"] / 1000, 1) for x in r["result"]]
    for name in ("buildings", "farmland", "woods"):
        r = post("elements/count", {"bpolys": BPOLYS, "time": tlist, "filter": LAYERS[name]})
        out[name] = [int(x["value"]) for x in r["result"]]
        print(name, out[name], flush=True)
    print("roadKm", out["roadKm"], flush=True)
    # people who edited ways (roads, buildings, land use, ...) in the 12 months
    # before each timestamp; nodes are excluded because the query over every
    # element type exceeds the API time limit for this area.
    users = [None]
    for a, b in zip(ts[:-1], ts[1:]):
        r = post("users/count", {"bpolys": BPOLYS, "time": f"{a},{b}", "filter": "type:way"})
        users.append(int(r["result"][0]["value"]))
        print("users", a, b, users[-1], flush=True)
    out["users"] = users
    r = post("users/count", {"bpolys": BPOLYS, "time": f"{START},{ts[0]}", "filter": "type:way"})
    out["users"][0] = int(r["result"][0]["value"])
    return out


# ---------------------------------------------------------------- map layers

def chunks(step=0.1):
    minx, miny, maxx, maxy = AREA.bounds
    y = miny
    while y < maxy:
        x = minx
        while x < maxx:
            b = box(x, y, min(x + step, maxx), min(y + step, maxy))
            if AREA_P.intersects(b):
                yield tuple(round(v, 4) for v in b.bounds)
            x += step
        y += step


def bbox_param(b):
    return ",".join(str(v) for v in b)


def timelines(layer, latest):
    """osmId -> sorted list of (timestamp, alive_after) and creation info."""
    events = defaultdict(dict)
    centroid = {}
    created_cs = {}
    for i, b in enumerate(chunks(STEP[layer])):
        r = post("contributions/centroid", {"bboxes": bbox_param(b), "time": f"{START},{latest}",
                                            "filter": LAYERS[layer], "properties": "metadata"})
        for f in r["features"]:
            p = f["properties"]
            oid = p["@osmId"]
            alive = not p.get("@deletion", False)
            events[oid][p["@timestamp"]] = alive
            if f.get("geometry") and alive:
                centroid[oid] = f["geometry"]["coordinates"]
            if p.get("@creation"):
                created_cs.setdefault(oid, (p["@timestamp"], p["@contributionChangesetId"]))
        print(f"  {layer} chunk {i} {b} -> {len(r['features'])}", flush=True)
    return {k: sorted(v.items()) for k, v in events.items()}, centroid, created_cs


def frame_span(ev, ts):
    """First and last frame index at which the element exists."""
    vis = []
    j = 0
    alive = False
    for k, t in enumerate(ts):
        stamp = t + "T23:59:59Z" if len(t) == 10 and k == len(ts) - 1 else t + "T00:00:00Z"
        while j < len(ev) and ev[j][0] <= stamp:
            alive = ev[j][1]
            j += 1
        if alive:
            vis.append(k)
    if not vis:
        return None
    return vis[0], vis[-1]


def rnd(c, nd=5):
    if isinstance(c[0], (int, float)):
        return [round(c[0], nd), round(c[1], nd)]
    return [rnd(x, nd) for x in c]


def geometries(layer, latest, ids_needed, tol, tags=None):
    geoms = defaultdict(list)
    props = "metadata,tags" if tags is not None else "metadata"
    for i, b in enumerate(chunks(STEP[layer])):
        r = post("contributions/latest/geometry", {"bboxes": bbox_param(b), "time": f"{START},{latest}",
                                                   "filter": LAYERS[layer], "properties": props})
        for f in r["features"]:
            oid = f["properties"]["@osmId"]
            if f.get("geometry") and oid in ids_needed:
                geoms[oid].append(f["geometry"])
                if tags is not None:
                    tags[oid] = f["properties"]
        print(f"  {layer} geometry chunk {i} -> {len(r['features'])}", flush=True)
    # elements deleted since: take their last geometry before deletion
    missing = sorted(i for i in ids_needed if i not in geoms)
    print(f"  {layer}: {len(missing)} deleted elements need older geometry", flush=True)
    minx, miny, maxx, maxy = AREA.bounds
    for s in range(0, len(missing), 150):
        batch = missing[s:s + 150]
        r = post("contributions/geometry", {"bboxes": f"{minx},{miny},{maxx},{maxy}",
                                            "time": f"{START},{latest}",
                                            "filter": f"({LAYERS[layer]}) and id:({','.join(batch)})",
                                            "properties": props})
        last = {}
        for f in r["features"]:
            if f.get("geometry"):
                oid = f["properties"]["@osmId"]
                t = f["properties"]["@timestamp"]
                if oid not in last or t >= last[oid][0]:
                    last[oid] = (t, f["geometry"])
        for oid, (_, g) in last.items():
            geoms[oid].append(g)
            if tags is not None:
                tags[oid] = next(f["properties"] for f in r["features"]
                                 if f["properties"]["@osmId"] == oid)
    out = {}
    for oid, parts in geoms.items():
        shapes = []
        for g in parts:
            try:
                s = shape(g)
            except Exception:
                continue
            if s.is_empty:
                continue
            s = s.simplify(tol, preserve_topology=True)
            if not s.is_empty and AREA_P.intersects(s):
                shapes.append(s)
        if shapes:
            out[oid] = shapes
    return out


ROAD_CLASS = {
    "motorway": 0, "trunk": 0, "primary": 0, "motorway_link": 0, "trunk_link": 0, "primary_link": 0,
    "secondary": 1, "tertiary": 1, "secondary_link": 1, "tertiary_link": 1,
}


def singles(shapes):
    """Split multi-part and mixed geometries into single LineStrings / Polygons."""
    for s in shapes:
        if hasattr(s, "geoms"):
            yield from singles(s.geoms)
        elif s.geom_type in ("LineString", "Polygon") and not s.is_empty:
            yield s


def road_class(tags):
    hw = tags.get("highway", "")
    if hw in ROAD_CLASS:
        return ROAD_CLASS[hw]
    if hw in ("track", "path", "footway", "cycleway", "bridleway", "steps", "pedestrian"):
        return 3
    return 2


def write_lines(layer, ts, latest, tol):
    ev, centroid, created = timelines(layer, latest)
    spans = {oid: frame_span(e, ts) for oid, e in ev.items()}
    spans = {k: v for k, v in spans.items() if v}
    tags = {} if layer == "roads" else None
    geoms = geometries(layer, latest, set(spans), tol, tags)
    feats = []
    for oid, shapes in geoms.items():
        a, z = spans[oid]
        props = {"a": a}
        if z < len(ts) - 1:
            props["z"] = z
        if layer == "roads":
            props["c"] = road_class(tags.get(oid, {}))
        clipped = [s if OUTLINE_P.contains(s) else s.intersection(OUTLINE) for s in shapes]
        for s in singles(clipped):
            m = mapping(s)
            feats.append({"type": "Feature", "properties": props,
                          "geometry": {"type": m["type"], "coordinates": rnd(m["coordinates"])}})
    fc = {"type": "FeatureCollection", "features": feats}
    (OUT / f"{layer}.geojson").write_text(json.dumps(fc, separators=(",", ":")))
    print(f"{layer}: {len(geoms)} elements, {len(feats)} features", flush=True)
    return ev, created


def write_roads(ts, latest):
    return write_lines("roads", ts, latest, 0.00003)


GRID = (0.025, 0.018)  # building grid cell, degrees lon x lat (about 2 km)


def write_buildings(ts, latest):
    """Building counts per grid cell at every frame (elements/count/groupBy/boundary)."""
    dx, dy = GRID
    minx, miny, maxx, maxy = AREA.bounds
    cells = []
    y = miny
    while y < maxy:
        x = minx
        while x < maxx:
            b = box(x, y, x + dx, y + dy)
            if AREA_P.intersects(b):
                cells.append(tuple(round(v, 4) for v in b.bounds))
            x += dx
        y += dy
    rows = []
    for s in range(0, len(cells), 300):
        batch = cells[s:s + 300]
        bb = "|".join(f"c{s + i}:{bbox_param(b)}" for i, b in enumerate(batch))
        r = post("elements/count/groupBy/boundary",
                 {"bboxes": bb, "time": ",".join(ts), "filter": LAYERS["buildings"]})
        for g in r["groupByResult"]:
            i = int(g["groupByObject"][1:])
            counts = [int(v["value"]) for v in g["result"]]
            if any(counts):
                b = cells[i]
                rows.append([round((b[0] + b[2]) / 2, 4), round((b[1] + b[3]) / 2, 4), counts])
        print(f"  buildings grid {s + len(batch)}/{len(cells)}", flush=True)
    (OUT / "buildings.json").write_text(json.dumps(
        {"cell": [dx, dy], "rows": rows}, separators=(",", ":")))
    print(f"buildings: {len(rows)} non-empty cells, total now {sum(r[2][-1] for r in rows)}", flush=True)


def changeset_summary(created, years, top=25):
    """Changesets that added the most elements in the given years."""
    counts = defaultdict(int)
    for oid, (t, cs) in created.items():
        if t[:4] in years:
            counts[cs] += 1
    total = sum(counts.values())
    rows = sorted(counts.items(), key=lambda kv: -kv[1])[:top]
    return total, rows


def osm_changeset(cs):
    path = CACHE / f"changeset_{cs}.json"
    if path.exists():
        return json.loads(path.read_text())
    req = urllib.request.Request(f"https://api.openstreetmap.org/api/0.6/changeset/{cs}.json",
                                 headers={"User-Agent": "who-mapped-tokachi/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())["changeset"]
    keep = {"id": d["id"], "created_at": d.get("created_at"), "changes_count": d.get("changes_count"),
            "tags": d.get("tags", {})}  # user names are deliberately not stored
    path.write_text(json.dumps(keep, ensure_ascii=False))
    time.sleep(1)
    return keep


def write_changesets(name, created, years):
    total, rows = changeset_summary(created, years)
    out = {"layer": name, "years": sorted(years), "elementsAdded": total, "changesets": []}
    for cs, n in rows:
        meta = osm_changeset(cs)
        meta["elementsAddedInArea"] = n
        out["changesets"].append(meta)
    path = ROOT / f"scripts/changesets_{name}_{min(years)}_{max(years)}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"wrote {path.name}", flush=True)


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(parents=True, exist_ok=True)
    latest = latest_timestamp()
    ts = frames(latest)
    print("frames", ts, flush=True)
    if what in ("all", "stats"):
        s = stats(ts)
        (OUT / "stats.json").write_text(json.dumps(s, separators=(",", ":")))
    if what in ("all", "layers"):
        write_roads(ts, latest)
        write_buildings(ts, latest)
        write_lines("farmland", ts, latest, 0.0001)
        write_lines("woods", ts, latest, 0.0001)
    if what in LAYERS and what != "buildings":
        write_lines(what, ts, latest, 0.00003 if what == "roads" else 0.0001)


if __name__ == "__main__":
    main()
