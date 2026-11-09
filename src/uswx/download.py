"""Download the latest ECMWF Open Data forecast."""

from __future__ import annotations

import os
import warnings
from datetime import datetime
from pathlib import Path

from .config import DEFAULT_STEPS, PARAMS


def fetch_latest(
    target_dir: str | Path = "data",
    params: list[str] | None = None,
    steps: list[int] | None = None,
    model: str = "ifs",
    sources: list[str] | None = None,
) -> tuple[Path, datetime]:
    """Download the most recent global forecast run as one GRIB2 file.

    Returns the file path and the run (initialisation) time in UTC.

    ECMWF mirrors its open data on AWS, Azure and Google Cloud. Sources are tried in
    order; set the environment variable ``ECMWF_SOURCES`` (e.g. ``"aws,ecmwf"``) to
    change the order without touching the code.
    """
    from ecmwf.opendata import Client

    params = params or PARAMS
    steps = steps or DEFAULT_STEPS
    if sources is None:
        sources = os.environ.get("ECMWF_SOURCES", "ecmwf,aws").split(",")

    last_error: Exception | None = None
    for source in [s.strip() for s in sources if s.strip()]:
        try:
            # The library's defaults retry up to 500 times, two minutes apart; fail fast
            # instead so the next mirror gets a chance.
            client = Client(source=source, model=model, resol="0p25",
                            maximum_retries=3, retry_after=20)
            run = client.latest(type="fc", step=steps[-1], param=params)
            target = Path(target_dir) / f"{model}_{run:%Y%m%d%H}.grib2"
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                client.retrieve(date=run.date(), time=run.hour, type="fc",
                                step=steps, param=params, target=str(target))
            return target, run
        except Exception as err:  # noqa: BLE001  (network or server problem: try the next mirror)
            warnings.warn(f"ECMWF source '{source}' failed: {err}", stacklevel=2)
            last_error = err
    raise RuntimeError("Could not download the forecast from any source") from last_error
