#!/usr/bin/env python3
"""Generate a standalone SVG map of the narrator's journey.

Uses only Python's standard library. Pass a Natural Earth countries GeoJSON as
the optional first argument; without it the route still renders on a blank map.
"""

from __future__ import annotations

import html
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "narrator_journey_map.svg"
GEOJSON = Path(sys.argv[1]) if len(sys.argv) > 1 else None


EUROPE = (-13.0, 36.0, 31.0, 58.5)
ATLANTIC = (-80.0, 35.0, 31.0, 58.5)
NYNJ = (-74.35, 40.08, -73.65, 41.02)


def project(lon: float, lat: float, bounds, box):
    west, south, east, north = bounds
    x0, y0, width, height = box
    x = x0 + (lon - west) / (east - west) * width
    # Equirectangular projection is sufficient for this explanatory route map.
    y = y0 + (north - lat) / (north - south) * height
    return x, y


def fmt(value: float) -> str:
    return f"{value:.1f}"


def geo_paths(data, bounds, box):
    west, south, east, north = bounds
    paths = []
    for feature in data.get("features", []):
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates", [])
        polygons = [coords] if geom.get("type") == "Polygon" else coords if geom.get("type") == "MultiPolygon" else []
        for rings in polygons:
            for ring in rings:
                visible = [(lon, lat) for lon, lat in ring if west - 5 <= lon <= east + 5 and south - 5 <= lat <= north + 5]
                if len(visible) < 2:
                    continue
                pts = [project(lon, lat, bounds, box) for lon, lat in visible]
                paths.append("M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + " Z")
    return paths


def line(points, bounds, box):
    xy = [project(lon, lat, bounds, box) for lon, lat in points]
    return "M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in xy)


def marker(number, name, lon, lat, bounds, box, dx=10, dy=-10, uncertain=False, anchor="start"):
    x, y = project(lon, lat, bounds, box)
    cls = "uncertain" if uncertain else "certain"
    label = html.escape(name)
    return (
        f'<g class="stop {cls}"><circle cx="{fmt(x)}" cy="{fmt(y)}" r="9"/>'
        f'<text class="num" x="{fmt(x)}" y="{fmt(y + 3.5)}">{number}</text>'
        f'<text class="label" x="{fmt(x + dx)}" y="{fmt(y + dy)}" text-anchor="{anchor}">{label}</text></g>'
    )


def main():
    data = {"features": []}
    if GEOJSON and GEOJSON.exists():
        data = json.loads(GEOJSON.read_text(encoding="utf-8"))

    eu_box = (55, 125, 760, 420)
    at_box = (55, 670, 760, 160)
    ny_box = (865, 125, 580, 420)

    # Coordinates represent named places or deliberately broad approximation points.
    europe_stops = [
        (1, "Alsace home area", 7.35, 48.30, True),
        (2, "Strasbourg", 7.752, 48.573, False),
        (3, "German–Polish border training", 19.50, 53.30, True),
        (4, "Tilsit / Sovetsk", 21.883, 55.083, False),
        (5, "Russian territory / winter front", 24.80, 55.40, True),
        (6, "Radviliškis?", 23.55, 55.81, True),
        (7, "Galicia front", 24.00, 49.20, True),
        (8, "Silesia hospital & recovery", 17.00, 51.00, True),
        (9, "Marienburg / Malbork?", 19.03, 54.04, True),
        (10, "Königsberg / Kaliningrad?", 20.51, 54.71, True),
        (11, "Berlin", 13.405, 52.52, False),
        (12, "Wiesbaden", 8.24, 50.08, False),
        (13, "Strasbourg & home", 7.752, 48.573, False),
        (14, "Paris", 2.352, 48.857, False),
    ]
    # Story order: hospital transfers can double back geographically.
    europe_route = [(s[2], s[3]) for s in europe_stops]

    ny_stops = [
        (16, "Manhattan arrival / 49th St.", -73.970, 40.755, False),
        (17, "375 Park Avenue", -73.972, 40.759, False),
        (18, "Welfare Island hospital", -73.949, 40.758, False),
        (19, "Newark relatives", -74.172, 40.735, False),
        (20, "Bronx relatives / later home", -73.900, 40.850, True),
        (21, "Belmar, Curtis Avenue", -74.018, 40.178, False),
    ]

    eu_base = ''.join(f'<path d="{d}"/>' for d in geo_paths(data, EUROPE, eu_box))
    at_base = ''.join(f'<path d="{d}"/>' for d in geo_paths(data, ATLANTIC, at_box))
    ny_base = ''.join(f'<path d="{d}"/>' for d in geo_paths(data, NYNJ, ny_box))

    eu_line = line(europe_route, EUROPE, eu_box)
    transatlantic = line([(2.352, 48.857), (-73.97, 40.755)], ATLANTIC, at_box)
    local_route = line([(s[2], s[3]) for s in ny_stops], NYNJ, ny_box)

    # Hand-tuned label positions minimize collisions.
    eu_offsets = {
        1: (-12, 17, "end"), 2: (-12, -11, "end"), 3: (-12, 17, "end"),
        4: (12, -12, "start"), 5: (12, 18, "start"), 6: (12, -11, "start"),
        7: (12, 18, "start"), 8: (12, 18, "start"), 9: (-12, -12, "end"),
        10: (-12, -12, "end"), 11: (-12, 18, "end"), 12: (-12, 18, "end"),
        13: (12, 18, "start"), 14: (-12, 18, "end"),
    }
    eu_marks = []
    for n, name, lon, lat, uncertain in europe_stops:
        dx, dy, anchor = eu_offsets[n]
        eu_marks.append(marker(n, name, lon, lat, EUROPE, eu_box, dx, dy, uncertain, anchor))

    ny_offsets = {
        16: (12, -22, "start"), 17: (12, 24, "start"), 18: (12, 5, "start"),
        19: (-12, -11, "end"), 20: (12, -11, "start"), 21: (12, 4, "start"),
    }
    ny_marks = []
    for n, name, lon, lat, uncertain in ny_stops:
        dx, dy, anchor = ny_offsets[n]
        ny_marks.append(marker(n, name, lon, lat, NYNJ, ny_box, dx, dy, uncertain, anchor))

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="900" viewBox="0 0 1500 900">
<defs>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity=".2"/></filter>
  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#a9462a"/></marker>
  <clipPath id="clip-eu"><rect x="55" y="125" width="760" height="420" rx="5"/></clipPath>
  <clipPath id="clip-at"><rect x="55" y="670" width="760" height="160" rx="5"/></clipPath>
  <clipPath id="clip-ny"><rect x="865" y="125" width="580" height="420" rx="5"/></clipPath>
</defs>
<style>
  .bg {{ fill:#f3efe4; }} .panel {{ fill:#dcebf0; stroke:#c8bfae; stroke-width:1.2; filter:url(#shadow); }}
  .land path {{ fill:#e3dccb; stroke:#b8ad99; stroke-width:.65; }}
  .route {{ fill:none; stroke:#a9462a; stroke-width:3.2; stroke-linecap:round; stroke-linejoin:round; marker-end:url(#arrow); }}
  .route.uncertain-segment {{ stroke-dasharray:8 7; opacity:.85; }}
  .stop circle {{ stroke-width:2.2; }} .stop.certain circle {{ fill:#224e5c; stroke:#fff; }}
  .stop.uncertain circle {{ fill:#fffdf7; stroke:#a9462a; stroke-dasharray:3 2; }}
  .num {{ font:700 10px Arial,sans-serif; text-anchor:middle; fill:#fff; }} .uncertain .num {{ fill:#a9462a; }}
  .label {{ font:600 12px Arial,sans-serif; fill:#283237; paint-order:stroke; stroke:#fffdf7; stroke-width:4; stroke-linejoin:round; }}
  .title {{ font:700 31px Georgia,serif; fill:#223c45; }} .subtitle {{ font:15px Arial,sans-serif; fill:#59666b; }}
  .heading {{ font:700 18px Georgia,serif; fill:#223c45; }} .small {{ font:12px Arial,sans-serif; fill:#59666b; }}
  .legend {{ font:13px Arial,sans-serif; fill:#37464b; }}
</style>
<rect class="bg" width="1500" height="900"/>
<text class="title" x="55" y="52">The narrator’s journey</text>
<text class="subtitle" x="55" y="80">Reconstructed from the chronological edited transcript • sequence, not exact track • Persons A–E treated as one composite narrator</text>
<rect class="panel" x="35" y="105" width="800" height="460" rx="12"/>
<rect class="panel" x="845" y="105" width="620" height="460" rx="12"/>
<rect class="panel" x="35" y="645" width="800" height="210" rx="12"/>
<g class="land" clip-path="url(#clip-eu)">{eu_base}</g>
<g class="land" clip-path="url(#clip-at)">{at_base}</g>
<g class="land" clip-path="url(#clip-ny)">{ny_base}</g>
<g class="small" fill="#6a766f" font-weight="700">
  <text x="295" y="250">FRANCE</text><text x="470" y="280">GERMANY</text><text x="615" y="285">POLAND</text>
  <text x="685" y="150">LITHUANIA</text><text x="685" y="350">GALICIA</text><text x="735" y="405">UKRAINE</text>
  <text x="100" y="745">NORTH AMERICA</text><text x="430" y="745">ATLANTIC OCEAN</text><text x="690" y="745">EUROPE</text>
  <text x="900" y="285">NEW JERSEY</text><text x="1225" y="330">NEW YORK</text>
</g>
<text class="heading" x="55" y="98">Europe, 1914–postwar</text>
<text class="heading" x="865" y="98">New York and New Jersey, c. 1922 onward</text>
<text class="heading" x="55" y="637">Atlantic crossing (port and track unspecified)</text>
<path class="route uncertain-segment" d="{eu_line}"/>
<path class="route uncertain-segment" d="{transatlantic}"/>
<path class="route uncertain-segment" d="{local_route}"/>
{''.join(eu_marks)}
{''.join(ny_marks)}
<g class="stop uncertain"><circle cx="430" cy="760" r="9"/><text class="num" x="430" y="763.5">15</text><text class="label" x="442" y="750" text-anchor="start">Atlantic voyage to New York</text></g>
<g transform="translate(870 510)">
  <circle cx="0" cy="0" r="8" fill="#224e5c" stroke="#fff" stroke-width="2"/><text class="legend" x="15" y="5">Named location</text>
  <circle cx="170" cy="0" r="8" fill="#fffdf7" stroke="#a9462a" stroke-width="2" stroke-dasharray="3 2"/><text class="legend" x="185" y="5">Approximate / disputed identification</text>
</g>
<text class="small" x="55" y="882">Numbers show narrative order. Dashed lines connect known or inferred stops; they do not claim the precise historical road, rail, ship, or front-line path.</text>
</svg>'''
    OUT.write_text(svg, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
