"""Custom art store: corrupt files, SVG import and round trips."""

from __future__ import annotations

import json

import pytest

from umbraforge import custom_art


@pytest.fixture()
def store(tmp_path, monkeypatch):
    path = tmp_path / "art.json"
    monkeypatch.setenv(custom_art.STORE_ENV, str(path))
    return path


def test_load_keeps_art_with_a_broken_timestamp(store):
    store.write_text(json.dumps({
        "format": "umbraforge-art", "version": 1,
        "shapes": [{"key": "user-shape-x", "name": "X",
                    "path": "M 0 0 L 10 10 Z", "created": "yesterday"}],
        "icons": [],
    }), encoding="utf-8")

    records = custom_art.load()["shapes"]

    assert len(records) == 1
    assert records[0]["created"] == 0.0


def test_load_drops_records_without_paths(store):
    store.write_text(json.dumps({
        "shapes": [{"key": "user-shape-x", "path": "   "},
                   {"key": "user-shape-ok", "path": "M 0 0 L 10 10 Z"}],
        "icons": [],
    }), encoding="utf-8")

    records = custom_art.load()["shapes"]

    assert [record["key"] for record in records] == ["user-shape-ok"]


def test_added_art_round_trips(store):
    record = custom_art.add("shape", "Star burst", "M 0 0 L 10 10 Z",
                            "Made by hand")

    assert record["key"].startswith("user-shape-star-burst")
    assert custom_art.label("shape", record["key"]) == "Star burst"
    assert store.is_file()
    assert custom_art.get("shape", record["key"])["note"] == "Made by hand"
    assert custom_art.path("shape", record["key"]) is not None
    assert custom_art.remove("shape", record["key"]) is True
    assert custom_art.entries("shape") == []


def test_duplicate_names_get_distinct_keys(store):
    first = custom_art.add("icon", "Glyph", "M 0 0 L 10 10 Z")
    second = custom_art.add("icon", "Glyph", "M 0 0 L 10 10 Z")

    assert first["key"] != second["key"]
    assert second["key"].endswith("-2")


def test_import_file_reads_shape_primitives(store, tmp_path):
    source = tmp_path / "badge.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<rect x="1" y="2" width="10" height="20" rx="2"/>'
        '<circle cx="5" cy="5" r="3"/>'
        '</svg>', encoding="utf-8")

    record = custom_art.import_file(source, "shape")

    assert record["name"] == "badge"
    assert record["note"] == "Imported from badge.svg"
    assert custom_art.path("shape", record["key"]) is not None


def test_non_svg_files_are_rejected(store, tmp_path):
    source = tmp_path / "photo.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n")

    with pytest.raises(ValueError, match="SVG"):
        custom_art.import_file(source, "shape")


def test_empty_artwork_is_rejected_and_not_stored(store):
    with pytest.raises(ValueError):
        custom_art.add("shape", "Nothing", "M 0 0")

    assert custom_art.entries("shape") == []


def test_blank_names_fall_back_to_a_label(store):
    record = custom_art.add("shape", "   ", "M 0 0 L 10 10 Z")

    assert record["name"] == "Custom art"
    assert custom_art.label("shape", record["key"]) == "Custom art"

    assert custom_art.rename("shape", record["key"], "  ") is True
    assert custom_art.label("shape", record["key"]) == "Custom art"
