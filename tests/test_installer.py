"""Installer packaging: payload extraction, flattening and install metadata."""

from __future__ import annotations

import json
import subprocess
import time
import zipfile

import pytest

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


def test_a_single_file_archive_keeps_its_only_file(tmp_path):
    payload = _package(tmp_path / "single.zip", {
        "UmbraForge.exe": b"MZ fake",
    })
    app_dir = tmp_path / "install"

    config = installer_core.install(
        app_dir, payload, create_shortcuts=False, quiet=True,
        data_dir=tmp_path / "data")

    assert (app_dir / "UmbraForge.exe").read_bytes() == b"MZ fake"
    assert config["bundled"] is True


def test_a_frozen_install_without_a_payload_fails_clearly(tmp_path,
                                                          monkeypatch):
    monkeypatch.setattr(installer_core.sys, "frozen", True, raising=False)

    with pytest.raises(RuntimeError, match="payload"):
        installer_core.install(tmp_path / "install", None,
                               create_shortcuts=False, quiet=True,
                               data_dir=tmp_path / "data")

    assert not (tmp_path / "install").exists()


def test_uninstaller_uses_cmd_quoting(tmp_path):
    app_dir = tmp_path / "UmbraForge"
    app_dir.mkdir()

    script = installer_core._write_uninstaller(app_dir, [])

    text = script.read_text(encoding="utf-8", errors="replace")
    assert 'cd /d "%TEMP%"' in text
    assert 'rmdir /s /q "' in text
    assert '\\"' not in text
    assert "\r\r\n" not in text


def test_uninstaller_doubles_percent_signs(tmp_path):
    app_dir = tmp_path / "Programs" / "100% Real"
    app_dir.mkdir(parents=True)

    script = installer_core._write_uninstaller(app_dir, [])

    text = script.read_text(encoding="utf-8", errors="replace")
    assert "100%% Real" in text
    assert 'rmdir /s /q "' in text


def _oem_ready() -> bool:
    if not installer_core.IS_WINDOWS:
        return False
    try:
        "UmbraForge caf\u00e9".encode("oem")
    except (LookupError, UnicodeError):
        return False
    return True


def _run_uninstaller(script) -> None:
    # Explorer starts the script with the folder as the working directory.
    # The doubled outer quotes are how cmd.exe keeps a path with spaces and
    # metacharacters in one piece.
    command = f'cmd.exe /c ""{script}""'
    subprocess.run(command, input=b"Y\r\n", capture_output=True, timeout=30,
                   cwd=str(script.parent))
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if not script.parent.exists():
            return
        time.sleep(0.25)


@pytest.mark.skipif(not installer_core.IS_WINDOWS, reason="uses cmd.exe")
@pytest.mark.parametrize("name", ["UmbraForge", "Tools & Games", "100% Real",
                                  "A^B", "Tools & Games (x86)"])
def test_uninstaller_removes_the_program_folder(tmp_path, name):
    app_dir = tmp_path / "Programs" / name
    (app_dir / "assets").mkdir(parents=True)
    (app_dir / "assets" / "mark.txt").write_text("x", encoding="utf-8")
    shortcut = tmp_path / "Desktop" / "UmbraForge.lnk"
    shortcut.parent.mkdir()
    shortcut.write_text("fake", encoding="utf-8")
    script = installer_core._write_uninstaller(app_dir, [str(shortcut)])

    _run_uninstaller(script)

    assert not app_dir.exists()
    assert not shortcut.exists()


@pytest.mark.skipif(not _oem_ready(), reason="needs an OEM code page")
def test_uninstaller_handles_a_non_ascii_folder(tmp_path):
    app_dir = tmp_path / "Programs" / "UmbraForge caf\u00e9"
    (app_dir / "assets").mkdir(parents=True)
    (app_dir / "assets" / "mark.txt").write_text("x", encoding="utf-8")
    script = installer_core._write_uninstaller(app_dir, [])

    _run_uninstaller(script)

    assert not app_dir.exists()


def test_setup_cli_reports_a_missing_payload(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(installer_core.sys, "frozen", True, raising=False)
    monkeypatch.setattr(installer_core, "payload_archive", lambda: None)

    code = installer_core.main(["--quiet", "--app-dir",
                                str(tmp_path / "install")])

    assert code == 1
    assert "payload" in capsys.readouterr().err
