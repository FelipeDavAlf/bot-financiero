from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional
from core.models import Transaction


@dataclass
class ValidationResult:
    """
    Represents the result of validating a transaction.
    User-facing error messages are strictly in Spanish.
    """
    is_valid: bool
    is_duplicate: bool = False
    error_message: Optional[str] = None
    transaction: Optional[Transaction] = None


class BaseTransactionValidator(ABC):
    """
    Strategy interface for transaction validators (Strategy Pattern).
    Implementations validate specific business rules (deduplication, schema integrity, etc.).
    """

    @abstractmethod
    def validate(self, transaction: Transaction, context: dict) -> ValidationResult:
        """
        Validates a single transaction against business rules.
        
        Args:
            transaction: The Transaction object to validate.
            context: Shared validation context (e.g. existing signatures, batch state).

        Returns:
            ValidationResult indicating validity, duplicate status, and error messages.
        """
        pass
