from contextlib import contextmanager
from typing import Callable, Generator, List, Optional
from sqlalchemy.orm import Session
from core.database.models import User, Account
from core.database.session import SessionLocal

# Default initial accounts created for new users
DEFAULT_ACCOUNTS = [
    ("Efectivo", "Efectivo"),
    ("Tarjeta Débito BBVA", "Débito"),
    ("Tarjeta Crédito BBVA", "Crédito"),
    ("Tarjeta Débito Nu", "Débito"),
    ("Tarjeta Crédito Nu", "Crédito"),
    ("Tarjeta Débito Stori", "Débito"),
    ("Tarjeta Crédito Stori", "Crédito"),
    ("Tarjeta Crédito Rappi", "Crédito"),
    ("Cuenta Mercado Pago", "Débito"),
]


def infer_account_type(name: str) -> str:
    """Infers an account type ('Débito', 'Crédito', 'Efectivo', 'Inversión', 'General') from keywords."""
    lowered = name.lower()
    if any(k in lowered for k in ["crédito", "credito", "credit", "rappi"]):
        return "Crédito"
    if any(k in lowered for k in ["débito", "debito", "debit", "cheques", "nómina", "nomina"]):
        return "Débito"
    if any(k in lowered for k in ["efectivo", "cash"]):
        return "Efectivo"
    if any(k in lowered for k in ["cetes", "inversion", "inversión", "ahorro", "fondo", "apartado"]):
        return "Inversión"
    return "General"


class UserRepository:
    """
    Handles persistence and retrieval of User and Account records.
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

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Retrieves a user by their Telegram ID."""
        with self._get_session() as session:
            return session.query(User).filter(User.telegram_id == telegram_id).first()

    def create_user(
        self,
        telegram_id: int,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
        seed_defaults: bool = True,
    ) -> User:
        """Creates a new user and seeds initial default accounts."""
        with self._get_session() as session:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
            )
            session.add(user)
            session.flush()

            if seed_defaults:
                for acc_name, acc_type in DEFAULT_ACCOUNTS:
                    account = Account(
                        user_id=user.id,
                        name=acc_name,
                        account_type=acc_type,
                    )
                    session.add(account)

            session.commit()
            session.refresh(user)
            return user

    def get_or_create_user(
        self,
        telegram_id: int,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
    ) -> User:
        """Finds an existing user or creates a new one seamlessly."""
        user = self.get_by_telegram_id(telegram_id)
        if not user:
            try:
                user = self.create_user(telegram_id, first_name, username)
            except Exception:
                # Concurrent request race condition handling: re-fetch if already created
                user = self.get_by_telegram_id(telegram_id)
                if not user:
                    raise
        return user

    def get_user_accounts(self, user_id: int, active_only: bool = True) -> List[Account]:
        """Returns all accounts belonging to the user."""
        with self._get_session() as session:
            query = session.query(Account).filter(Account.user_id == user_id)
            if active_only:
                query = query.filter(Account.is_active.is_(True))
            return query.all()

    def get_user_account_names(self, user_id: int) -> List[str]:
        """Returns a list of account names configured for the user."""
        accounts = self.get_user_accounts(user_id)
        return [acc.name for acc in accounts]

    def get_account_by_name(self, user_id: int, name: str, active_only: bool = True) -> Optional[Account]:
        """Finds an account by exact or case-insensitive name."""
        clean_name = name.strip()
        with self._get_session() as session:
            query = session.query(Account).filter(
                Account.user_id == user_id,
                Account.name.ilike(clean_name),
            )
            if active_only:
                query = query.filter(Account.is_active.is_(True))
            account = query.first()

            # Fallback to substring matching if exact match not found
            if not account and active_only:
                account = (
                    session.query(Account)
                    .filter(Account.user_id == user_id, Account.is_active.is_(True))
                    .filter(Account.name.ilike(f"%{clean_name}%"))
                    .first()
                )
            return account

    def add_account(
        self,
        user_id: int,
        name: str,
        account_type: Optional[str] = None,
    ) -> tuple[Account, bool]:
        """
        Adds or reactivates an account for a user.
        Returns a tuple: (account, is_new_or_reactivated).
        """
        clean_name = name.strip()
        final_type = account_type or infer_account_type(clean_name)

        with self._get_session() as session:
            existing = (
                session.query(Account)
                .filter(Account.user_id == user_id, Account.name.ilike(clean_name))
                .first()
            )
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    existing.account_type = final_type
                    session.commit()
                    session.refresh(existing)
                    return existing, True
                return existing, False

            account = Account(user_id=user_id, name=clean_name, account_type=final_type, is_active=True)
            session.add(account)
            session.commit()
            session.refresh(account)
            return account, True

    def deactivate_account(self, user_id: int, name: str) -> Optional[Account]:
        """
        Soft-deactivates an account by name. Preserves historical transaction relations.
        Returns the deactivated Account or None if not found.
        """
        clean_name = name.strip()
        with self._get_session() as session:
            query = session.query(Account).filter(
                Account.user_id == user_id,
                Account.name.ilike(clean_name),
                Account.is_active.is_(True),
            )
            account = query.first()
            if not account:
                account = (
                    session.query(Account)
                    .filter(Account.user_id == user_id, Account.is_active.is_(True))
                    .filter(Account.name.ilike(f"%{clean_name}%"))
                    .first()
                )

            if account:
                account.is_active = False
                session.commit()
                session.refresh(account)
                return account
            return None

