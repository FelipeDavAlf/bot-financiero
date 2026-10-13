from typing import List, Optional
from core.models import Transaction
from core.validators.base import BaseTransactionValidator, ValidationResult
from core.validators.integrity_validator import IntegrityValidator
from core.validators.duplicate_validator import DuplicateValidator


class TransactionValidationPipeline:
    """
    Pipeline pattern orchestrator for executing a sequence of transaction validators.
    Allows dynamic extension and addition of validation rules without modifying existing logic.
    """

    def __init__(self, validators: Optional[List[BaseTransactionValidator]] = None):
        self.validators: List[BaseTransactionValidator] = validators or []

    def add_validator(self, validator: BaseTransactionValidator) -> "TransactionValidationPipeline":
        """Adds a validator to the pipeline sequence."""
        self.validators.append(validator)
        return self

    def validate(self, transaction: Transaction, context: Optional[dict] = None) -> ValidationResult:
        """
        Executes all validators sequentially on a transaction.
        Short-circuits on the first failure.
        """
        ctx = context if context is not None else {}
        for validator in self.validators:
            result = validator.validate(transaction, ctx)
            if not result.is_valid:
                return result

        return ValidationResult(is_valid=True, transaction=transaction)


def create_default_pipeline() -> TransactionValidationPipeline:
    """
    Factory function providing standard production validation pipeline:
    1. Integrity check (amounts, dates, descriptions, types)
    2. Duplicate check (fingerprint matching against existing storage and batch)
    """
    pipeline = TransactionValidationPipeline()
    pipeline.add_validator(IntegrityValidator())
    pipeline.add_validator(DuplicateValidator())
    return pipeline
