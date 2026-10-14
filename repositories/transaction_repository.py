from contextlib import contextmanager
from typing import Callable, Generator, List, Optional, Set
from sqlalchemy.orm import Session
from core.models import Transaction
from core.database.models import TransactionRecord
from core.database.session import SessionLocal
from core.validators.duplicate_validator import generate_transaction_fingerprint


class TransactionRepository:
    """
    Handles database persistence and queries for financial transactions.
    Supports either an injected Session (e.g., for unit testing) or dynamic session creation
    via a session factory to guarantee thread safety and prevent connection corruption.
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        session_factory: Optional[Callable[[], Session]] = None,
    ):
        self._db = db
        self.db = db
        self.session_factory = session_factory or SessionLocal

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """Provides a database session with automatic commit, rollback, and cleanup."""
        if self._db is not None:
            try:
                yield self._db
            except Exception:
                self._db.rollback()
                raise
        else:
            session = self.session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    def save_transaction(
        self,
        user_id: int,
        transaction: Transaction,
        fingerprint: Optional[str] = None,
    ) -> TransactionRecord:
        """
        Saves a validated Transaction model into the database associated with a specific user.
        """
        if not fingerprint:
            fingerprint = generate_transaction_fingerprint(
                date_val=transaction.date,
                amount_val=transaction.amount,
                tx_type=transaction.transaction_type,
                source=transaction.source_account,
                destination=transaction.destination_account,
                description=transaction.description,
            )

        with self._get_session() as session:
            record = TransactionRecord(
                user_id=user_id,
                date=transaction.date,
                transaction_type=transaction.transaction_type,
                amount=transaction.amount,
                source_account_name=transaction.source_account,
                destination_account_name=transaction.destination_account,
                category=transaction.category,
                subcategory=transaction.subcategory,
                description=transaction.description,
                fingerprint=fingerprint,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def save_batch(
        self,
        user_id: int,
        transactions: List[Transaction],
    ) -> List[TransactionRecord]:
        """
        Saves multiple transactions in a single transaction commit.
        """
        records = []
        with self._get_session() as session:
            for tx in transactions:
                fingerprint = generate_transaction_fingerprint(
                    date_val=tx.date,
                    amount_val=tx.amount,
                    tx_type=tx.transaction_type,
                    source=tx.source_account,
                    destination=tx.destination_account,
                    description=tx.description,
                )
                record = TransactionRecord(
                    user_id=user_id,
                    date=tx.date,
                    transaction_type=tx.transaction_type,
                    amount=tx.amount,
                    source_account_name=tx.source_account,
                    destination_account_name=tx.destination_account,
                    category=tx.category,
                    subcategory=tx.subcategory,
                    description=tx.description,
                    fingerprint=fingerprint,
                )
                session.add(record)
                records.append(record)

            session.commit()
            for record in records:
                session.refresh(record)
            return records

    def get_user_fingerprints(self, user_id: int) -> Set[str]:
        """
        Retrieves all canonical fingerprints registered for a user to perform fast duplicate checks.
        """
        with self._get_session() as session:
            results = (
                session.query(TransactionRecord.fingerprint)
                .filter(TransactionRecord.user_id == user_id)
                .filter(TransactionRecord.fingerprint.isnot(None))
                .all()
            )
            return {r[0] for r in results if r[0]}

    def get_recent_transactions(self, user_id: int, limit: int = 10) -> List[TransactionRecord]:
        """
        Retrieves the most recent transactions recorded for a user.
        """
        with self._get_session() as session:
            return (
                session.query(TransactionRecord)
                .filter(TransactionRecord.user_id == user_id)
                .order_by(TransactionRecord.date.desc(), TransactionRecord.id.desc())
                .limit(limit)
                .all()
            )

    def get_all_user_transactions(self, user_id: int) -> List[TransactionRecord]:
        """
        Retrieves all transactions recorded for a user, ordered chronologically.
        """
        with self._get_session() as session:
            return (
                session.query(TransactionRecord)
                .filter(TransactionRecord.user_id == user_id)
                .order_by(TransactionRecord.date.asc(), TransactionRecord.id.asc())
                .all()
            )

