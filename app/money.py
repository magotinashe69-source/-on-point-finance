"""Money helpers for On Point Finance.

Money is ALWAYS stored as an integer number of centavos (1,500.00 MT -> 150000).
These two functions are the ONLY place money crosses between a display string and
the stored integer. Use them everywhere; never do ad-hoc float maths on money.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CURRENCY_SUFFIX = "MT"


def str_to_cents(value: str) -> int:
    """Convert a human-typed amount into integer centavos.

    Accepts forms like "1500", "1500.00" and "1,500.00" (commas are treated as
    thousands separators). Raises ValueError for empty, non-numeric, negative,
    or over-precise (more than two decimal places) input.
    """
    if value is None:
        raise ValueError("Amount is required.")

    text = str(value).strip().replace(",", "")
    if text == "":
        raise ValueError("Amount is required.")

    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"'{value}' is not a valid amount.")

    if not amount.is_finite():
        raise ValueError("Amount must be a finite number.")
    if amount < 0:
        raise ValueError("Amount cannot be negative.")
    if -amount.as_tuple().exponent > 2:
        raise ValueError("Amount cannot have more than two decimal places.")

    cents = (amount * 100).to_integral_value(rounding=ROUND_HALF_UP)
    return int(cents)


def cents_to_str(cents: int, suffix: str = CURRENCY_SUFFIX) -> str:
    """Format integer centavos for display, e.g. 150000 -> "1,500.00 MT".

    Negative values keep their sign (useful for a negative balance).
    """
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise ValueError("cents must be an integer number of centavos.")

    amount = Decimal(cents) / Decimal(100)
    formatted = f"{amount:,.2f}"
    return f"{formatted} {suffix}".strip()


def cents_to_major(cents: int) -> float:
    """Convert integer centavos to major MT units for display, e.g. 150000 -> 1500.0.

    For charts/JSON only — storage and maths always stay in integer centavos.
    """
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise ValueError("cents must be an integer number of centavos.")
    return float(Decimal(cents) / Decimal(100))
