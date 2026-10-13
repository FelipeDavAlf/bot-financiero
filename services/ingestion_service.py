from dataclasses import dataclass, field
import logging
from typing import List, Optional
from core.models import Transaction
from core.validators.pipeline import TransactionValidationPipeline, create_default_pipeline
from services.sheets_service import SheetsService


@dataclass
class IngestionResult:
    """Represents the outcome of a single transaction ingestion."""
    success: bool
    transaction: Optional[Transaction] = None
    is_duplicate: bool = False
    error_message: Optional[str] = None


@dataclass
class BatchIngestionResult:
    """Represents the outcome of a batch transaction ingestion."""
    added_count: int = 0
    duplicate_count: int = 0
    invalid_count: int = 0
    accepted_transactions: List[Transaction] = field(default_factory=list)
    duplicate_transactions: List[Transaction] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class TransactionIngestionService:
    """
    Unified Ingestion Service (Facade & Orchestrator Pattern).
    Applies the validation pipeline and coordinates persistence across any input source:
    Telegram text messages, voice notes, documents (PDF/CSV/Excel), and future email parsers.
    """

    def __init__(
        self,
        sheets_service: SheetsService,
        pipeline: Optional[TransactionValidationPipeline] = None,
    ):
        self.sheets_service = sheets_service
        self.pipeline = pipeline or create_default_pipeline()

    def ingest_transaction(self, transaction: Transaction) -> IngestionResult:
        """
        Ingests a single transaction through the validation pipeline and saves it.
        """
        try:
            existing_fingerprints = self.sheets_service.get_existing_fingerprints()
            context = {"existing_fingerprints": existing_fingerprints}

            validation_result = self.pipeline.validate(transaction, context)
            if not validation_result.is_valid:
                return IngestionResult(
                    success=False,
                    transaction=transaction,
                    is_duplicate=validation_result.is_duplicate,
                    error_message=validation_result.error_message or "Validación fallida.",
                )

            self.sheets_service.append_raw_row([
                transaction.date.isoformat(),
                transaction.transaction_type,
                transaction.amount,
                transaction.source_account or "",
                transaction.destination_account or "",
                transaction.category,
                transaction.subcategory,
                transaction.description,
            ])

            return IngestionResult(success=True, transaction=transaction)
        except Exception as exc:
            logging.error(f"Error ingesting single transaction: {exc}")
            return IngestionResult(
                success=False,
                transaction=transaction,
                error_message=f"Error interno al guardar: {exc}",
            )

    def ingest_batch(self, transactions: List[Transaction]) -> BatchIngestionResult:
        """
        Ingests a list of transactions through the validation pipeline in batch,
        filtering out duplicates and invalid items before saving.
        """
        result = BatchIngestionResult()
        if not transactions:
            return result

        try:
            existing_fingerprints = self.sheets_service.get_existing_fingerprints()
            context = {"existing_fingerprints": existing_fingerprints}

            valid_transactions: List[Transaction] = []
            rows_to_save = []

            for tx in transactions:
                val_res = self.pipeline.validate(tx, context)
                if val_res.is_duplicate:
                    result.duplicate_count += 1
                    result.duplicate_transactions.append(tx)
                elif not val_res.is_valid:
                    result.invalid_count += 1
                    if val_res.error_message:
                        result.errors.append(val_res.error_message)
                else:
                    valid_transactions.append(tx)
                    rows_to_save.append([
                        tx.date.isoformat(),
                        tx.transaction_type,
                        tx.amount,
                        tx.source_account or "",
                        tx.destination_account or "",
                        tx.category,
                        tx.subcategory,
                        tx.description,
                    ])

            if rows_to_save:
                self.sheets_service.append_raw_rows(rows_to_save)

            result.added_count = len(valid_transactions)
            result.accepted_transactions = valid_transactions
            return result
        except Exception as exc:
            logging.error(f"Error ingesting batch: {exc}")
            result.errors.append(f"Error al guardar lote en la base de datos: {exc}")
            return result
