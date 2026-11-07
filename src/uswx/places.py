"""Turn a longitude/latitude into a short place description.

``describe_location`` returns a (relation, name) pair so callers can build grammatical
phrases: ("in", "Louisiana"), ("off", "Maine"), ("in", "British Columbia, Canada"),
("far", "23.2°N, 69.5°W") when no state is close, or ("at", coordinates) when the
boundary data could not be loaded.
"""

from __future__ import annotations

from functools import lru_cache

COUNTRIES = {"United States of America", "Canada", "Mexico"}
SUFFIX = {"United States of America": "", "Canada": ", Canada", "Mexico": ", Mexico"}
NEAR_DEGREES = 3.0  # "off <state>" if the nearest state is within this distance


def format_coords(lon: float, lat: float) -> str:
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{abs(lat):.1f}°{ns}, {abs(lon):.1f}°{ew}"


@lru_cache(maxsize=1)
def _states():
    """(name, prepared geometry) for US states and Canadian/Mexican provinces.

    Uses the Natural Earth file cartopy already downloads for the map borders.
    Returns an empty list if it cannot be loaded, so callers fall back to coordinates.
    """
    try:
        import cartopy.io.shapereader as shpreader
        from shapely.prepared import prep

        path = shpreader.natural_earth(resolution="50m", category="cultural",
                                       name="admin_1_states_provinces_lakes")
        out = []
        for rec in shpreader.Reader(path).records():
            if rec.attributes.get("admin") in COUNTRIES and rec.geometry is not None:
                name = rec.attributes["name"] + SUFFIX[rec.attributes["admin"]]
                out.append((name, rec.geometry, prep(rec.geometry)))
        return out
    except Exception:  # noqa: BLE001  (no data or no network: fall back to coordinates)
        return []


def describe_location(lon: float, lat: float) -> tuple[str, str]:
    """("in", state), ("off", nearest state), ("far", coords) or ("at", coords)."""
    states = _states()
    if not states:
        return ("at", format_coords(lon, lat))
    from shapely.geometry import Point

    pt = Point(lon, lat)
    for name, _, prepared in states:
        if prepared.contains(pt):
            return ("in", name)
    name, geom, _ = min(states, key=lambda s: s[1].distance(pt))
    if geom.distance(pt) <= NEAR_DEGREES:
        return ("off", name)
    return ("far", format_coords(lon, lat))
