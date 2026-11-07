"""Download the latest ECMWF forecast once and build everything the web page needs.

Usage:
    python scripts/build_site.py

Writes:
    docs/maps/<region>/*.png   maps for every region, all from the same forecast run
    docs/data/latest.json      run time, list of maps, and highlights for the page
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from uswx import (
    REGIONS,
    fetch_latest,
    open_forecast,
    plot_precip,
    plot_vapour_pressure,
    precip_24h,
    prepare_fields,
    subset_region,
)
from uswx.config import DEFAULT_STEPS, PAD_DEGREES
from uswx.highlights import find_highlights

DOCS = Path("docs")


def iso(t) -> str:
    return pd.Timestamp(t).strftime("%Y-%m-%dT%H:%MZ")


def main() -> None:
    path, run = fetch_latest(steps=DEFAULT_STEPS)
    print(f"Run {run:%Y-%m-%d %H} UTC -> {path}")
    full = open_forecast(path)

    site = {"model": "ECMWF IFS", "run": iso(run),
            "generated": iso(datetime.now(timezone.utc).replace(tzinfo=None)),
            "regions": {}, "highlights": []}

    for key, region in REGIONS.items():
        ds = prepare_fields(subset_region(full, region, pad=PAD_DEGREES))
        rain = precip_24h(ds)
        outdir = DOCS / "maps" / key
        layers = {"vapour_pressure": [], "precip24h": []}

        for k, step in enumerate(DEFAULT_STEPS):
            f = plot_vapour_pressure(ds, k, region, outdir / f"vapour_pressure_{step:03d}.png")
            valid = pd.Timestamp(ds["time"].values) + pd.Timedelta(ds["step"].values[k])
            layers["vapour_pressure"].append(
                {"step": step, "valid": iso(valid), "file": f.relative_to(DOCS).as_posix()})
        for k, step in enumerate(DEFAULT_STEPS[1:]):
            f = plot_precip(rain, k, region, outdir / f"precip24h_{step:03d}.png")
            valid = pd.Timestamp(ds["time"].values) + pd.Timedelta(hours=step)
            layers["precip24h"].append(
                {"step": step, "valid": iso(valid), "file": f.relative_to(DOCS).as_posix()})

        site["regions"][key] = {"name": region.name, "layers": layers}
        if key == "conus":
            site["highlights"] = find_highlights(ds, rain, region)
        print(f"{region.name}: maps done")

    out = DOCS / "data" / "latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(site, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out} with {len(site['highlights'])} highlights")


if __name__ == "__main__":
    main()
