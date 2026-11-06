"""Regions, parameters and default settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    key: str
    name: str
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    central_lon: float  # for the Lambert conformal map projection

    def __post_init__(self):
        if not (-180 <= self.lon_min < self.lon_max <= 180):
            raise ValueError("Longitudes must satisfy -180 <= lon_min < lon_max <= 180")
        if not (-90 <= self.lat_min < self.lat_max <= 90):
            raise ValueError("Latitudes must satisfy -90 <= lat_min < lat_max <= 90")


REGIONS = {
    "conus": Region("conus", "Contiguous United States", -126.0, -65.0, 23.0, 51.0, -96.0),
    "ohio-valley": Region("ohio-valley", "Ohio Valley", -92.0, -78.0, 34.0, 43.0, -85.0),
}

# ECMWF Open Data short names
#   msl  mean sea level pressure (Pa)
#   tcwv total column water vapour (kg m-2)
#   tp   total precipitation, accumulated from the start of the run (m)
# Extra degrees of data around each region so curved map corners are filled
PAD_DEGREES = 20.0

PARAMS = ["msl", "tcwv", "tp"]
DEFAULT_STEPS = [0, 24, 48, 72]   # forecast hours; 24 h spacing gives daily rainfall totals
