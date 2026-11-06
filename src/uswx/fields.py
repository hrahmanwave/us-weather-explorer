"""Read GRIB output and derive display fields."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import ndimage

from .config import Region


def open_forecast(path: str | Path) -> xr.Dataset:
    """Open a multi-parameter GRIB2 file as one Dataset.

    Parameters on different level types come out of cfgrib as separate datasets,
    so they are opened together and merged.
    """
    import cfgrib

    parts = cfgrib.open_datasets(str(path), backend_kwargs={"indexpath": ""})
    drop = ["surface", "entireAtmosphere", "meanSea", "heightAboveGround"]
    parts = [p.drop_vars(drop, errors="ignore") for p in parts]
    return xr.merge(parts, compat="override")


def subset_region(ds: xr.Dataset, region: Region, pad: float = 0.0) -> xr.Dataset:
    """Cut a region (plus ``pad`` degrees on every side) out of a global field.

    Padding matters for curved map projections: the plotted area is wider at the
    bottom than the lat/lon box, so the extra margin keeps the map corners filled.
    """
    lon = ds["longitude"]
    if float(lon.max()) > 180:  # 0..360 grid -> -180..180
        ds = ds.assign_coords(longitude=((lon + 180) % 360) - 180).sortby("longitude")
    lat = ds["latitude"]
    s, n = max(region.lat_min - pad, -90), min(region.lat_max + pad, 90)
    w, e = max(region.lon_min - pad, -180), min(region.lon_max + pad, 180)
    lat_slice = slice(n, s) if float(lat[0]) > float(lat[-1]) else slice(s, n)
    out = ds.sel(latitude=lat_slice, longitude=slice(w, e))
    if out.sizes["latitude"] == 0 or out.sizes["longitude"] == 0:
        raise ValueError(f"Region {region.name} does not overlap the data")
    return out


def prepare_fields(ds: xr.Dataset) -> xr.Dataset:
    """Display units: pressure Pa -> hPa."""
    out = ds.copy()
    if "msl" in out:
        out["msl"] = out["msl"] / 100.0
        out["msl"].attrs.update(units="hPa", long_name="Mean sea level pressure")
    if "tcwv" in out:
        out["tcwv"].attrs.update(units="kg m-2", long_name="Total column water vapour")
    return out


def precip_24h(ds: xr.Dataset) -> xr.DataArray:
    """24-hour precipitation totals (mm) ending at each step.

    ECMWF ``tp`` is accumulated from the start of the run, so the total for the
    24 h ending at step k is tp[k] - tp[k-1], valid only where steps are 24 h apart.
    """
    if "tp" not in ds:
        raise KeyError("Dataset has no 'tp' variable")
    steps = pd.to_timedelta(ds["step"].values)
    if len(steps) < 2:
        raise ValueError("Need at least two forecast steps")
    gaps = steps[1:] - steps[:-1]
    if not (gaps == pd.Timedelta(hours=24)).all():
        raise ValueError("Steps must be 24 h apart for daily totals")
    daily = ds["tp"].diff("step", label="upper") * 1000.0
    daily = daily.clip(min=0)  # tiny negative values from packing
    daily.attrs.update(units="mm", long_name="24-hour precipitation")
    return daily.rename("precip_24h")


def smooth(field: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """Gaussian smoothing (sigma in grid cells). Removes terrain noise in reduced pressure."""
    return ndimage.gaussian_filter(field, sigma=sigma, mode="nearest")


def find_extrema(
    field: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    region: Region,
    window: int = 41,
    min_depth: float = 2.0,
) -> list[dict]:
    """Local pressure minima (L) and maxima (H) inside ``region``.

    A point counts if it is the extreme value within a ``window`` x ``window`` box and
    stands out from that box's mean by at least ``min_depth`` (same units as ``field``).
    Points within half a window of the data edge are ignored, because a "minimum" there
    may just be where the data stops.
    """
    half = window // 2
    interior = np.zeros(field.shape, dtype=bool)
    interior[half:-half, half:-half] = True
    LON, LAT = np.meshgrid(lon, lat)
    inside = ((LON >= region.lon_min) & (LON <= region.lon_max)
              & (LAT >= region.lat_min) & (LAT <= region.lat_max))
    box_mean = ndimage.uniform_filter(field, size=window, mode="nearest")
    out = []
    for kind, filt, sign in (("L", ndimage.minimum_filter, -1), ("H", ndimage.maximum_filter, 1)):
        is_ext = (field == filt(field, size=window, mode="nearest"))
        strong = sign * (field - box_mean) >= min_depth
        for i, j in zip(*np.nonzero(is_ext & strong & interior & inside)):
            out.append({"kind": kind, "lon": float(lon[j]), "lat": float(lat[i]),
                        "value": float(field[i, j])})
    return out
