"""Amounts travel as integer cents and land as exact decimals — never as a float."""

from __future__ import annotations

from decimal import Decimal

import pyarrow as pa

AMOUNT_SCALE = 2
AMOUNT_PRECISION = 18
AMOUNT_TYPE = pa.decimal128(AMOUNT_PRECISION, AMOUNT_SCALE)


def euros(cents: int) -> Decimal:
    """Return `cents` as an exact amount in euros."""
    return Decimal(cents).scaleb(-AMOUNT_SCALE)
