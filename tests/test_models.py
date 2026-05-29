from datetime import date
import pytest
from pydantic import ValidationError
from core.models import Transaction

def test_valid_transaction():
    """Validates that a correctly formatted transaction is parsed without errors."""
    transaction = Transaction(
        date=date(2026, 5, 28),
        transaction_type="Gasto",
        amount=150.0,
        source_account="Tarjeta Débito",
        category="Comida",
        subcategory="Pizza",
        description="Tacos"
    )
    assert transaction.amount == 150.0
    assert transaction.transaction_type == "Gasto"
    assert transaction.subcategory == "Pizza"

def test_invalid_negative_amount():
    """Validates that Pydantic raises a ValidationError when the amount is negative."""
    with pytest.raises(ValidationError):
        Transaction(
            date=date(2026, 5, 28),
            transaction_type="Gasto",
            amount=-50.0,  # Esto debería fallar según nuestras reglas de Pydantic
            category="Comida",
            subcategory="Pizza",
            description="Error Test"
        )