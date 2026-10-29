"""Licence verification: signature, expiry, product and machine binding."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from umbraforge import licensing

FIXTURES = Path(__file__).parent / "fixtures"
BEFORE_EXPIRY = dt.date(2019, 6, 1)
AFTER_EXPIRY = dt.date(2026, 10, 28)


def _token(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8").strip()


def test_valid_signature_parses() -> None:
    licence = licensing.parse_token(_token("expired.license"), today=BEFORE_EXPIRY)
    assert licence.product == "umbraforge"
    assert licence.licensee == "Test Fixture"
    assert licence.features == {"batch", "templates"}
    assert licence.allows("batch")
    assert licence.allows("*")
    assert not licence.allows("studio")
    assert licence.days_left(BEFORE_EXPIRY) > 0


def test_expired_token_is_rejected() -> None:
    with pytest.raises(licensing.LicenseError, match="expired"):
        licensing.parse_token(_token("expired.license"), today=AFTER_EXPIRY)


def test_allow_expired_is_opt_in() -> None:
    licence = licensing.parse_token(
        _token("expired.license"), today=AFTER_EXPIRY, allow_expired=True
    )
    assert licence.expired()


def test_tampered_payload_fails_signature() -> None:
    prefix, payload, signature = _token("expired.license").split(".")
    tampered = payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB")
    with pytest.raises(licensing.LicenseError, match="signature"):
        licensing.parse_token(f"{prefix}.{tampered}.{signature}", today=BEFORE_EXPIRY)


def test_wrong_product_is_rejected() -> None:
    with pytest.raises(licensing.LicenseError, match="not a umbraforge licence|not 'umbraforge'"):
        licensing.parse_token(_token("other-product.license"), today=BEFORE_EXPIRY)


def test_machine_binding() -> None:
    bound = _token("expired-bound.license")
    licence = licensing.parse_token(
        bound, machine="test-machine-0001", today=BEFORE_EXPIRY
    )
    assert licence.machine == "test-machine-0001"
    with pytest.raises(licensing.LicenseError, match="different machine"):
        licensing.parse_token(bound, machine="some-other-machine", today=BEFORE_EXPIRY)


def test_malformed_tokens_are_rejected() -> None:
    for token in ("", "nope", "UF1.aaa", "UF1.aaa.bbb.ccc", "XX1.aaa.bbb"):
        with pytest.raises(licensing.LicenseError):
            licensing.parse_token(token)


def test_require_without_licence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(licensing, "active_license", lambda **_: None)
    with pytest.raises(licensing.LicenseError, match="needs a valid licence"):
        licensing.require("batch")
    assert licensing.allows("batch") is False


def test_require_with_licence(monkeypatch: pytest.MonkeyPatch) -> None:
    licence = licensing.License(
        product="umbraforge", edition="pro", licensee="T", email="", license_id="",
        issued=None, expires=None, features=frozenset({"batch"}), max_machines=1,
        machine=None,
    )
    monkeypatch.setattr(licensing, "active_license", lambda **_: licence)
    assert licensing.require("batch") is licence
    with pytest.raises(licensing.LicenseError, match="does not include"):
        licensing.require("studio")


def test_install_and_revoke(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "license.key"
    monkeypatch.setattr(licensing, "default_license_path", lambda: target)
    monkeypatch.delenv("UMBRAFORGE_LICENSE", raising=False)
    fake = licensing.License(
        product="umbraforge", edition="pro", licensee="T", email="", license_id="",
        issued=None, expires=None, features=frozenset({"*"}), max_machines=1,
        machine=None, raw="UF1.fake.sig",
    )
    monkeypatch.setattr(licensing, "parse_token", lambda *a, **k: fake)

    written = licensing.install_license("anything")
    assert written == target
    assert target.read_text(encoding="utf-8").strip() == "UF1.fake.sig"
    assert licensing.revoke_license() is True
    assert not target.exists()
    assert licensing.revoke_license() is False


def test_describe_status_without_licence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(licensing, "active_license", lambda **_: None)
    status = licensing.describe_status()
    assert status["licensed"] is False
    assert status["edition"] == "community"
    assert status["features"] == []
    assert status["machine"]


def test_machine_id_is_stable_and_not_the_raw_guid() -> None:
    first = licensing.machine_id()
    assert first == licensing.machine_id()
    assert len(first) == 32
    assert ":" not in first
