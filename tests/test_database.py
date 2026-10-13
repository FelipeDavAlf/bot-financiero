import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database.session import Base
from core.database.models import User
from repositories.user_repository import UserRepository
from repositories.transaction_repository import TransactionRepository
from core.models import Transaction


@pytest.fixture
def db_session():
    """Provides a fresh in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_user_repository_create_and_get(db_session):
    repo = UserRepository(db_session)
    user = repo.create_user(telegram_id=12345, first_name="Felipe", username="fdavila")

    assert user.id is not None
    assert user.telegram_id == 12345
    assert user.first_name == "Felipe"

    # Default accounts should be seeded
    accounts = repo.get_user_accounts(user.id)
    assert len(accounts) > 0
    names = repo.get_user_account_names(user.id)
    assert "Efectivo" in names
    assert "Tarjeta Débito BBVA" in names


def test_user_repository_get_or_create_existing(db_session):
    repo = UserRepository(db_session)
    user1 = repo.get_or_create_user(telegram_id=99999, first_name="Carlos")
    user2 = repo.get_or_create_user(telegram_id=99999, first_name="Carlos Modified")

    assert user1.id == user2.id
    assert db_session.query(User).count() == 1


def test_transaction_repository_save_and_fingerprints(db_session):
    user_repo = UserRepository(db_session)
    user = user_repo.create_user(telegram_id=11111, first_name="Ana")

    tx_repo = TransactionRepository(db_session)
    tx = Transaction(
        date=date(2026, 10, 13),
        transaction_type="Gasto",
        amount=222.0,
        source_account="Tarjeta Crédito Rappi",
        destination_account=None,
        category="Vivienda y Servicios",
        subcategory="Estantes baño",
        description="Estantes para baño",
    )

    record = tx_repo.save_transaction(user_id=user.id, transaction=tx)
    assert record.id is not None
    assert record.user_id == user.id
    assert record.amount == 222.0
    assert record.fingerprint is not None

    fingerprints = tx_repo.get_user_fingerprints(user_id=user.id)
    assert record.fingerprint in fingerprints


def test_multi_user_data_isolation(db_session):
    user_repo = UserRepository(db_session)
    user_a = user_repo.create_user(telegram_id=1001, first_name="User A")
    user_b = user_repo.create_user(telegram_id=1002, first_name="User B")

    tx_repo = TransactionRepository(db_session)
    tx = Transaction(
        date=date(2026, 10, 13),
        transaction_type="Gasto",
        amount=100.0,
        source_account="Efectivo",
        destination_account=None,
        category="Alimentación",
        subcategory="Tacos",
        description="Tacos de pastor",
    )

    # Save transaction for User A only
    tx_repo.save_transaction(user_id=user_a.id, transaction=tx)

    # Verify User A has 1 transaction and fingerprint
    fingerprints_a = tx_repo.get_user_fingerprints(user_id=user_a.id)
    assert len(fingerprints_a) == 1
    txs_a = tx_repo.get_recent_transactions(user_id=user_a.id)
    assert len(txs_a) == 1

    # Verify User B has 0 transactions and 0 fingerprints (strict isolation)
    fingerprints_b = tx_repo.get_user_fingerprints(user_id=user_b.id)
    assert len(fingerprints_b) == 0
    txs_b = tx_repo.get_recent_transactions(user_id=user_b.id)
    assert len(txs_b) == 0
