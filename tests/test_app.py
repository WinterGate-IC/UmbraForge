"""Bootstrap behaviour: creating the app, opening targets, CLI flags."""

from __future__ import annotations

from pathlib import Path

from umbraforge import app, branding, templates
from umbraforge.layers import Design


def test_create_app_applies_branding_and_theme(qapp):
    created = app.create_app(["umbraforge-tests"])
    assert created is qapp
    assert created.applicationName() == branding.APP_NAME
    assert created.organizationName() == app.ORGANISATION
    assert created.organizationDomain() == app.ORGANISATION_DOMAIN
    assert created.applicationVersion() == branding.VERSION
    assert created.styleSheet()


def test_open_target_loads_a_saved_design(tmp_path):
    design = templates.build("signal_lost")
    design.name = "Signal round trip"
    path = design.save(tmp_path / "roundtrip.umbra")

    loaded, target, error = app.open_target(str(path))
    assert error == ""
    assert target == path
    assert isinstance(loaded, Design)
    assert loaded.name == "Signal round trip"
    assert loaded.to_dict() == design.to_dict()


def test_open_target_reports_a_bad_path(tmp_path):
    missing = tmp_path / "nothing.umbra"
    loaded, target, error = app.open_target(str(missing))
    assert loaded is None
    assert target is None
    assert "Could not open" in error


def test_help_and_version_short_circuit(qapp, capsys):
    assert app.main(["--version"]) == 0
    out = capsys.readouterr().out
    assert branding.APP_NAME in out
    assert branding.VERSION in out

    assert app.main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "Usage" in out
