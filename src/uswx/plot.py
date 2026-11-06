"""Static maps for a region: water vapour + pressure, and 24 h precipitation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from .config import Region
from .fields import find_extrema, smooth

TCWV_LEVELS = np.arange(0, 75, 5)
MSL_INTERVAL = 4  # hPa
PRECIP_LEVELS = [1, 5, 10, 15, 25, 35, 50, 75, 100, 150, 200]  # mm
PRECIP_COLORS = ["#c6e9fb", "#7fcdf3", "#2b9be0", "#1c64b8", "#2e9b45", "#7fd13b",
                 "#f5e14b", "#f59c2a", "#e3442a", "#a3157d"]
CREDIT = "Data: ECMWF Open Data (IFS)"


def _times(da: xr.DataArray | xr.Dataset) -> tuple[pd.Timestamp, pd.Timestamp, int]:
    run = pd.Timestamp(da["time"].values)
    step_h = int(pd.Timedelta(da["step"].values) / pd.Timedelta(hours=1))
    return run, run + pd.Timedelta(hours=step_h), step_h


def _new_map(region: Region, use_cartopy: bool):
    """Figure and axes with coastlines, borders and states; returns (fig, ax, plot kwargs)."""
    if use_cartopy:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        proj = ccrs.LambertConformal(central_longitude=region.central_lon,
                                     standard_parallels=(33, 45))
        fig = plt.figure(figsize=(10, 6.8))
        ax = plt.axes(projection=proj)
        ax.set_extent([region.lon_min, region.lon_max, region.lat_min, region.lat_max],
                      crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.7)
        ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.6)
        ax.add_feature(cfeature.STATES.with_scale("50m"), linewidth=0.3, edgecolor="0.35")
        return fig, ax, {"transform": ccrs.PlateCarree()}
    fig, ax = plt.subplots(figsize=(10, 6.8))
    ax.set_xlim(region.lon_min, region.lon_max)
    ax.set_ylim(region.lat_min, region.lat_max)
    ax.set_aspect(1 / np.cos(np.deg2rad((region.lat_min + region.lat_max) / 2)))
    return fig, ax, {}


def _finish(fig, ax, title: str, note: str, out: str | Path) -> Path:
    ax.set_title(title, fontsize=11)
    fig.text(0.99, 0.01, f"{CREDIT} · {note}", ha="right", fontsize=7, color="0.4")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_vapour_pressure(ds: xr.Dataset, step_index: int, region: Region,
                         out: str | Path, use_cartopy: bool = True) -> Path:
    """Water vapour shading, smoothed sea level pressure contours, L/H pressure centres."""
    d = ds.isel(step=step_index) if "step" in ds.dims else ds
    run, valid, step_h = _times(d)
    lon, lat = d["longitude"].values, d["latitude"].values
    fig, ax, kw = _new_map(region, use_cartopy)

    cf = ax.contourf(lon, lat, d["tcwv"].values, levels=TCWV_LEVELS,
                     cmap="YlGnBu", extend="max", **kw)
    cb = fig.colorbar(cf, ax=ax, orientation="horizontal", pad=0.04, shrink=0.7)
    cb.set_label("Total column water vapour (kg m$^{-2}$)")

    msl = smooth(d["msl"].values)
    lo = np.floor(np.nanmin(msl) / MSL_INTERVAL) * MSL_INTERVAL
    hi = np.ceil(np.nanmax(msl) / MSL_INTERVAL) * MSL_INTERVAL
    levels = np.arange(lo, hi + MSL_INTERVAL, MSL_INTERVAL)
    if len(levels) > 1:
        cs = ax.contour(lon, lat, msl, levels=levels, colors="k", linewidths=0.6, **kw)
        ax.clabel(cs, fmt="%d", fontsize=7)
    halo = [pe.withStroke(linewidth=3, foreground="white")]
    for c in find_extrema(msl, lon, lat, region):
        color = "crimson" if c["kind"] == "L" else "navy"
        ax.text(c["lon"], c["lat"], c["kind"], color=color, fontsize=16, fontweight="bold",
                ha="center", va="center", path_effects=halo, **kw)
        ax.text(c["lon"], c["lat"] - 1.0, f"{c['value']:.0f}", color=color, fontsize=8,
                fontweight="bold", ha="center", va="top", path_effects=halo, **kw)

    title = (f"{region.name} — water vapour & sea level pressure, +{step_h} h\n"
             f"Run {run:%Y-%m-%d %H} UTC · Valid {valid:%a %d %b %Y %H} UTC")
    return _finish(fig, ax, title,
                   f"Smoothed pressure contours every {MSL_INTERVAL} hPa", out)


def plot_precip(precip: xr.DataArray, step_index: int, region: Region,
                out: str | Path, use_cartopy: bool = True) -> Path:
    """24 h precipitation map; the heaviest total in the region is marked."""
    p = precip.isel(step=step_index)
    run, valid, step_h = _times(p)
    start = valid - pd.Timedelta(hours=24)
    lon, lat = p["longitude"].values, p["latitude"].values
    vals = p.values
    fig, ax, kw = _new_map(region, use_cartopy)

    cmap = mcolors.ListedColormap(PRECIP_COLORS).with_extremes(over="#5a0a4f")
    norm = mcolors.BoundaryNorm(PRECIP_LEVELS, cmap.N)
    masked = np.ma.masked_less(vals, PRECIP_LEVELS[0])
    cf = ax.contourf(lon, lat, masked, levels=PRECIP_LEVELS, cmap=cmap, norm=norm,
                     extend="max", **kw)
    cb = fig.colorbar(cf, ax=ax, orientation="horizontal", pad=0.04, shrink=0.7)
    cb.set_label("24-hour precipitation (mm)")

    LON, LAT = np.meshgrid(lon, lat)
    inside = ((LON >= region.lon_min) & (LON <= region.lon_max)
              & (LAT >= region.lat_min) & (LAT <= region.lat_max))
    vals_in = np.where(inside, vals, np.nan)
    if np.nanmax(vals_in) >= PRECIP_LEVELS[0]:
        i, j = np.unravel_index(np.nanargmax(vals_in), vals.shape)
        ax.plot(lon[j], lat[i], marker="^", color="k", ms=7, **kw)
        ax.text(lon[j] + 0.4, lat[i] + 0.4, f"max {vals[i, j]:.0f} mm", fontsize=8,
                fontweight="bold",
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")], **kw)

    title = (f"{region.name} — 24 h precipitation ending +{step_h} h\n"
             f"{start:%a %d %b %H} UTC to {valid:%a %d %b %Y %H} UTC · Run {run:%Y-%m-%d %H} UTC")
    return _finish(fig, ax, title, "Totals below 1 mm not shown", out)
