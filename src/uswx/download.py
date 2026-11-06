"""Download the latest ECMWF Open Data forecast."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import DEFAULT_STEPS, PARAMS


def fetch_latest(
    target_dir: str | Path = "data",
    params: list[str] | None = None,
    steps: list[int] | None = None,
    model: str = "ifs",
) -> tuple[Path, datetime]:
    """Download the most recent global forecast run as one GRIB2 file.

    Returns the file path and the run (initialisation) time in UTC.
    """
    from ecmwf.opendata import Client

    params = params or PARAMS
    steps = steps or DEFAULT_STEPS
    client = Client(source="ecmwf", model=model, resol="0p25")
    run = client.latest(type="fc", step=steps[-1], param=params)
    target = Path(target_dir) / f"{model}_{run:%Y%m%d%H}.grib2"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        client.retrieve(date=run.date(), time=run.hour, type="fc",
                        step=steps, param=params, target=str(target))
    return target, run
