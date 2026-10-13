from datetime import date, timedelta
from core.models import Transaction
from core.validators.duplicate_validator import (
    DuplicateValidator,
    generate_transaction_fingerprint,
    normalize_amount,
    normalize_date,
    normalize_text,
)
from core.validators.integrity_validator import IntegrityValidator
from core.validators.pipeline import create_default_pipeline


def test_normalize_amount():
    assert normalize_amount(100) == 100.0
    assert normalize_amount(100.5) == 100.5
    assert normalize_amount("$2,300.00") == 2300.0
    assert normalize_amount("$500.50") == 500.5
    assert normalize_amount(" 1,500 ") == 1500.0
    assert normalize_amount(None) == 0.0


def test_normalize_date():
    assert normalize_date(date(2026, 9, 2)) == "2026-09-02"
    assert normalize_date("2026-09-02") == "2026-09-02"
    assert normalize_date("02/09/2026") == "2026-09-02"
    assert normalize_date("02-09-2026") == "2026-09-02"


def test_normalize_text():
    assert normalize_text("  SPEI ENVIADO   Mercado Pago ") == "spei enviado mercado pago"
    assert normalize_text("Alimentación & Café") == "alimentacion cafe"
    assert normalize_text(None) == ""


def test_duplicate_fingerprint_matches_sheet_formatted_row():
    # Transaction from model
    tx = Transaction(
        date=date(2026, 9, 10),
        transaction_type="Traspaso",
        amount=500.0,
        source_account="Tarjeta Débito BBVA",
        destination_account="Cuenta Mercado Pago",
        category="Traspaso",
        subcategory="Ahorro",
        description="SPEI ENVIADO Mercado Pago Felipe Davila",
    )
    tx_fp = generate_transaction_fingerprint(
        date_val=tx.date,
        amount_val=tx.amount,
        tx_type=tx.transaction_type,
        source=tx.source_account,
        destination=tx.destination_account,
        description=tx.description,
    )

    # Row from Google Sheets with currency symbol '$500.00'
    sheet_row_fp = generate_transaction_fingerprint(
        date_val="2026-09-10",
        amount_val="$500.00",
        tx_type="Traspaso",
        source="Tarjeta Débito BBVA",
        destination="Cuenta Mercado Pago",
        description="SPEI ENVIADO Mercado Pago Felipe Davila",
    )

    assert tx_fp == sheet_row_fp


def test_duplicate_validator_detects_existing_and_in_batch():
    validator = DuplicateValidator()
    existing_fps = {
        generate_transaction_fingerprint(
            date_val="2026-09-10",
            amount_val="$500.00",
            tx_type="Traspaso",
            source="Tarjeta Débito BBVA",
            destination="Cuenta Mercado Pago",
            description="SPEI ENVIADO Mercado Pago Felipe Davila",
        )
    }
    context = {"existing_fingerprints": existing_fps}

    tx_dup = Transaction(
        date=date(2026, 9, 10),
        transaction_type="Traspaso",
        amount=500.0,
        source_account="Tarjeta Débito BBVA",
        destination_account="Cuenta Mercado Pago",
        category="Traspaso",
        subcategory="Ahorro",
        description="SPEI ENVIADO Mercado Pago Felipe Davila",
    )

    # First validation: should be detected as duplicate from existing records
    res = validator.validate(tx_dup, context)
    assert not res.is_valid
    assert res.is_duplicate

    # New transaction: should pass and be tracked in batch
    tx_new = Transaction(
        date=date(2026, 9, 11),
        transaction_type="Gasto",
        amount=150.0,
        source_account="Efectivo",
        destination_account=None,
        category="Alimentación",
        subcategory="Comida",
        description="Tacos de pastor",
    )
    res_new = validator.validate(tx_new, context)
    assert res_new.is_valid

    # Repeating the exact same new transaction in the same batch: must be flagged as duplicate
    res_repeat = validator.validate(tx_new, context)
    assert not res_repeat.is_valid
    assert res_repeat.is_duplicate


def test_integrity_validator():
    validator = IntegrityValidator()

    # Amount <= 0
    tx_zero = Transaction(
        date=date.today(),
        transaction_type="Gasto",
        amount=0.01,
        category="Otros",
        subcategory="Test",
        description="Test",
    )
    tx_zero.amount = 0.0  # bypass pydantic gt=0 for test
    res = validator.validate(tx_zero, {})
    assert not res.is_valid
    assert "mayor a cero" in res.error_message

    # Empty description
    tx_no_desc = Transaction(
        date=date.today(),
        transaction_type="Gasto",
        amount=50.0,
        category="Otros",
        subcategory="Test",
        description="   ",
    )
    res = validator.validate(tx_no_desc, {})
    assert not res.is_valid
    assert "vacía" in res.error_message

    # Future date
    tx_future = Transaction(
        date=date.today() + timedelta(days=5),
        transaction_type="Gasto",
        amount=50.0,
        category="Otros",
        subcategory="Test",
        description="Compra futura",
    )
    res = validator.validate(tx_future, {})
    assert not res.is_valid
    assert "futura" in res.error_message


def test_default_validation_pipeline():
    pipeline = create_default_pipeline()
    assert len(pipeline.validators) == 2

    tx_valid = Transaction(
        date=date.today(),
        transaction_type="Gasto",
        amount=85.0,
        source_account="Efectivo",
        category="Transporte",
        subcategory="Metro",
        description="Recarga tarjeta metro",
    )
    context = {"existing_fingerprints": set()}
    result = pipeline.validate(tx_valid, context)
    assert result.is_valid
