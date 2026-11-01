"""Преобразование котировок T-Invest API в числа."""

from decimal import Decimal


def quotation_to_float(quotation) -> float:
    """Собрать units + nano в float (рыночная цена)."""
    return float(Decimal(quotation.units) + Decimal(quotation.nano) / Decimal(1_000_000_000))
