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
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
    )
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


def test_infer_account_type():
    from repositories.user_repository import infer_account_type
    assert infer_account_type("Tarjeta Débito Santander") == "Débito"
    assert infer_account_type("Banamex Crédito Platino") == "Crédito"
    assert infer_account_type("Efectivo Monedero") == "Efectivo"
    assert infer_account_type("Cetesdirecto Ahorro") == "Inversión"
    assert infer_account_type("Billetera Digital") == "General"


def test_add_and_deactivate_custom_accounts(db_session):
    repo = UserRepository(db_session)
    user = repo.create_user(telegram_id=55555, first_name="Custom Accounts User")

    # Add custom account
    acc, was_added = repo.add_account(user_id=user.id, name="Tarjeta Débito Santander")
    assert was_added is True
    assert acc.name == "Tarjeta Débito Santander"
    assert acc.account_type == "Débito"
    assert acc.is_active is True

    # Re-adding the same active account returns False
    acc2, was_added2 = repo.add_account(user_id=user.id, name="Tarjeta Débito Santander")
    assert was_added2 is False
    assert acc2.id == acc.id

    # Check it appears in active names
    active_names = repo.get_user_account_names(user_id=user.id)
    assert "Tarjeta Débito Santander" in active_names

    # Deactivate account
    deactivated = repo.deactivate_account(user_id=user.id, name="santander")
    assert deactivated is not None
    assert deactivated.id == acc.id
    assert deactivated.is_active is False

    # Check it no longer appears in active names
    active_names_after = repo.get_user_account_names(user_id=user.id)
    assert "Tarjeta Débito Santander" not in active_names_after

    # Reactivating account returns True
    reactivated, was_reactivated = repo.add_account(user_id=user.id, name="Tarjeta Débito Santander")
    assert was_reactivated is True
    assert reactivated.is_active is True


def test_repositories_scoped_session_factory():
    """Verifies that repositories operate properly without pre-created sessions via session_factory."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
    )

    user_repo = UserRepository(session_factory=factory)
    tx_repo = TransactionRepository(session_factory=factory)

    # User creation and lookup with scoped sessions
    user = user_repo.create_user(telegram_id=88888, first_name="ScopedUser")
    assert user.id is not None
    fetched = user_repo.get_by_telegram_id(88888)
    assert fetched is not None
    assert fetched.id == user.id

    # Transaction save with scoped sessions
    tx = Transaction(
        date=date(2026, 10, 14),
        transaction_type="Gasto",
        amount=150.0,
        source_account="Efectivo",
        destination_account=None,
        category="Alimentación",
        subcategory="Comida rápida",
        description="Hamburguesa",
    )
    record = tx_repo.save_transaction(user_id=user.id, transaction=tx)
    assert record.id is not None
    assert record.user_id == user.id

    all_txs = tx_repo.get_all_user_transactions(user_id=user.id)
    assert len(all_txs) == 1
    assert all_txs[0].description == "Hamburguesa"


def test_session_rollback_recovery(db_session):
    """Verifies that an exception during an operation does not leave a pending rollback error."""
    user_repo = UserRepository(db_session)
    user = user_repo.create_user(telegram_id=44444, first_name="RollbackTest")
    assert user.id is not None

    # Attempting to insert a duplicate user should fail unique constraint
    with pytest.raises(Exception):
        user_repo.create_user(telegram_id=44444, first_name="Duplicate")

    # The session must recover immediately and allow subsequent queries without PendingRollbackError
    recovered_user = user_repo.get_by_telegram_id(44444)
    assert recovered_user is not None
    assert recovered_user.first_name == "RollbackTest"


