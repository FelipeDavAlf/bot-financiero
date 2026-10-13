from typing import List, Optional, Set
from sqlalchemy.orm import Session
from core.models import Transaction
from core.database.models import TransactionRecord
from core.validators.duplicate_validator import generate_transaction_fingerprint


class TransactionRepository:
    """
    Handles database persistence and queries for financial transactions.
    """

    def __init__(self, db: Session):
        self.db = db

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
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
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
            self.db.add(record)
            records.append(record)

        self.db.commit()
        for record in records:
            self.db.refresh(record)
        return records

    def get_user_fingerprints(self, user_id: int) -> Set[str]:
        """
        Retrieves all canonical fingerprints registered for a user to perform fast duplicate checks.
        """
        results = (
            self.db.query(TransactionRecord.fingerprint)
            .filter(TransactionRecord.user_id == user_id)
            .filter(TransactionRecord.fingerprint.isnot(None))
            .all()
        )
        return {r[0] for r in results if r[0]}

    def get_recent_transactions(self, user_id: int, limit: int = 10) -> List[TransactionRecord]:
        """
        Retrieves the most recent transactions recorded for a user.
        """
        return (
            self.db.query(TransactionRecord)
            .filter(TransactionRecord.user_id == user_id)
            .order_by(TransactionRecord.date.desc(), TransactionRecord.id.desc())
            .limit(limit)
            .all()
        )
