import unittest
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

from archive.catalog import HandoverArchive
from plan.freeze import freeze_plan
from routing.intake import record_revision
from routing.revision_store import RevisionStore
from routing.routes import RouteRule


def incident_routes(outbound_releases=1, return_releases=2):
    return (
        RouteRule('outbound', 'A', 'B', '1/2', outbound_releases),
        RouteRule('return', 'B', 'A', '1/2', return_releases),
    )


def audit_values(result):
    return tuple((row.route_id, row.probability) for row in result.routes)


class LineTestCase(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        self.source_path = directory / 'routing.sqlite'
        self.archive_path = directory / 'handover.sqlite'
        self.source = self.enterContext(RevisionStore(self.source_path))
        self.archive = self.enterContext(HandoverArchive.open(self.archive_path))

    def prepare(self, routes, stations=('A', 'B'), initial=None):
        if initial is None:
            initial = tuple(int(station == 'A') for station in stations)
        revision_id = record_revision(self.source, stations, initial, routes)
        return revision_id, freeze_plan(self.source, self.archive, revision_id)

    def disconnect_source(self):
        self.source.close()
        self.source_path.rename(self.source_path.with_suffix('.offline'))

    def reopen_archive(self):
        self.archive.close()
        self.archive = self.enterContext(HandoverArchive.open(self.archive_path))

    def source_count(self):
        return self.source.connection.execute('SELECT count(*) FROM revisions').fetchone()[0]

    def archive_counts(self, archive=None):
        connection = (self.archive if archive is None else archive).connection
        return connection.execute('''
            SELECT (SELECT count(*) FROM plans),
                   (SELECT count(*) FROM reports),
                   (SELECT count(*) FROM receipts)
        ''').fetchone()

    def assert_occupations(self, report, zero, rare):
        self.assertEqual(report.zero, zero)
        self.assertEqual(report.rare, rare)
        for column in (report.zero, report.rare):
            self.assertTrue(all(isinstance(value, Fraction) and value >= 0 for value in column))
            self.assertEqual(sum(column), 1)
