"""Optional add-on discovery for UmbraForge.

The MIT core ships no paid features. A private add-on package (``umbraforge_pro``)
adds them at runtime, and every one of its entry points is gated by a signed
licence checked in :mod:`umbraforge.licensing`.

Nothing here hides code. The point is different: the public tree contains no
paid implementation to copy, and the paid implementation refuses to run unless
the machine holds a valid WinterGate licence. See ``OPEN_CORE.md``.

Add-on contract
---------------
A package exposes ``register(registry)`` and calls::

    registry.addon("umbraforge-pro", "1.0.0", features=("batch",))
    registry.add_menu_action("Add-ons", "Batch export...", callback,
                             feature="batch")
    registry.add_hook("render.after", callback, feature="batch")

Handlers must call ``licensing.require("batch")`` themselves; registration alone
is not an authorisation check.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import licensing

PRODUCT = "umbraforge"
ENTRY_POINT_GROUP = "umbraforge.addons"
OPTIONAL_MODULES = ("umbraforge_pro", "umbraforge_addons")
BUNDLED_DIR = "addons"

__all__ = ["AddOn", "MenuAction", "Registry", "registry", "load"]


@dataclass
class AddOn:
    name: str
    version: str = "0.0.0"
    vendor: str = ""
    description: str = ""
    features: tuple[str, ...] = ()
    enabled: bool = True

    @property
    def label(self) -> str:
        return f"{self.name} {self.version}".strip()


@dataclass
class MenuAction:
    menu: str
    label: str
    callback: Callable[[], Any]
    feature: str | None = None
    tooltip: str = ""


class Registry:
    """Collects contributions from installed add-ons."""

    def __init__(self) -> None:
        self.addons: list[AddOn] = []
        self.menu_actions: list[MenuAction] = []
        self.errors: list[str] = []
        self._hooks: dict[str, list[tuple[Callable[..., Any], str | None]]] = {}
        self._loaded = False

    # ---------------------------------------------------------- discovery
    def _candidates(self) -> list[tuple[str, Callable[[], Any]]]:
        candidates: list[tuple[str, Callable[[], Any]]] = []
        try:
            entry_points = importlib.metadata.entry_points()
            selected = (entry_points.select(group=ENTRY_POINT_GROUP)
                        if hasattr(entry_points, "select")
                        else entry_points.get(ENTRY_POINT_GROUP, []))
            for entry in selected:
                candidates.append((entry.name, entry.load))
        except Exception as exc:  # noqa: BLE001 - optional metadata
            self.errors.append(f"entry points unavailable: {exc}")

        for name in OPTIONAL_MODULES:
            try:
                if importlib.util.find_spec(name) is not None:
                    candidates.append((name, lambda name=name: importlib.import_module(name)))
            except (ImportError, ValueError):
                continue

        # A release can drop add-ons next to the package without installing them.
        bundled = Path(__file__).resolve().parent / BUNDLED_DIR
        if bundled.is_dir():
            for path in sorted(bundled.iterdir()):
                if path.is_dir() and (path / "__init__.py").is_file():
                    candidates.append((path.name, self._import_path(path)))
        return candidates

    @staticmethod
    def _import_path(path: Path) -> Callable[[], Any]:
        def load() -> Any:
            spec = importlib.util.spec_from_file_location(
                f"{PRODUCT}_addon_{path.name}", path / "__init__.py",
                submodule_search_locations=[str(path)],
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load add-on at {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
        return load

    def load(self) -> "Registry":
        if self._loaded:
            return self
        self._loaded = True
        for name, loader in self._candidates():
            try:
                module = loader()
                register = getattr(module, "register", None)
                if not callable(register):
                    raise TypeError("add-on has no register(registry) function")
                register(self)
            except Exception as exc:  # noqa: BLE001 - one bad add-on is isolated
                self.errors.append(f"{name}: {exc}")
        return self

    # ---------------------------------------------------------- permissions
    def allows(self, feature: str | None) -> bool:
        if feature in (None, "", "*"):
            return True
        licence = licensing.active_license()
        return bool(licence and licence.allows(feature))

    # ---------------------------------------------------------- contributions
    def addon(
        self,
        name: str,
        version: str = "0.0.0",
        *,
        vendor: str = "",
        description: str = "",
        features: tuple[str, ...] = (),
        enabled: bool | None = None,
    ) -> AddOn:
        if enabled is None:
            enabled = all(self.allows(feature) for feature in features)
        record = AddOn(name, version, vendor, description, tuple(features), enabled)
        self.addons.append(record)
        return record

    def add_menu_action(
        self,
        menu: str,
        label: str,
        callback: Callable[[], Any],
        *,
        feature: str | None = None,
        tooltip: str = "",
    ) -> MenuAction:
        action = MenuAction(menu, label, callback, feature, tooltip)
        self.menu_actions.append(action)
        return action

    def add_hook(
        self,
        name: str,
        callback: Callable[..., Any],
        *,
        feature: str | None = None,
    ) -> None:
        self._hooks.setdefault(name, []).append((callback, feature))

    def run(self, name: str, value: Any, context: Any = None) -> Any:
        """Pass ``value`` through every licensed hook registered for ``name``."""
        for callback, feature in self._hooks.get(name, []):
            if not self.allows(feature):
                continue
            try:
                result = callback(value, context)
            except Exception as exc:  # noqa: BLE001 - a hook must not crash the app
                self.errors.append(f"hook {name}: {exc}")
                continue
            if result is not None:
                value = result
        return value

    def menu_entries(self, menu: str) -> list[MenuAction]:
        return [action for action in self.menu_actions if action.menu == menu]

    @property
    def pro_available(self) -> bool:
        return any(record.enabled and record.features for record in self.addons)


registry = Registry()


def load() -> Registry:
    """Discover add-ons once and return the shared registry."""
    return registry.load()
