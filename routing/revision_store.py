import json
import sqlite3
from fractions import Fraction
from pathlib import Path

from routing.revisions import RouteRevision, build_revision
from routing.routes import RouteRule
from routing.stations import validate_identity


class RevisionStore:
    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(path, isolation_level=None)
        try:
            self.initialize()
        except BaseException:
            self.close()
            raise

    def initialize(self) -> None:
        self.connection.execute('''
            CREATE TABLE IF NOT EXISTS revisions (
                revision_id TEXT PRIMARY KEY NOT NULL,
                payload TEXT NOT NULL
            )
        ''')

    def append(self, revision: RouteRevision) -> None:
        # The store also accepts revisions constructed by callers outside intake.
        revision = build_revision(revision.revision_id, revision.stations, revision.initial, revision.routes)
        payload = {
            'stations': [station.name for station in revision.stations],
            'initial': [str(mass) for mass in revision.initial],
            'routes': [
                [route.route_id, route.source, route.destination, str(route.base_probability), route.releases]
                for route in revision.routes
            ],
        }
        self.connection.execute(
            'INSERT INTO revisions (revision_id, payload) VALUES (?, ?)',
            (revision.revision_id, json.dumps(payload, ensure_ascii=False)),
        )

    def get(self, revision_id: str) -> RouteRevision:
        validate_identity(revision_id, 'revision identity')
        row = self.connection.execute(
            'SELECT payload FROM revisions WHERE revision_id = ?', (revision_id,),
        ).fetchone()
        if row is None:
            raise KeyError(revision_id)
        try:
            payload = json.loads(row[0])
            return build_revision(
                revision_id,
                payload['stations'],
                tuple(Fraction(mass) for mass in payload['initial']),
                tuple(RouteRule(*route) for route in payload['routes']),
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
            raise ValueError(f'invalid revision payload for {revision_id!r}') from error

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> 'RevisionStore':
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
