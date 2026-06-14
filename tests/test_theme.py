"""Tests for WCAG 2.1 relative luminance and on-primary text contrast."""

from __future__ import annotations

import pytest

from app.pdf.theme import (
    DEFAULT_PRIMARY_COLOR,
    ON_PRIMARY_DARK,
    WHITE,
    on_primary_text_color,
    relative_luminance,
)


def test_relative_luminance_black_is_zero():
    assert relative_luminance("#000000") == pytest.approx(0.0, abs=1e-6)


def test_relative_luminance_white_is_one():
    assert relative_luminance("#FFFFFF") == pytest.approx(1.0, abs=1e-6)


def test_relative_luminance_mid_gray():
    assert relative_luminance("#808080") == pytest.approx(0.2159, abs=1e-3)


def test_on_primary_dark_background_uses_white_text():
    assert on_primary_text_color("#000000") == WHITE


def test_on_primary_light_background_uses_dark_text():
    assert on_primary_text_color("#FFFFFF") == ON_PRIMARY_DARK


def test_on_primary_default_primary_uses_white_text():
    """The default blue primary keeps the current white-on-primary look."""
    assert on_primary_text_color(DEFAULT_PRIMARY_COLOR) == WHITE


def test_on_primary_bright_yellow_uses_dark_text():
    assert on_primary_text_color("#FFFF00") == ON_PRIMARY_DARK


def test_on_primary_mid_gray_uses_dark_text():
    """#808080's luminance (~0.216) is above the 0.179 threshold, so dark
    text yields the better contrast ratio (~4.31:1 vs ~3.95:1 for white)."""
    assert on_primary_text_color("#808080") == ON_PRIMARY_DARK


def test_on_primary_very_dark_blue_uses_white_text():
    assert on_primary_text_color("#1A1A2E") == WHITE


def test_on_primary_light_border_color_uses_dark_text():
    assert on_primary_text_color("#D0D8E8") == ON_PRIMARY_DARK
