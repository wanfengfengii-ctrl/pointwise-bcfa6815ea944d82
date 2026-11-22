from fractions import Fraction as F

from archive.catalog import HandoverArchive
from archive.plan_store import PlanStore
from plan.audit import audit_plan
from publication.issue import issue_report
from publication.read import read_report
from routing.intake import record_revision
from tests.support import LineTestCase, audit_values, incident_routes


class InjectedCommitFailure(RuntimeError):
    pass


class HandoverTests(LineTestCase):
    def test_reopen(self):
        old_revision, old_plan = self.prepare(incident_routes())
        old_audit = audit_plan(self.archive, old_plan, '1/4')
        old_issue = issue_report(self.archive, old_plan)
        new_revision, new_plan = self.prepare(incident_routes(2, 1))
        self.assertNotEqual(old_revision, new_revision)
        self.assertNotEqual(old_plan, new_plan)
        self.assertEqual(tuple(route.releases for route in self.source.get(old_revision).routes), (1, 2))
        self.assertEqual(tuple(route.releases for route in self.source.get(new_revision).routes), (2, 1))
        self.disconnect_source()
        self.reopen_archive()
        self.assertFalse(self.source_path.exists())
        offline_audit = audit_plan(self.archive, old_plan, '1/4')
        self.assertEqual(audit_values(offline_audit), (('outbound', F(1, 8)), ('return', F(1, 32))))
        self.assertEqual(offline_audit, old_audit)
        received = read_report(self.archive, old_issue[0].report_id)
        self.assertEqual(received, old_issue)
        self.assert_occupations(received[0], (1, 0), (0, 1))
        self.assert_occupations(issue_report(self.archive, old_plan)[0], (1, 0), (0, 1))

    def test_exact_report_id(self):
        _, old_plan = self.prepare(incident_routes())
        old_issue = issue_report(self.archive, old_plan)
        _, new_plan = self.prepare(incident_routes(2, 1))
        new_issue = issue_report(self.archive, new_plan)
        self.disconnect_source()
        self.reopen_archive()
        for pair, expected in ((old_issue, (0, 1)), (new_issue, (1, 0))):
            report, receipt = read_report(self.archive, pair[0].report_id)
            self.assertEqual((report, receipt), pair)
            self.assert_occupations(report, (1, 0), expected)
            self.assertEqual((receipt.report_id, receipt.plan_id), (report.report_id, report.plan_id))
        self.assertNotEqual(old_issue[0].report_id, new_issue[0].report_id)

    def test_unknown_report(self):
        _, plan_id = self.prepare(incident_routes())
        previous = issue_report(self.archive, plan_id)
        before = self.archive_counts()
        with self.assertRaises(KeyError):
            read_report(self.archive, 'unissued')
        self.assertEqual(self.archive_counts(), before)
        self.assertEqual(read_report(self.archive, previous[0].report_id), previous)

    def test_station_alignment(self):
        _, old_plan = self.prepare(incident_routes(), ('B', 'A'), (0, 1))
        old_issue = issue_report(self.archive, old_plan)
        record_revision(self.source, ('A', 'B'), (0, 1), incident_routes(2, 1))
        self.disconnect_source()
        self.reopen_archive()
        report, receipt = read_report(self.archive, old_issue[0].report_id)
        self.assertEqual((report, receipt), old_issue)
        self.assertEqual(report.stations, ('B', 'A'))
        self.assertEqual(tuple(zip(report.stations, report.zero, report.rare)), (('B', F(0), F(1)), ('A', F(1), F(0))))

    def test_init_idempotent(self):
        old_revision, old_plan = self.prepare(incident_routes())
        issued = issue_report(self.archive, old_plan)
        corrected = record_revision(self.source, ('A', 'B'), (1, 0), incident_routes(2, 1))
        source_baseline = {identifier: self.source.get(identifier) for identifier in (old_revision, corrected)}
        plan_baseline = PlanStore(self.archive).load(old_plan)
        audit_baseline = audit_plan(self.archive, old_plan, '1/4')
        for _ in range(2):
            self.source.initialize()
            self.archive.initialize()
            self.assertEqual(self.source_count(), 2)
            self.assertEqual(self.archive_counts(), (1, 1, 1))
            self.assertEqual({identifier: self.source.get(identifier) for identifier in source_baseline}, source_baseline)
            self.assertEqual(PlanStore(self.archive).load(old_plan), plan_baseline)
            self.assertEqual(read_report(self.archive, issued[0].report_id), issued)
        self.disconnect_source()
        self.reopen_archive()
        self.assertEqual(audit_plan(self.archive, old_plan, '1/4'), audit_baseline)
        self.assertEqual(read_report(self.archive, issued[0].report_id), issued)

    def test_rollback(self):
        _, first_plan = self.prepare(incident_routes())
        old_issue = issue_report(self.archive, first_plan)
        _, second_plan = self.prepare(incident_routes(2, 1))
        counts = self.archive_counts()
        stages = []

        def abort():
            stages.append(self.archive_counts())
            raise InjectedCommitFailure('cancel before commit')

        with self.assertRaisesRegex(InjectedCommitFailure, 'cancel before commit'):
            issue_report(self.archive, second_plan, before_commit=abort)
        self.assertEqual(stages, [(2, 2, 2)])
        self.assertEqual(self.archive_counts(), counts)
        self.assertEqual(read_report(self.archive, old_issue[0].report_id), old_issue)
        retried = issue_report(self.archive, second_plan)
        self.assertEqual(read_report(self.archive, retried[0].report_id), retried)
        self.assertEqual(self.archive_counts(), (2, 2, 2))

    def test_reopen_atomic(self):
        _, first_plan = self.prepare(incident_routes())
        old_issue = issue_report(self.archive, first_plan)
        _, second_plan = self.prepare(incident_routes(2, 1))
        counts = self.archive_counts()
        staged_ids = []
        with HandoverArchive.open(self.archive_path) as observer:
            def abort():
                self.assertEqual(self.archive_counts(), (2, 2, 2))
                self.assertEqual(self.archive_counts(observer), counts)
                staged_id = self.archive.connection.execute(
                    'SELECT report_id FROM reports WHERE plan_id = ?', (second_plan,),
                ).fetchone()[0]
                staged_ids.append(staged_id)
                with self.assertRaises(KeyError):
                    read_report(observer, staged_id)
                raise InjectedCommitFailure('interrupt staged issue')

            with self.assertRaises(InjectedCommitFailure):
                issue_report(self.archive, second_plan, before_commit=abort)
        self.reopen_archive()
        self.assertEqual(self.archive_counts(), counts)
        self.assertEqual(len(staged_ids), 1)
        with self.assertRaises(KeyError):
            read_report(self.archive, staged_ids[0])
        self.assertEqual(read_report(self.archive, old_issue[0].report_id), old_issue)

    def test_missing_plan(self):
        _, plan_id = self.prepare(incident_routes())
        original = issue_report(self.archive, plan_id)
        counts = self.archive_counts()
        with self.assertRaises(KeyError):
            issue_report(self.archive, 'missing-plan', before_commit=lambda: self.fail('unknown plan reached commit'))
        self.assertEqual(self.archive_counts(), counts)
        self.assertEqual(read_report(self.archive, original[0].report_id), original)
