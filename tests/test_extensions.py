"""Add-on discovery and licence gating."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from umbraforge import extensions, licensing


def _licence(features: set[str]) -> licensing.License:
    return licensing.License(
        product="umbraforge", edition="pro", licensee="T", email="", license_id="",
        issued=None, expires=None, features=frozenset(features), max_machines=1,
        machine=None, raw="",
    )


def test_registry_without_licence_denies_gated_contributions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(licensing, "active_license", lambda **_: None)
    registry = extensions.Registry()
    seen: list[str] = []
    registry.addon("umbraforge-pro", "1.0", features=("batch",))
    registry.add_menu_action("Add-ons", "Batch", lambda: seen.append("batch"),
                             feature="batch")

    assert registry.allows("batch") is False
    assert registry.allows(None) is True
    assert registry.addons[0].enabled is False

    registry.run("render.after", "value")
    assert seen == []


def test_registry_with_licence_enables_only_covered_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(licensing, "active_license", lambda **_: _licence({"batch"}))
    registry = extensions.Registry()
    registry.addon("umbraforge-pro", "1.0", features=("batch",))
    registry.addon("other", "1.0", features=("studio",))

    assert registry.addons[0].enabled is True
    assert registry.addons[1].enabled is False
    assert registry.allows("batch") is True
    assert registry.allows("studio") is False


def test_hooks_chain_and_skip_unlicensed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(licensing, "active_license", lambda **_: _licence({"batch"}))
    registry = extensions.Registry()
    registry.add_hook("render.after", lambda value, ctx: value + 1, feature="batch")
    registry.add_hook("render.after", lambda value, ctx: value + 10, feature="studio")
    registry.add_hook("render.after", lambda value, ctx: value * 2)

    assert registry.run("render.after", 1) == 4


def test_failing_hook_is_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(licensing, "active_license", lambda **_: _licence({"*"}))

    def explode(value, ctx):
        raise RuntimeError("boom")

    registry = extensions.Registry()
    registry.add_hook("render.after", explode)
    registry.add_hook("render.after", lambda value, ctx: value + 1)

    assert registry.run("render.after", 1) == 2
    assert any("boom" in error for error in registry.errors)


def test_bundled_addon_imports_and_registers(tmp_path: Path) -> None:
    package = tmp_path / "demo_addon"
    package.mkdir()
    (package / "__init__.py").write_text(
        "def register(registry):\n"
        "    registry.addon('demo', '2.0', features=('batch',))\n",
        encoding="utf-8",
    )
    module = extensions.Registry._import_path(package)()
    registry = extensions.Registry()
    module.register(registry)

    assert registry.addons[0].name == "demo"
    assert registry.addons[0].version == "2.0"
    sys.modules.pop("umbraforge_addon_demo_addon", None)


def test_broken_addon_does_not_break_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken():
        raise RuntimeError("missing dependency")

    registry = extensions.Registry()
    monkeypatch.setattr(registry, "_candidates", lambda: [("broken", broken)])
    registry.load()

    assert registry.addons == []
    assert any("missing dependency" in error for error in registry.errors)
