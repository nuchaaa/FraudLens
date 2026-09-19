from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def create_database_engine(url: str) -> Engine:
    if make_url(url).drivername != "postgresql+psycopg":
        raise ValueError("FraudLens requires PostgreSQL with the psycopg driver")
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)
