"""Download the latest ECMWF forecast and draw US maps.

Usage:
    python scripts/make_maps.py                    # contiguous US
    python scripts/make_maps.py --region ohio-valley

Writes to docs/maps/<region>/ (later served by GitHub Pages):
    vapour_pressure_000.png ... (one per forecast step)
    precip24h_024.png ...       (24 h totals ending at each step after the first)
"""

from __future__ import annotations

import argparse
from pathlib import Path

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
from uswx.config import PAD_DEGREES


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--region", choices=sorted(REGIONS), default="conus")
    p.add_argument("--steps", type=int, nargs="+", default=[0, 24, 48, 72])
    p.add_argument("--out", default="docs/maps")
    args = p.parse_args()
    region = REGIONS[args.region]
    outdir = Path(args.out) / region.key

    path, run = fetch_latest(steps=args.steps)
    print(f"Run {run:%Y-%m-%d %H} UTC -> {path}")
    ds = prepare_fields(subset_region(open_forecast(path), region, pad=PAD_DEGREES))

    for k, step in enumerate(args.steps):
        print("Saved", plot_vapour_pressure(ds, k, region, outdir / f"vapour_pressure_{step:03d}.png"))

    rain = precip_24h(ds)
    for k, step in enumerate(args.steps[1:]):
        print("Saved", plot_precip(rain, k, region, outdir / f"precip24h_{step:03d}.png"))


if __name__ == "__main__":
    main()
