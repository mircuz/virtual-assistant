"""Unit tests for booking_engine.db.connection helper functions."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from booking_engine.db.connection import _rows_to_dicts, _fetchone_dict, get_table


class TestRowsToDicts:
    def test_empty_result(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        assert _rows_to_dicts(cursor) == []

    def test_single_row(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [("val1", 42)]
        cursor.description = [("col_a",), ("col_b",)]
        result = _rows_to_dicts(cursor)
        assert result == [{"col_a": "val1", "col_b": 42}]

    def test_multiple_rows(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [("a", 1), ("b", 2)]
        cursor.description = [("name",), ("num",)]
        result = _rows_to_dicts(cursor)
        assert len(result) == 2
        assert result[0] == {"name": "a", "num": 1}
        assert result[1] == {"name": "b", "num": 2}

    def test_none_values(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(None, "x")]
        cursor.description = [("a",), ("b",)]
        result = _rows_to_dicts(cursor)
        assert result == [{"a": None, "b": "x"}]


class TestFetchoneDict:
    def test_no_row(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        assert _fetchone_dict(cursor) is None

    def test_one_row(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("hello", 99)
        cursor.description = [("greeting",), ("code",)]
        result = _fetchone_dict(cursor)
        assert result == {"greeting": "hello", "code": 99}


class TestGetTable:
    @patch("booking_engine.db.connection._settings", None)
    def test_no_settings_returns_bare_name(self):
        assert get_table("shops") == "shops"

    def test_with_settings_returns_qualified(self):
        mock_settings = MagicMock()
        mock_settings.table_prefix = "mircom_test.virtual_assistant"
        with patch("booking_engine.db.connection._settings", mock_settings):
            assert get_table("shops") == "mircom_test.virtual_assistant.shops"
