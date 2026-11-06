"""US weather explorer from ECMWF Open Data."""

from .config import REGIONS, Region
from .download import fetch_latest
from .fields import open_forecast, precip_24h, prepare_fields, subset_region
from .plot import plot_precip, plot_vapour_pressure

__version__ = "0.0.1"

__all__ = [
    "REGIONS",
    "Region",
    "fetch_latest",
    "open_forecast",
    "plot_precip",
    "plot_vapour_pressure",
    "precip_24h",
    "prepare_fields",
    "subset_region",
]
