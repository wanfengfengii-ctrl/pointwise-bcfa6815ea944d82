import sqlite3
from pathlib import Path

from archive.transactions import write_transaction


class HandoverArchive:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    @classmethod
    def open(cls, path: str | Path) -> 'HandoverArchive':
        connection = sqlite3.connect(path, isolation_level=None)
        archive = cls(connection)
        try:
            connection.execute('PRAGMA foreign_keys = ON')
            archive.initialize()
        except BaseException:
            archive.close()
            raise
        return archive

    def initialize(self) -> None:
        with write_transaction(self.connection):
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY NOT NULL,
                    revision_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            ''')
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY NOT NULL,
                    plan_id TEXT NOT NULL REFERENCES plans(plan_id),
                    payload TEXT NOT NULL
                )
            ''')
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS receipts (
                    report_id TEXT PRIMARY KEY NOT NULL REFERENCES reports(report_id),
                    payload TEXT NOT NULL
                )
            ''')

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> 'HandoverArchive':
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
