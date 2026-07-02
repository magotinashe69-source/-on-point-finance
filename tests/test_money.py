"""Tests for the money helpers — the most important code in the app."""

import pytest

from app.money import str_to_cents, cents_to_str


# --- str_to_cents: happy paths ---------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("1500.00", 150000),
        ("1,500.00", 150000),   # thousands separator
        ("1500", 150000),       # no decimals
        ("1500.5", 150050),     # one decimal
        ("0", 0),
        ("0.05", 5),
        ("1,234,567.89", 123456789),
        ("  1500.00  ", 150000),  # surrounding whitespace
    ],
)
def test_str_to_cents_valid(text, expected):
    assert str_to_cents(text) == expected


# --- str_to_cents: rejected input ------------------------------------------

@pytest.mark.parametrize("bad", ["", "   ", "abc", "12.3.4", None])
def test_str_to_cents_rejects_garbage(bad):
    with pytest.raises(ValueError):
        str_to_cents(bad)


def test_str_to_cents_rejects_negative():
    with pytest.raises(ValueError):
        str_to_cents("-5.00")


def test_str_to_cents_rejects_too_many_decimals():
    with pytest.raises(ValueError):
        str_to_cents("1.005")


# --- cents_to_str ----------------------------------------------------------

@pytest.mark.parametrize(
    "cents, expected",
    [
        (450000, "4,500 MT"),       # whole meticais, no decimals
        (150000, "1,500 MT"),
        (0, "0 MT"),
        (5, "0 MT"),                # 0.05 MT rounds to 0 whole meticais
        (123456789, "1,234,568 MT"),  # 1,234,567.89 rounds half-up
        (-150000, "-1,500 MT"),     # negative balance keeps its sign
    ],
)
def test_cents_to_str(cents, expected):
    assert cents_to_str(cents) == expected


def test_cents_to_str_rejects_non_integer():
    with pytest.raises(ValueError):
        cents_to_str(1500.0)  # float is not allowed
    with pytest.raises(ValueError):
        cents_to_str(True)    # bool is not a money amount


# --- round trip ------------------------------------------------------------

# The display now shows whole meticais only (no centavos), so the round trip
# holds for whole-metical amounts — the amounts real fees actually use.
@pytest.mark.parametrize("text", ["0", "9", "1500", "1,234,567", "1000000"])
def test_round_trip_whole_meticais(text):
    cents = str_to_cents(text)
    displayed = cents_to_str(cents)
    # Stripping the " MT" suffix and re-parsing must give the same cents back.
    assert str_to_cents(displayed.replace(" MT", "")) == cents
