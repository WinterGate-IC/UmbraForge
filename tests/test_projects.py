"""Project files: UmbraForge containers, reopen, merge, recents and save."""

from __future__ import annotations

import base64
import json
import zipfile

import pytest
from PySide6.QtCore import QMimeData, QUrl

from umbraforge import branding, quality, templates
from umbraforge.layers import (
    Design,
    ImageLayer,
    ShapeLayer,
    asset_bytes,
    project_info,
)
from umbraforge.ui import dialogs


def _project(name: str = "Project Test") -> Design:
    design = Design(name=name)
    design.set_size(640, 640)
    design.add(ShapeLayer(name="Disc", shape="circle", fill="#ff7a3d"))
    payload = b"fake-image-bytes"
    design.assets["asset"] = {
        "name": "dot.png", "mime": "image/png",
        "data": base64.b64encode(payload).decode("ascii"), "w": 4, "h": 4,
    }
    design.add(ImageLayer(name="Dot", asset_id="asset"))
    return design


# --------------------------------------------------------------------------
# the .umbra container
# --------------------------------------------------------------------------
def test_project_header_is_for_umbraforge_only(tmp_path):
    design = _project()
    path = design.save(tmp_path / "studio")
    assert path.name == "studio.umbra"

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["format"] == "umbraforge"
    assert raw["saved_with"].startswith(branding.APP_NAME)
    assert raw["saved_at"]
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))

    info = project_info(path)
    assert info["name"] == "Project Test"
    assert (info["width"], info["height"]) == (640, 640)
    assert info["layers"] == 2
    assert info["assets"] == 1
    assert info["version"] >= 1

    reopened = Design.open(path)
    assert reopened.to_dict() == design.to_dict()


def test_project_info_rejects_other_files(tmp_path):
    foreign = tmp_path / "foreign.umbra"
    foreign.write_text('{"format": "png"}', encoding="utf-8")
    with pytest.raises(ValueError, match="not an UmbraForge"):
        project_info(foreign)


def test_import_project_layers_remaps_images_and_ids(tmp_path):
    source = _project("Source")
    target = Design(name="Base")
    target.set_size(1200, 1200)

    count = target.import_layers(source)

    assert count == 2
    assert target.name == "Base"
    assert [type(layer) for layer in target.layers] == [ShapeLayer, ImageLayer]
    assert target.layers[0].id != source.layers[0].id
    image = next(layer for layer in target.layers
                 if isinstance(layer, ImageLayer))
    assert image.asset_id in target.assets
    assert asset_bytes(target.assets, image.asset_id) == b"fake-image-bytes"
    assert image.original_asset_id == image.asset_id
    assert target.layers[-1].id == target.selected


def test_import_project_skips_missing_image_assets():
    source = Design(name="Broken")
    source.add(ShapeLayer(name="Shape"))
    source.add(ImageLayer(name="Ghost", asset_id="missing"))
    target = Design(name="Base")

    assert target.import_layers(source) == 1
    assert [type(layer) for layer in target.layers] == [ShapeLayer]


# --------------------------------------------------------------------------
# one save flow
# --------------------------------------------------------------------------
def test_save_dialog_defaults_to_png_and_offers_projects(qapp):
    dialog = dialogs.SaveDialog(templates.build("signal_lost"))
    try:
        assert dialog._format() == "png"
        assert dialogs._format_suffix(dialog._format()) == "png"
        keys = [dialog.format_combo.itemData(index)
                for index in range(dialog.format_combo.count())]
        for key in ("png", "umbra", "jpg", "webp", "ico", "icns", "webicon",
                    "bmp", "tif"):
            assert key in keys
        assert keys[0] == "png"

        dialog._select_format("umbra")
        assert dialog.path_edit.text().endswith(".umbra")
        assert "editable" in dialog.save_button.text().lower()
    finally:
        dialog.deleteLater()


def test_save_dialog_writes_an_editable_project(qapp, tmp_path, monkeypatch):
    design = _project("Saved Project")
    dialog = dialogs.SaveDialog(design)
    try:
        dialog._select_format("umbra")
        target = tmp_path / "saved.umbra"
        dialog.path_edit.setText(str(target))
        monkeypatch.setattr(dialogs.QMessageBox, "exec", lambda self: 0)
        dialog._save()
        assert dialog.saved_format == "umbra"
        assert dialog.saved_path == target
        assert Design.open(target).name == "Saved Project"
    finally:
        dialog.deleteLater()


def test_save_dialog_writes_a_flat_png(qapp, tmp_path, monkeypatch):
    design = _project("Flat Image")
    dialog = dialogs.SaveDialog(design)
    try:
        target = tmp_path / "flat.png"
        dialog.path_edit.setText(str(target))
        monkeypatch.setattr(dialogs.QMessageBox, "exec", lambda self: 0)
        dialog._save()
        assert dialog.saved_format == "png"
        assert target.exists()
        assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        dialog.deleteLater()


# --------------------------------------------------------------------------
# icons and web kits
# --------------------------------------------------------------------------
def test_icon_and_web_kit_writers(qapp, tmp_path, monkeypatch):
    design = templates.build("ember_sigil")
    monkeypatch.setattr(quality, "_icon_base", lambda profile=None: 256)

    ico, _plan = quality.save_icon_export(
        design, tmp_path / "mark.ico", "ico", size=256)
    assert ico.read_bytes()[:4] == b"\x00\x00\x01\x00"

    icns, _plan = quality.save_icon_export(
        design, tmp_path / "mark.icns", "icns", size=256)
    assert icns.exists() and icns.stat().st_size > 0

    bundle, _plan = quality.save_web_icon_kit(design, tmp_path / "web.zip")
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
    assert {"favicon.ico", "favicon-16x16.png", "apple-touch-icon.png",
            "site.webmanifest", "browserconfig.xml"} <= names


# --------------------------------------------------------------------------
# window workflow
# --------------------------------------------------------------------------
def test_window_has_one_save_action_and_no_export_action(window):
    assert hasattr(window, "act_save")
    assert not hasattr(window, "act_export")
    assert window.act_save.text().startswith("Save")


def test_recent_project_is_listed_and_reopens(window, tmp_path):
    design = _project("Recent Project")
    path = design.save(tmp_path / "recent.umbra")

    window._remember_project(path)

    assert window._recent_paths()[0] == path.resolve()
    assert path.resolve() in [item.resolve()
                              for item in window.library_panel._recent_paths]
    assert window.library_panel._recent_empty.isHidden()

    assert window._open_path(path)
    assert window.design.name == "Recent Project"
    assert window.path == path
    assert "recent.umbra" in window.windowTitle()


def test_drop_targets_split_projects_from_images(window, tmp_path):
    project = tmp_path / "drop.umbra"
    project.write_text("{}", encoding="utf-8")
    image = tmp_path / "drop.png"
    image.write_bytes(b"not really a png")
    other = tmp_path / "notes.txt"
    other.write_text("ignore", encoding="utf-8")

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(project)),
                  QUrl.fromLocalFile(str(image)),
                  QUrl.fromLocalFile(str(other))])

    projects, images = window._dropped_files(mime)
    assert projects == [project]
    assert images == [image]
