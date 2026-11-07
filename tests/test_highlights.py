import pytest
from test_uswx import fake_global

from uswx.config import PAD_DEGREES, REGIONS
from uswx.fields import precip_24h, prepare_fields, subset_region
from uswx.highlights import find_highlights
from uswx.places import format_coords

CONUS = REGIONS["conus"]


def fake_place(lon, lat):
    return ("in", "Testland")


def test_highlights_found_and_ordered():
    ds = prepare_fields(subset_region(fake_global(), CONUS, pad=PAD_DEGREES))
    rain = precip_24h(ds)
    hl = find_highlights(ds, rain, CONUS, place=fake_place)
    kinds = {h["kind"] for h in hl}
    assert "low" in kinds              # 1015 - 18 = 997 hPa storm
    assert "moisture" in kinds         # tcwv peaks at 50
    assert all(h["region"] == "conus" for h in hl)
    assert [h["step"] for h in hl] == sorted(h["step"] for h in hl)
    low = next(h for h in hl if h["kind"] == "low")
    assert low["title"] == "Low pressure over Testland"
    assert low["lon"] == pytest.approx(-88, abs=1)


def test_no_rain_highlight_below_threshold():
    ds = prepare_fields(subset_region(fake_global(), CONUS, pad=PAD_DEGREES))
    hl = find_highlights(ds, precip_24h(ds), CONUS, place=fake_place)
    assert not any(h["kind"] == "rain" for h in hl)  # fake storm only gives 20 mm


def test_format_coords():
    assert format_coords(-88.0, 38.4) == "38.4°N, 88.0°W"


def test_same_system_listed_once():
    ds = prepare_fields(subset_region(fake_global(step_hours=(0, 24, 48, 72)), CONUS,
                                      pad=PAD_DEGREES))
    hl = find_highlights(ds, precip_24h(ds), CONUS, place=fake_place)
    assert sum(h["kind"] == "low" for h in hl) == 1   # stationary storm at every step


def test_phrases():
    from uswx.highlights import _phrase
    assert _phrase("rain", ("in", "Maine")) == "in Maine"
    assert _phrase("low", ("in", "Maine")) == "over Maine"
    assert _phrase("rain", ("off", "Maine")) == "off Maine"
    assert _phrase("low", ("far", "23.2°N, 69.5°W")) == "at 23.2°N, 69.5°W"
    assert _phrase("rain", ("at", "40.0°N, 90.0°W")) == "at 40.0°N, 90.0°W"


def test_far_offshore_rain_and_moisture_skipped():
    ds = prepare_fields(subset_region(fake_global(), CONUS, pad=PAD_DEGREES))
    hl = find_highlights(ds, precip_24h(ds), CONUS, place=lambda a, b: ("far", "sea"))
    assert all(h["kind"] in ("low", "high") for h in hl)


def test_json_written_as_utf8(tmp_path):
    import json
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"t": "23.2°N kg/m²"}, ensure_ascii=False), encoding="utf-8")
    assert "°" in f.read_bytes().decode("utf-8")


def test_value_matches_sentence():
    import re
    ds = prepare_fields(subset_region(fake_global(), CONUS, pad=PAD_DEGREES))
    for h in find_highlights(ds, precip_24h(ds), CONUS, place=fake_place):
        assert str(h["value"]) in re.findall(r"\d+", h["detail"])
