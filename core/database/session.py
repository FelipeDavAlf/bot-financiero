from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from core.config import settings

# Configure database engine
connect_args = {}
database_url = settings.normalized_database_url
if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Ensures healthy PostgreSQL connections
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)
Base = declarative_base()


def init_db() -> None:
    """Creates all database tables defined in the metadata and applies safe schema migrations."""
    import logging
    from sqlalchemy import text
    import core.database.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Safe automated schema migration for existing PostgreSQL deployments
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE transactions ALTER COLUMN fingerprint TYPE VARCHAR(500);"))
                logging.info("Successfully updated transactions.fingerprint column to VARCHAR(500).")
    except Exception as exc:
        logging.warning(f"Could not apply automated migration on transactions.fingerprint: {exc}")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provides a transactional database session scope."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
