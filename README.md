# us-weather-explorer

Daily weather maps and highlights for the **United States**, built from
[ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data).
The aim: a web page that answers *"what's the interesting weather in the US right now,
and where is it heading?"* — storms, heavy rain, and atmospheric rivers — with maps
for the next few days.

> **Status:** step 1. Downloads the latest ECMWF IFS forecast and draws maps for the
> contiguous US and the Ohio Valley.

## Maps

| Map | What it shows |
| --- | --- |
| `vapour_pressure_XXX.png` | Total column water vapour (moisture plumes, atmospheric rivers) with sea level pressure contours; the deepest low is marked |
| `precip24h_XXX.png` | 24-hour precipitation totals; the heaviest total is marked |

## Installation

GRIB decoding needs ecCodes. On Windows the easiest route is conda:

```bash
conda create -n uswx -c conda-forge python=3.11 cfgrib cartopy xarray matplotlib ecmwf-opendata
conda activate uswx
pip install -e ".[dev]"
```

## Make today's maps

```bash
python scripts/make_maps.py                     # contiguous US
python scripts/make_maps.py --region ohio-valley
```

Maps go to `docs/maps/<region>/`.

## Roadmap

- [x] Download latest ECMWF IFS forecast (Open Data, 0.25°)
- [x] Water vapour + pressure maps, 24 h precipitation maps (CONUS, Ohio Valley)
- [ ] 10 m wind and 2 m temperature anomaly maps
- [ ] Web page with region tabs and a forecast-step slider (GitHub Pages)
- [ ] Automatic highlights: deep lows, heavy rain, strong winds, atmospheric rivers
- [ ] Daily automatic update with GitHub Actions
- [ ] Rainfall totals for major river basins (Ohio, Mississippi, ...)

## Data and credit

Forecast data: ECMWF Open Data (IFS). Check ECMWF's terms of use for attribution requirements.

## License

MIT (code)
