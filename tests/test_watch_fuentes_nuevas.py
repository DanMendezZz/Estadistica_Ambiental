"""Tests del watcher semanal de fuentes nuevas (issue #15, scripts/watch_fuentes_nuevas.py)."""

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import watch_fuentes_nuevas as watcher  # noqa: E402


def _epoch(days_ago: float) -> int:
    return int(time.time() - days_ago * 24 * 3600)


class TestParseEpoch:
    def test_valid_epoch(self):
        assert watcher._parse_epoch(_epoch(1)) is not None

    def test_none_returns_none(self):
        assert watcher._parse_epoch(None) is None

    def test_empty_string_returns_none(self):
        assert watcher._parse_epoch("") is None

    def test_garbage_string_returns_none(self):
        assert watcher._parse_epoch("no-es-una-fecha") is None

    def test_nan_returns_none(self):
        assert watcher._parse_epoch(float("nan")) is None

    def test_out_of_range_returns_none(self):
        # No debe propagar OverflowError con epochs absurdos.
        assert watcher._parse_epoch(10**20) is None
        assert watcher._parse_epoch(-(10**20)) is None


class TestMain:
    def test_finds_dataset_within_window(self):
        df = pd.DataFrame(
            [{"name": "Nuevo", "url": "https://x", "organization": "IDEAM", "created": _epoch(1)}]
        )
        with patch.object(watcher, "list_datasets_co", return_value=df):
            assert watcher.main() == 1

    def test_ignores_dataset_outside_window(self):
        df = pd.DataFrame(
            [{"name": "Viejo", "url": "https://x", "organization": "IDEAM", "created": _epoch(100)}]
        )
        with patch.object(watcher, "list_datasets_co", return_value=df):
            assert watcher.main() == 0

    def test_invalid_created_value_is_skipped_not_fatal(self):
        df = pd.DataFrame(
            [{"name": "Raro", "url": "https://x", "organization": "IDEAM", "created": "basura"}]
        )
        with patch.object(watcher, "list_datasets_co", return_value=df):
            assert watcher.main() == 0

    def test_empty_source_returns_zero(self):
        with patch.object(watcher, "list_datasets_co", return_value=pd.DataFrame()):
            assert watcher.main() == 0
