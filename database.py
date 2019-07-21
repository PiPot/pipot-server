import re
from abc import ABCMeta

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import scoped_session, sessionmaker


class DeclarativeABCMeta(DeclarativeMeta, ABCMeta):
    """
    Empty class to create a mixin between DeclarativeMeta and ABCMeta
    """
    pass

Base = declarative_base(metaclass=DeclarativeMeta)
Base.query = None
db_engine = None


def create_session(db_string, drop_tables=False):
    """
    Creates a new DB session using the scoped_session that SQLAlchemy
    provices.

    :param db_string: The connection string.
    :type db_string: str
    :param drop_tables: Drop existing tables?
    :type drop_tables: bool
    :return: A SQLAlchemy session object
    :rtype: sqlalchemy.orm.scoped_session
    """
    global db_engine, Base

    db_engine = create_engine(db_string, convert_unicode=True)
    db_session = scoped_session(sessionmaker(bind=db_engine))
    Base.query = db_session.query_property()

    if drop_tables:
        Base.metadata.drop_all(bind=db_engine)

    Base.metadata.create_all(bind=db_engine)

    return db_session
