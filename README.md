# us-weather-explorer

[![tests](https://github.com/hrahmanwave/us-weather-explorer/actions/workflows/tests.yml/badge.svg)](https://github.com/hrahmanwave/us-weather-explorer/actions/workflows/tests.yml)
[![update site](https://github.com/hrahmanwave/us-weather-explorer/actions/workflows/update-site.yml/badge.svg)](https://github.com/hrahmanwave/us-weather-explorer/actions/workflows/update-site.yml)

Daily weather maps and highlights for the **United States**, built from
[ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data).
The aim: a web page that answers *"what's the interesting weather in the US right now,
and where is it heading?"* — storms, heavy rain, and atmospheric rivers — with maps
for the next few days.

**Live page:** https://hrahmanwave.github.io/us-weather-explorer/ (rebuilt automatically twice a day)

The page lists what stands out in the forecast (heavy rain, deep lows, strong highs,
moisture plumes), and shows the maps with a day-by-day timeline. Click a highlight to
jump to its map.

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

## Build the site

```bash
python scripts/build_site.py
```

Downloads the latest forecast once, draws maps for every region from that same run
(`docs/maps/<region>/`), finds the highlights, and writes `docs/data/latest.json`.
Open the page locally with:

```bash
python -m http.server --directory docs
```

then visit http://localhost:8000.

To draw maps for a single region only: `python scripts/make_maps.py --region ohio-valley`.

## How highlights are found

| Highlight | Rule |
| --- | --- |
| Heavy rain | 24-hour total of at least 25 mm; the wettest point each day |
| Low pressure | A local pressure minimum at or below 1008 hPa |
| Strong high | A local pressure maximum at or above 1032 hPa |
| Moisture plume | Total column water vapour of at least 50 kg/m² |

Pressure centres are found on smoothed sea level pressure and must stand out from their
surroundings; a system seen at several forecast times is listed once, where it is strongest.
Place names come from Natural Earth state and province boundaries.

## Roadmap

- [x] Download latest ECMWF IFS forecast (Open Data, 0.25°)
- [x] Water vapour + pressure maps, 24 h precipitation maps (CONUS, Ohio Valley)
- [ ] 10 m wind and 2 m temperature anomaly maps
- [x] Web page with region tabs and a forecast timeline (GitHub Pages)
- [x] Automatic highlights: heavy rain, deep lows, strong highs, moisture plumes
- [x] Automatic update twice a day with GitHub Actions, published to GitHub Pages
- [ ] Rainfall totals for major river basins (Ohio, Mississippi, ...)

## How the site stays up to date

The **update site** workflow (`.github/workflows/update-site.yml`) runs at 08:40 and 20:40 UTC,
after ECMWF publishes the 00 and 12 UTC runs. It installs the package, runs
`scripts/build_site.py`, and publishes `docs/` to GitHub Pages. The maps and `latest.json`
are build output and are not committed to the repository. It can also be started by hand from
the Actions tab (**Run workflow**).

The forecast is downloaded from ECMWF directly first, then from its Google, Azure and AWS mirrors
(set `ECMWF_SOURCES` to change the order).

## Data and credit

Forecast data: ECMWF Open Data (IFS), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Contains modified ECMWF data.

## License

MIT (code)
