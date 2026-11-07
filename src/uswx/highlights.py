"""Find the notable weather in a forecast and describe it in plain words."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import xarray as xr

from .config import Region
from .fields import find_extrema, smooth
from .places import describe_location

# Thresholds for something to count as a highlight
RAIN_MM = 25.0          # 24 h total
LOW_HPA = 1008.0        # low centre at or below
HIGH_HPA = 1032.0       # high centre at or above
MOISTURE_KG = 50.0      # total column water vapour
MAX_HIGHLIGHTS = 8
# How many of each kind to list, and how far apart (degrees) two of a kind must be
# to count as different systems. Rain is kept per day instead.
PER_KIND = {"rain": 3, "low": 3, "high": 2, "moisture": 1}
SAME_SYSTEM_DEG = 8.0


def _valid(ds: xr.Dataset | xr.DataArray, k: int) -> pd.Timestamp:
    run = pd.Timestamp(ds["time"].values)
    return run + pd.Timedelta(ds["step"].values[k])


def _when(t: pd.Timestamp) -> str:
    return f"{t:%a} {t.day} {t:%b}, {t:%H} UTC"


# Preposition for each kind of highlight when the place is inside a state
OVER = {"rain": "in", "low": "over", "high": "over", "moisture": "over"}


def _phrase(kind: str, where: tuple[str, str]) -> str:
    relation, name = where
    word = {"in": OVER[kind], "off": "off"}.get(relation, "at")
    return f"{word} {name}"


def _num(x: float) -> int:
    """Round once, so the big number on the page and the sentence always agree."""
    return int(f"{x:.0f}")


def _inside(lon: np.ndarray, lat: np.ndarray, region: Region) -> np.ndarray:
    LON, LAT = np.meshgrid(lon, lat)
    return ((LON >= region.lon_min) & (LON <= region.lon_max)
            & (LAT >= region.lat_min) & (LAT <= region.lat_max))


def find_highlights(
    ds: xr.Dataset,
    precip: xr.DataArray | None,
    region: Region,
    place: Callable[[float, float], tuple[str, str]] = describe_location,
) -> list[dict]:
    """Highlights for one region: heavy rain, deep lows, strong highs, moisture plumes.

    ``ds`` holds msl (hPa) and tcwv on a padded grid; ``precip`` holds 24 h totals (mm).
    Each highlight records the region, layer and step to show on the web page.
    """
    lon, lat = ds["longitude"].values, ds["latitude"].values
    inside = _inside(lon, lat, region)
    steps_h = [int(pd.Timedelta(s) / pd.Timedelta(hours=1)) for s in ds["step"].values]
    found: list[dict] = []

    for k, step in enumerate(steps_h):
        t = _valid(ds, k)
        msl = smooth(ds["msl"].isel(step=k).values)
        for c in find_extrema(msl, lon, lat, region):
            if c["kind"] == "L" and c["value"] <= LOW_HPA:
                found.append({
                    "kind": "low", "score": (LOW_HPA - c["value"]) / 4 + 1,
                    "title": f"Low pressure {_phrase('low', place(c['lon'], c['lat']))}",
                    "detail": f"Centre at {_num(c['value'])} hPa on {_when(t)}.",
                    "layer": "vapour_pressure", "step": step,
                    "lon": c["lon"], "lat": c["lat"], "value": _num(c["value"])})
            elif c["kind"] == "H" and c["value"] >= HIGH_HPA:
                found.append({
                    "kind": "high", "score": (c["value"] - HIGH_HPA) / 6 + 0.5,
                    "title": f"Strong high pressure {_phrase('high', place(c['lon'], c['lat']))}",
                    "detail": f"Centre at {_num(c['value'])} hPa on {_when(t)}.",
                    "layer": "vapour_pressure", "step": step,
                    "lon": c["lon"], "lat": c["lat"], "value": _num(c["value"])})

        tcwv = np.where(inside, ds["tcwv"].isel(step=k).values, np.nan)
        if np.nanmax(tcwv) >= MOISTURE_KG:
            i, j = np.unravel_index(np.nanargmax(tcwv), tcwv.shape)
            where = place(float(lon[j]), float(lat[i]))
            if where[0] == "far":   # far out at sea: not a US highlight
                continue
            found.append({
                "kind": "moisture", "score": (tcwv[i, j] - MOISTURE_KG) / 10 + 0.5,
                "title": f"Moisture plume {_phrase('moisture', where)}",
                "detail": f"Water vapour up to {_num(tcwv[i, j])} kg/m² on {_when(t)}.",
                "layer": "vapour_pressure", "step": step,
                "lon": float(lon[j]), "lat": float(lat[i]), "value": _num(tcwv[i, j])})

    if precip is not None:
        for k in range(precip.sizes["step"]):
            t = _valid(precip, k)
            step = int(pd.Timedelta(precip["step"].values[k]) / pd.Timedelta(hours=1))
            rain = np.where(inside, precip.isel(step=k).values, np.nan)
            if np.nanmax(rain) >= RAIN_MM:
                i, j = np.unravel_index(np.nanargmax(rain), rain.shape)
                where = place(float(lon[j]), float(lat[i]))
                if where[0] == "far":
                    continue
                found.append({
                    "kind": "rain", "score": rain[i, j] / 25,
                    "title": f"Heavy rain {_phrase('rain', where)}",
                    "detail": f"Up to {_num(rain[i, j])} mm in the 24 hours to {_when(t)}.",
                    "layer": "precip24h", "step": step,
                    "lon": float(lon[j]), "lat": float(lat[i]), "value": _num(rain[i, j])})

    # A slow-moving low shows up at every step; list each system once, at the step
    # where it is strongest. Heavy rain is kept per day.
    chosen: list[dict] = []
    for h in sorted(found, key=lambda h: h["score"], reverse=True):
        same_kind = [c for c in chosen if c["kind"] == h["kind"]]
        if len(same_kind) >= PER_KIND[h["kind"]]:
            continue
        if h["kind"] == "rain":
            duplicate = any(c["step"] == h["step"] for c in same_kind)
        else:
            duplicate = any(np.hypot(c["lon"] - h["lon"], c["lat"] - h["lat"]) < SAME_SYSTEM_DEG
                            for c in same_kind)
        if not duplicate:
            chosen.append(h)
    top = chosen[:MAX_HIGHLIGHTS]
    for h in top:
        h["region"] = region.key
        h["score"] = round(float(h["score"]), 2)
    return sorted(top, key=lambda h: (h["step"], -h["score"]))
