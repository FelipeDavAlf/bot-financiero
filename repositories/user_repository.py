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

    def add_account(self, user_id: int, name: str, account_type: str = "General") -> Account:
        """Adds a custom account for a user."""
        account = Account(user_id=user_id, name=name, account_type=account_type)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account
