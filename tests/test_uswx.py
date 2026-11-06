import numpy as np
import pandas as pd
import pytest
import xarray as xr

from uswx.config import REGIONS, Region
from uswx.fields import find_extrema, precip_24h, prepare_fields, smooth, subset_region
from uswx.plot import plot_precip, plot_vapour_pressure

CONUS = REGIONS["conus"]


def fake_global(lon0_360=False, step_hours=(0, 24, 48)):
    lat = np.arange(90, -90.25, -0.5)
    lon = np.arange(0, 360, 0.5) if lon0_360 else np.arange(-180, 180, 0.5)
    steps = pd.to_timedelta(list(step_hours), unit="h")
    LON, LAT = np.meshgrid(((lon + 180) % 360) - 180, lat)
    dist2 = (LON + 88) ** 2 + (LAT + 0 - 38) ** 2          # storm near Kentucky
    msl = 101500 - 1800 * np.exp(-dist2 / 20)
    tcwv = 10 + 40 * np.exp(-dist2 / 60)
    rate = 0.02 * np.exp(-dist2 / 5)                       # m per day near the storm
    tp = np.stack([rate * (h / 24) for h in step_hours])  # accumulated from run start
    n = len(steps)
    return xr.Dataset(
        {"msl": (("step", "latitude", "longitude"), np.broadcast_to(msl, (n, *msl.shape))),
         "tcwv": (("step", "latitude", "longitude"), np.broadcast_to(tcwv, (n, *msl.shape))),
         "tp": (("step", "latitude", "longitude"), tp)},
        coords={"latitude": lat, "longitude": lon, "step": steps,
                "time": np.datetime64("2026-11-06T00:00")},
    )


@pytest.mark.parametrize("lon0_360", [False, True])
def test_subset_conus(lon0_360):
    sub = subset_region(fake_global(lon0_360), CONUS)
    assert float(sub.longitude.min()) == pytest.approx(-126.0)
    assert float(sub.longitude.max()) == pytest.approx(-65.0)


def test_precip_24h_is_daily_increment():
    ds = subset_region(fake_global(), CONUS)
    rain = precip_24h(ds)
    assert rain.sizes["step"] == 2
    assert float(rain.max()) == pytest.approx(20.0, rel=1e-3)  # 0.02 m/day -> 20 mm
    assert float(rain.min()) >= 0


def test_precip_requires_24h_steps():
    ds = subset_region(fake_global(step_hours=(0, 12, 24)), CONUS)
    with pytest.raises(ValueError):
        precip_24h(ds)


def test_region_validation():
    with pytest.raises(ValueError):
        Region("x", "bad", -65, -126, 23, 51, -96)


def test_maps_written(tmp_path):
    ds = prepare_fields(subset_region(fake_global(), CONUS))
    a = plot_vapour_pressure(ds, 1, CONUS, tmp_path / "vp.png", use_cartopy=False)
    b = plot_precip(precip_24h(ds), 0, CONUS, tmp_path / "pr.png", use_cartopy=False)
    assert a.stat().st_size > 10_000 and b.stat().st_size > 10_000


def test_padding_widens_subset():
    plain = subset_region(fake_global(), CONUS)
    padded = subset_region(fake_global(), CONUS, pad=10)
    assert float(padded.longitude.min()) == pytest.approx(-136.0)
    assert padded.sizes["latitude"] > plain.sizes["latitude"]


def test_extrema_finds_interior_low_not_edge():
    ds = prepare_fields(subset_region(fake_global(), CONUS, pad=12)).isel(step=0)
    msl = ds["msl"].values.copy()
    msl[0, 0] = 900.0                      # artificial "minimum" on the data edge
    found = find_extrema(smooth(msl), ds.longitude.values, ds.latitude.values, CONUS,
                         window=21)
    lows = [c for c in found if c["kind"] == "L"]
    assert len(lows) == 1
    assert lows[0]["lon"] == pytest.approx(-88, abs=1)
    assert lows[0]["lat"] == pytest.approx(38, abs=1)
