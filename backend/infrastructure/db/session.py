from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _enable_fks(dbapi_conn, _):  # noqa: ANN001
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
