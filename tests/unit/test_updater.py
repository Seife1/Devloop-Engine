import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from learnloop.updater import (
    parse_semver,
    is_newer_version,
    format_update_banner,
    check_for_updates,
    cmd_update,
)


def test_parse_semver():
    assert parse_semver("0.8.0") == (0, 8, 0)
    assert parse_semver("v0.7.7") == (0, 7, 7)
    assert parse_semver("1.0.0-beta.1") == (1, 0, 0)
    assert parse_semver("2") == (2, 0, 0)


def test_is_newer_version():
    assert is_newer_version("0.8.0", "0.7.7") is True
    assert is_newer_version("0.7.7", "0.7.7") is False
    assert is_newer_version("0.7.6", "0.7.7") is False
    assert is_newer_version("1.0.0", "0.8.0") is True


def test_format_update_banner():
    banner = format_update_banner("0.8.0", use_color=False)
    assert "Update available" in banner
    assert "learnloop update" in banner
    assert "v0.8.0" in banner


def test_check_for_updates_uses_cache(tmp_path: Path):
    cache_file = tmp_path / "update_check.json"
    cache_data = {
        "last_checked": 9999999999.0,  # Far in the future -> cache hit
        "latest_version": "9.9.9",
        "changelog_url": "https://example.com",
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    with patch("learnloop.updater.get_cache_path", return_value=cache_file):
        has_update, latest, changelog = check_for_updates(force=False)
        assert has_update is True
        assert latest == "9.9.9"
        assert changelog == "https://example.com"


def test_cmd_update_already_up_to_date(capsys):
    with patch("learnloop.updater.check_for_updates", return_value=(False, "0.7.7", None)):
        code = cmd_update(force=False)
        assert code == 0
        captured = capsys.readouterr()
        assert "already up-to-date" in captured.out
