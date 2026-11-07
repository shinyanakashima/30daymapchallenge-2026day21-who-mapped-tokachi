"""Classify the changesets that added roads in Tokachi in 2012 and 2013 by
their comment (import of Yahoo! JAPAN / ALPS data, tracing from Bing imagery,
other). Uses the cached ohsome responses from fetch_ohsome.py and the OSM API.

Writes scripts/roads_2012_2013_by_source.json (no user names).
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fetch_ohsome as F  # noqa: E402

IMPORT = re.compile(r"yahoo|alps|インポート|import", re.I)
BING = re.compile(r"bing", re.I)


def kind(tags):
    text = " ".join(str(v) for v in tags.values())
    if IMPORT.search(text):
        return "yahoo_alps_import"
    if BING.search(text):
        return "bing_imagery"
    return "other"


def main():
    _, _, created = F.timelines("roads", "2026-07-27")
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


if __name__ == "__main__":
    main()
