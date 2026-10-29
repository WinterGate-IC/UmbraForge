"""Installer packaging: payload extraction, flattening and install metadata."""

from __future__ import annotations

import json
import zipfile

from umbraforge import installer_core


def _package(path, names):
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in names.items():
            archive.writestr(name, data)
    return path


def test_payload_top_folder_is_flattened(tmp_path):
    payload = _package(tmp_path / "payload.zip", {
        "UmbraForge/UmbraForge.exe": b"MZ fake",
        "UmbraForge/README.md": b"read me",
        "UmbraForge/assets/umbraforge.ico": b"icon",
    })
    app_dir = tmp_path / "Programs" / "UmbraForge"
    data_dir = tmp_path / "Documents" / "UmbraForge"

    config = installer_core.install(
        app_dir, payload, create_shortcuts=False, quiet=True,
        data_dir=data_dir)

    assert (app_dir / "UmbraForge.exe").read_bytes() == b"MZ fake"
    assert (app_dir / "README.md").read_bytes() == b"read me"
    assert (app_dir / "assets" / "umbraforge.ico").exists()
    assert not (app_dir / "UmbraForge" / "UmbraForge.exe").exists()

    recorded = json.loads((app_dir / "install.json").read_text(encoding="utf-8"))
    assert recorded["version"] == installer_core.VERSION
    assert recorded["app_dir"] == str(app_dir.resolve())
    assert recorded["data_dir"] == str(data_dir.resolve())
    assert recorded["bundled"] is True
    assert (app_dir / "Uninstall UmbraForge.cmd").exists()
    assert config["launcher"].endswith("UmbraForge.exe")


def test_payload_cannot_escape_the_install_folder(tmp_path):
    payload = _package(tmp_path / "payload.zip", {
        "UmbraForge/UmbraForge.exe": b"MZ fake",
        "UmbraForge/../../escape.txt": b"nope",
    })
    app_dir = tmp_path / "install"
    installer_core.install(app_dir, payload, create_shortcuts=False,
                           quiet=True, data_dir=tmp_path / "data")

    assert not (tmp_path / "escape.txt").exists()
    assert (app_dir / "UmbraForge.exe").exists()


def test_a_flat_archive_is_also_accepted(tmp_path):
    payload = _package(tmp_path / "flat.zip", {
        "UmbraForge.exe": b"MZ fake",
        "LICENSE": b"MIT",
    })
    app_dir = tmp_path / "install"
    installer_core.install(app_dir, payload, create_shortcuts=False,
                           quiet=True, data_dir=tmp_path / "data")

    assert (app_dir / "UmbraForge.exe").exists()
    assert (app_dir / "LICENSE").exists()
