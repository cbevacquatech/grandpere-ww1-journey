#!/usr/bin/env python3
"""Convert Natural Earth countries GeoJSON into a browser-loadable local file."""

import json
import sys
from pathlib import Path


if len(sys.argv) != 2:
    raise SystemExit("usage: generate_offline_basemap.py PATH_TO_COUNTRIES_GEOJSON")

source = Path(sys.argv[1])
destination = Path(__file__).resolve().parent / "vendor" / "offline_countries.js"
data = json.loads(source.read_text(encoding="utf-8"))

# Retain only the fields used for map labels, reducing the embedded file size.
for feature in data.get("features", []):
    props = feature.get("properties", {})
    feature["properties"] = {"name": props.get("NAME") or props.get("ADMIN") or ""}

destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(
    "const OFFLINE_COUNTRIES=" + json.dumps(data, separators=(",", ":")) + ";\n",
    encoding="utf-8",
)
print(destination)
