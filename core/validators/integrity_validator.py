from datetime import date, timedelta
from core.models import Transaction
from core.validators.base import BaseTransactionValidator, ValidationResult

VALID_TRANSACTION_TYPES = {"Ingreso", "Gasto", "Traspaso"}


class IntegrityValidator(BaseTransactionValidator):
    """
    Validates data integrity and sanity checks on a transaction.
    Ensures positive amounts, valid movement types, non-empty descriptions, and reasonable dates.
    """

    def validate(self, transaction: Transaction, context: dict) -> ValidationResult:
        if transaction.amount <= 0:
            return ValidationResult(
                is_valid=False,
                error_message="El monto de la transacción debe ser mayor a cero.",
                transaction=transaction,
            )

        if transaction.transaction_type not in VALID_TRANSACTION_TYPES:
            return ValidationResult(
                is_valid=False,
                error_message=f"Tipo de transacción '{transaction.transaction_type}' no reconocido.",
                transaction=transaction,
            )

        if not transaction.description or not transaction.description.strip():
            return ValidationResult(
                is_valid=False,
                error_message="La descripción de la transacción no puede estar vacía.",
                transaction=transaction,
            )

        # Allow up to 1 day ahead to tolerate minor time zone variations
        max_allowed_date = date.today() + timedelta(days=1)
        min_allowed_date = date(2000, 1, 1)

        if transaction.date > max_allowed_date:
            return ValidationResult(
                is_valid=False,
                error_message=f"La fecha ({transaction.date}) no puede ser una fecha futura.",
                transaction=transaction,
            )

        if transaction.date < min_allowed_date:
            return ValidationResult(
                is_valid=False,
                error_message=f"La fecha ({transaction.date}) es anterior al límite permitido.",
                transaction=transaction,
            )

        return ValidationResult(is_valid=True, transaction=transaction)
