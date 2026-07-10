"""Exercise offline fallback at the spelling-generator boundary."""

from __future__ import annotations

import importlib
import pathlib
import typing as typ
import urllib.error

import pytest

if typ.TYPE_CHECKING:
    import types

NETWORK_UNAVAILABLE = "network unavailable"


@pytest.fixture
def generator(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import the standalone generator with its sibling modules visible."""
    scripts = pathlib.Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    return importlib.import_module("generate_typos_config")


def unavailable_remote(*_args: object, **_kwargs: object) -> None:
    """Model a remote dictionary authority that cannot be reached."""
    raise urllib.error.URLError(NETWORK_UNAVAILABLE)


def test_remote_failure_reuses_valid_tracked_config(
    tmp_path: pathlib.Path,
    generator: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A clean offline checkout can check its committed generated policy."""
    output = tmp_path / "typos.toml"
    output.write_text("[default.extend-words]\n", encoding="utf-8")
    monkeypatch.setattr(generator.rollout, "refresh_base", unavailable_remote)

    result = generator.main(output=output, repository=tmp_path)

    assert result.status == "tracked-config"
    assert result.cache == output


def test_remote_failure_rejects_missing_tracked_config(
    tmp_path: pathlib.Path,
    generator: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remote failure remains visible when no valid generated policy exists."""
    output = tmp_path / "typos.toml"
    monkeypatch.setattr(generator.rollout, "refresh_base", unavailable_remote)

    with pytest.raises(urllib.error.URLError, match="network unavailable"):
        generator.main(output=output, repository=tmp_path)
