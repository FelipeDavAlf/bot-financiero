from typing import List, Optional
from sqlalchemy.orm import Session
from core.database.models import User, Account

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
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Retrieves a user by their Telegram ID."""
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()

    def create_user(
        self,
        telegram_id: int,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
        seed_defaults: bool = True,
    ) -> User:
        """Creates a new user and seeds initial default accounts."""
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
        )
        self.db.add(user)
        self.db.flush()

        if seed_defaults:
            for acc_name, acc_type in DEFAULT_ACCOUNTS:
                account = Account(
                    user_id=user.id,
                    name=acc_name,
                    account_type=acc_type,
                )
                self.db.add(account)

        self.db.commit()
        self.db.refresh(user)
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
            user = self.create_user(telegram_id, first_name, username)
        return user

    def get_user_accounts(self, user_id: int, active_only: bool = True) -> List[Account]:
        """Returns all accounts belonging to the user."""
        query = self.db.query(Account).filter(Account.user_id == user_id)
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
        query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.name.ilike(clean_name),
        )
        if active_only:
            query = query.filter(Account.is_active.is_(True))
        account = query.first()

        # Fallback to substring matching if exact match not found
        if not account and active_only:
            account = (
                self.db.query(Account)
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

        existing = (
            self.db.query(Account)
            .filter(Account.user_id == user_id, Account.name.ilike(clean_name))
            .first()
        )
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.account_type = final_type
                self.db.commit()
                self.db.refresh(existing)
                return existing, True
            return existing, False

        account = Account(user_id=user_id, name=clean_name, account_type=final_type, is_active=True)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account, True

    def deactivate_account(self, user_id: int, name: str) -> Optional[Account]:
        """
        Soft-deactivates an account by name. Preserves historical transaction relations.
        Returns the deactivated Account or None if not found.
        """
        account = self.get_account_by_name(user_id=user_id, name=name, active_only=True)
        if account:
            account.is_active = False
            self.db.commit()
            self.db.refresh(account)
            return account
        return None

