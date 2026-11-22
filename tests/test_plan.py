import sqlite3
from dataclasses import replace
from fractions import Fraction as F

from archive.plan_store import PlanStore
from plan.audit import audit_plan
from plan.freeze import freeze_plan
from publication.issue import issue_report
from publication.read import read_report
from routing.intake import record_revision
from routing.routes import RouteRule
from tests.support import LineTestCase, audit_values, incident_routes


class PlanTests(LineTestCase):
    def test_parallel(self):
        routes = (
            RouteRule('linear', 'A', 'B', '1/2', 1),
            RouteRule('quadratic', 'A', 'B', '1/4', 2),
            RouteRule('return', 'B', 'A', '1/2', 0),
        )
        _, plan_id = self.prepare(routes)
        self.reopen_archive()
        result = audit_plan(self.archive, plan_id, '1/2')
        self.assertEqual(result.stations, ('A', 'B'))
        self.assertEqual(audit_values(result), (('linear', F(1, 4)), ('quadratic', F(1, 16)), ('return', F(1, 2))))
        self.assertEqual(tuple((row.source, row.destination) for row in result.routes), (('A', 'B'), ('A', 'B'), ('B', 'A')))
        self.assertEqual(result.remaining, (F(11, 16), F(1, 2)))

    def test_first_task_quarter(self):
        revision_id, plan_id = self.prepare(incident_routes())
        plan = PlanStore(self.archive).load(plan_id)
        self.assertEqual(plan.revision_id, revision_id)
        self.assertEqual(tuple(route.releases for route in plan.routes), (1, 2))
        self.assertEqual(tuple(route.base_probability for route in plan.routes), (F(1, 2), F(1, 2)))
        result = audit_plan(self.archive, plan_id, '1/4')
        self.assertEqual(audit_values(result), (('outbound', F(1, 8)), ('return', F(1, 32))))
        self.assertEqual(result.remaining, (F(7, 8), F(31, 32)))

    def test_parallel_leading(self):
        routes = (
            RouteRule('out-first', 'A', 'B', '1/4', 1),
            RouteRule('out-second', 'A', 'B', '1/4', 1),
            RouteRule('return', 'B', 'A', '1/4', 1),
        )
        _, plan_id = self.prepare(routes)
        result = audit_plan(self.archive, plan_id, '1/2')
        self.assertEqual(audit_values(result), (('out-first', F(1, 8)), ('out-second', F(1, 8)), ('return', F(1, 8))))
        self.assertEqual(result.remaining, (F(3, 4), F(7, 8)))

    def test_disconnected(self):
        _, existing = self.prepare(incident_routes())
        issued = issue_report(self.archive, existing)
        counts = self.archive_counts()
        outbound = RouteRule('outbound', 'A', 'B', '1/2', 0)
        revision_id = record_revision(self.source, ('A', 'B'), (1, 0), (outbound,))
        with self.assertRaisesRegex(ValueError, 'mutually reachable'):
            freeze_plan(self.source, self.archive, revision_id)
        self.assertEqual(self.archive_counts(), counts)
        self.assertEqual(self.source.get(revision_id).routes, (replace(outbound, base_probability=F(1, 2)),))
        self.assertEqual(read_report(self.archive, issued[0].report_id), issued)

    def test_zero_return(self):
        routes = (RouteRule('out', 'A', 'B', 1, 0), RouteRule('inactive-return', 'B', 'A', 0, 0))
        revision_id = record_revision(self.source, ('A', 'B'), (1, 0), routes)
        with self.assertRaisesRegex(ValueError, 'mutually reachable'):
            freeze_plan(self.source, self.archive, revision_id)
        self.assertEqual(self.archive_counts(), (0, 0, 0))
        self.assertEqual(self.source.get(revision_id).routes[1].base_probability, 0)

    def test_bad_ratio(self):
        _, plan_id = self.prepare(incident_routes())
        for value in ('5/4', '-1/4', '1/0', 0.5, True, None):
            with self.subTest(ratio=value), self.assertRaises(ValueError):
                audit_plan(self.archive, plan_id, value)
        result = audit_plan(self.archive, plan_id, '1/2')
        self.assertEqual(result.ratio, F(1, 2))
        self.assertEqual(audit_values(result), (('outbound', F(1, 4)), ('return', F(1, 8))))
        self.assertEqual(result.remaining, (F(3, 4), F(7, 8)))
        self.assertEqual(self.archive_counts(), (1, 0, 0))

    def test_zero_and_full_audit_keep_inactive_route(self):
        routes = incident_routes() + (RouteRule('inactive', 'A', 'B', 0, 0),)
        _, plan_id = self.prepare(routes)
        for ratio, value in ((0, 0), (1, F(1, 2))):
            result = audit_plan(self.archive, plan_id, ratio)
            self.assertEqual(audit_values(result), (('outbound', value), ('return', value), ('inactive', 0)))
            self.assertEqual(result.remaining, (1 - value, 1 - value))

    def test_unknown_ids_and_plan_size(self):
        with self.assertRaises(KeyError):
            freeze_plan(self.source, self.archive, 'missing-revision')
        with self.assertRaises(KeyError):
            audit_plan(self.archive, 'missing-plan', 0)
        for size in (1, 7):
            stations = tuple(str(index) for index in range(size))
            routes = tuple(RouteRule(name, name, stations[(index + 1) % size], 1, 0) for index, name in enumerate(stations))
            revision_id = record_revision(self.source, stations, (1,) + (0,) * (size - 1), routes)
            with self.assertRaisesRegex(ValueError, 'two to six'):
                freeze_plan(self.source, self.archive, revision_id)
        self.assertEqual(self.archive_counts(), (0, 0, 0))

    def test_duplicate_plan_save_preserves_original(self):
        _, plan_id = self.prepare(incident_routes())
        store = PlanStore(self.archive)
        plan = store.load(plan_id)
        with self.assertRaises(sqlite3.IntegrityError):
            store.save(replace(plan, initial=(F(0), F(1))))
        self.assertEqual(store.load(plan_id), plan)
        self.assertEqual(self.archive_counts(), (1, 0, 0))
