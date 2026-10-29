"""The release folder must hold exactly one official zip."""

from __future__ import annotations

import zipfile

from tools import build_release


def _touch(path, data: bytes = b"x"):
    path.write_bytes(data)
    return path


def test_prune_removes_loose_copies_and_old_bundles(tmp_path, monkeypatch):
    monkeypatch.setattr(build_release, "RELEASES", tmp_path)
    loose_package = _touch(tmp_path / build_release.PACKAGE_NAME)
    loose_setup = _touch(tmp_path / build_release.SETUP_NAME)
    old_bundle = _touch(tmp_path / "UmbraForge-20260101-000000.zip")
    current = _touch(tmp_path / "UmbraForge-20260102-000000.zip")
    notes = _touch(tmp_path / "notes.txt")

    build_release.prune_releases(keep=current)

    assert current.exists()
    assert notes.exists()
    assert not loose_package.exists()
    assert not loose_setup.exists()
    assert not old_bundle.exists()


def test_make_release_publishes_one_official_zip(tmp_path, monkeypatch):
    releases = tmp_path / "releases"
    build = tmp_path / "build"
    releases.mkdir()
    build.mkdir()
    monkeypatch.setattr(build_release, "RELEASES", releases)
    _touch(releases / build_release.PACKAGE_NAME)
    _touch(releases / build_release.SETUP_NAME)
    _touch(releases / "UmbraForge-20260101-000000.zip")

    package = _touch(build / "build-package.zip", b"package")
    setup = _touch(build / "build-setup.exe", b"setup")

    release = build_release.make_release(package, setup)

    files = sorted(path.name for path in releases.iterdir())
    assert release.name.startswith("UmbraForge-")
    assert release.name.endswith(".zip")
    assert files == [release.name]

    with zipfile.ZipFile(release) as archive:
        names = set(archive.namelist())
    assert package.name in names
    assert setup.name in names
    assert {"README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"} <= names
    assert "licenses/lgpl-3.0.txt" in names
