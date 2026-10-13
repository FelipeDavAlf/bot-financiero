from datetime import date
from unittest.mock import MagicMock
from core.models import Transaction
from services.ingestion_service import TransactionIngestionService
from core.validators.duplicate_validator import generate_transaction_fingerprint


def test_ingest_single_transaction_success():
    mock_sheets = MagicMock()
    mock_sheets.get_existing_fingerprints.return_value = set()

    service = TransactionIngestionService(sheets_service=mock_sheets)

    tx = Transaction(
        date=date(2026, 9, 10),
        transaction_type="Gasto",
        amount=120.0,
        source_account="Efectivo",
        category="Alimentación",
        subcategory="Comida",
        description="Almuerzo",
    )

    result = service.ingest_transaction(tx)
    assert result.success
    assert not result.is_duplicate
    assert mock_sheets.append_raw_row.called


def test_ingest_single_transaction_duplicate():
    tx = Transaction(
        date=date(2026, 9, 10),
        transaction_type="Gasto",
        amount=120.0,
        source_account="Efectivo",
        category="Alimentación",
        subcategory="Comida",
        description="Almuerzo",
    )
    existing_fp = generate_transaction_fingerprint(
        date_val=tx.date,
        amount_val=tx.amount,
        tx_type=tx.transaction_type,
        source=tx.source_account,
        destination=tx.destination_account,
        description=tx.description,
    )

    mock_sheets = MagicMock()
    mock_sheets.get_existing_fingerprints.return_value = {existing_fp}

    service = TransactionIngestionService(sheets_service=mock_sheets)
    result = service.ingest_transaction(tx)

    assert not result.success
    assert result.is_duplicate
    assert not mock_sheets.append_raw_row.called


def test_ingest_batch_deduplication():
    # Pre-populate one existing transaction
    tx_existing = Transaction(
        date=date(2026, 9, 10),
        transaction_type="Gasto",
        amount=500.0,
        source_account="Tarjeta Débito BBVA",
        category="Alimentación",
        subcategory="Supermercado",
        description="Despensa semanal",
    )
    existing_fp = generate_transaction_fingerprint(
        date_val=tx_existing.date,
        amount_val=tx_existing.amount,
        tx_type=tx_existing.transaction_type,
        source=tx_existing.source_account,
        destination=tx_existing.destination_account,
        description=tx_existing.description,
    )

    mock_sheets = MagicMock()
    mock_sheets.get_existing_fingerprints.return_value = {existing_fp}

    service = TransactionIngestionService(sheets_service=mock_sheets)

    tx_new = Transaction(
        date=date(2026, 9, 11),
        transaction_type="Gasto",
        amount=80.0,
        source_account="Efectivo",
        category="Transporte",
        subcategory="Uber",
        description="Viaje al trabajo",
    )

    # Ingest a batch containing:
    # 1. tx_existing (already in Google Sheets -> duplicate)
    # 2. tx_new (new -> should be added)
    # 3. tx_new again (repeated within batch -> duplicate)
    batch = [tx_existing, tx_new, tx_new]
    batch_result = service.ingest_batch(batch)

    assert batch_result.added_count == 1
    assert batch_result.duplicate_count == 2
    assert len(batch_result.accepted_transactions) == 1
    assert batch_result.accepted_transactions[0].description == "Viaje al trabajo"
    assert mock_sheets.append_raw_rows.called
