"""Classify, by changeset comment, the changesets that added
- roads in Tokachi in 2012 and 2013 (import of Yahoo! JAPAN / ALPS data,
  tracing from Bing imagery, other), and
- woods in 2010 (import of National Land Numerical Information, other).
Uses the cached ohsome responses from fetch_ohsome.py and the OSM API.

Writes scripts/roads_2012_2013_by_source.json and
scripts/woods_2010_by_source.json (no user names).
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fetch_ohsome as F  # noqa: E402
from shapely.geometry import Point  # noqa: E402


def inside(created, centroid):
    """Keep elements whose centroid lies inside the Tokachi outline."""
    return {k: v for k, v in created.items()
            if k in centroid and F.OUTLINE_P.contains(Point(*centroid[k]))}

IMPORT = re.compile(r"yahoo|alps|インポート|import", re.I)
BING = re.compile(r"bing", re.I)
KSJ = re.compile(r"National-Land Numerical Information|国土数値情報", re.I)


def kind(tags):
    text = " ".join(str(v) for v in tags.values())
    if IMPORT.search(text):
        return "yahoo_alps_import"
    if BING.search(text):
        return "bing_imagery"
    return "other"


def main():
    _, centroid, created = F.timelines("roads", "2026-07-27")
    created = inside(created, centroid)
    F.write_changesets("roads", created, {"2012", "2013"})  # the 25 largest, with comments
    out = {}
    for year in ("2012", "2013"):
        per_cs = Counter(cs for t, cs in created.values() if t[:4] == year)
        by_kind = defaultdict(lambda: {"ways": 0, "changesets": 0})
        for cs, n in per_cs.items():
            k = kind(F.osm_changeset(cs)["tags"])
            by_kind[k]["ways"] += n
            by_kind[k]["changesets"] += 1
        out[year] = {"waysAdded": sum(per_cs.values()), "changesets": len(per_cs), "byKind": by_kind}
        print(year, json.dumps(out[year]))
    (Path(__file__).parent / "roads_2012_2013_by_source.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))

    _, centroid, created = F.timelines("woods", "2026-07-27")
    created = inside(created, centroid)
    per_cs = Counter(cs for t, cs in created.values() if t[:4] == "2010")
    woods = {"elementsAdded": sum(per_cs.values()), "changesets": len(per_cs),
             "ksj_forest_import": 0, "other": 0, "comments": Counter()}
    for cs, n in per_cs.items():
        c = F.osm_changeset(cs)["tags"].get("comment", "")
        woods["ksj_forest_import" if KSJ.search(c) else "other"] += n
        if KSJ.search(c):
            woods["comments"][c] += n
    print("woods 2010", json.dumps(woods, ensure_ascii=False))
    (Path(__file__).parent / "woods_2010_by_source.json").write_text(
        json.dumps(woods, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
