import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def write_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    """Own one SQLite transaction, including errors raised during commit."""
    if connection.in_transaction:
        raise sqlite3.ProgrammingError('an archive write transaction is already active')
    connection.execute('BEGIN IMMEDIATE')
    try:
        yield
        connection.commit()
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
