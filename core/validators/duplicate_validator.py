import re
from datetime import date, datetime
from typing import Any, Optional
from core.models import Transaction
from core.validators.base import BaseTransactionValidator, ValidationResult


def normalize_amount(value: Any) -> float:
    """
    Normalizes monetary values to a rounded float (2 decimals).
    Handles raw floats, ints, and currency strings formatted like '$2,300.00', '1,200', etc.
    """
    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return round(abs(float(value)), 2)

    cleaned = str(value).replace("$", "").replace("€", "").replace(",", "").strip()
    # Match numeric float/int pattern
    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if match:
        try:
            return round(abs(float(match.group(0))), 2)
        except ValueError:
            return 0.0
    return 0.0


def normalize_date(value: Any) -> str:
    """
    Normalizes dates from datetime.date, datetime.datetime, or diverse string formats to YYYY-MM-DD.
    """
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")

    date_str = str(value).strip()
    if not date_str:
        return date.today().isoformat()

    # Attempt common date patterns
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback: extract YYYY-MM-DD via regex if embedded in longer string
    iso_match = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
    if iso_match:
        return iso_match.group(0)

    return date_str


def normalize_text(value: Optional[str]) -> str:
    """
    Cleans text by removing accents, special characters, and collapsing whitespace.
    """
    if not value:
        return ""

    text = str(value).lower()
    # Replace vowels with accents
    accents_map = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"
    }
    for accented, plain in accents_map.items():
        text = text.replace(accented, plain)

    # Keep alphanumeric and spaces only
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def generate_transaction_fingerprint(
    date_val: Any,
    amount_val: Any,
    tx_type: Optional[str] = None,
    source: Optional[str] = None,
    destination: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    Constructs a deterministic, normalized fingerprint for a transaction.
    Enables reliable deduplication between raw storage records and incoming models.
    """
    norm_date = normalize_date(date_val)
    norm_amount = f"{normalize_amount(amount_val):.2f}"
    norm_type = normalize_text(tx_type or "")
    norm_source = normalize_text(source or "")
    norm_dest = normalize_text(destination or "")
    norm_desc = normalize_text(description or "")

    return f"{norm_date}_{norm_amount}_{norm_type}_{norm_source}_{norm_dest}_{norm_desc}"


class DuplicateValidator(BaseTransactionValidator):
    """
    Validates that a transaction is not a duplicate against existing storage records
    or against other transactions within the same ingestion batch.
    """

    def validate(self, transaction: Transaction, context: dict) -> ValidationResult:
        existing_fingerprints: set = context.setdefault("existing_fingerprints", set())

        fingerprint = generate_transaction_fingerprint(
            date_val=transaction.date,
            amount_val=transaction.amount,
            tx_type=transaction.transaction_type,
            source=transaction.source_account,
            destination=transaction.destination_account,
            description=transaction.description,
        )

        if fingerprint in existing_fingerprints:
            return ValidationResult(
                is_valid=False,
                is_duplicate=True,
                error_message="Transacción duplicada detectada.",
                transaction=transaction,
            )

        # Track this fingerprint so intra-batch duplicates are also detected
        existing_fingerprints.add(fingerprint)
        return ValidationResult(is_valid=True, transaction=transaction)
