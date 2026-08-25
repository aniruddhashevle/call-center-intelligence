from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base
from src.utils.config import build_config


_session_factories: dict[int, sessionmaker] = {}


def get_engine():
    config = build_config()

    db_path = Path(config.db_path)
    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={
            "check_same_thread": False,
        },
    )

    encryption_key = getattr(
        config,
        "db_encryption_key",
        None,
    )

    if encryption_key:
        @event.listens_for(engine, "connect")
        def set_sqlite_key(
            dbapi_connection,
            connection_record,
        ):
            cursor = dbapi_connection.cursor()

            cursor.execute(
                f"PRAGMA key='{encryption_key}'"
            )

            cursor.close()

    return engine


def init_db() -> None:
    engine = get_engine()

    Base.metadata.create_all(
        bind=engine,
    )


def get_session() -> Session:
    engine = get_engine()

    engine_id = id(engine)

    factory = _session_factories.get(engine_id)

    if factory is None:
        factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
        )

        _session_factories[engine_id] = factory

    return factory()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session()

    try:
        yield session
        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()