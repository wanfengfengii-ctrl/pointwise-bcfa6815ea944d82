import json
from fractions import Fraction as F

from analysis.transition import build_transition
from archive.plan_store import PlanStore
from plan.audit import audit_plan
from plan.snapshot import FrozenPlan, FrozenRoute
from publication.issue import issue_report
from publication.read import read_report
from routing.routes import RouteRule
from tests.support import LineTestCase, audit_values, incident_routes


class OccupationTests(LineTestCase):
    def test_rare(self):
        _, plan_id = self.prepare(incident_routes())
        issued = issue_report(self.archive, plan_id)
        report, receipt = issued
        self.assertEqual(report.plan_id, plan_id)
        self.assertEqual(report.stations, ('A', 'B'))
        self.assert_occupations(report, (1, 0), (0, 1))
        self.assertEqual((receipt.report_id, receipt.plan_id), (report.report_id, plan_id))
        self.assertEqual(read_report(self.archive, report.report_id), issued)

    def test_swapped_orders(self):
        _, original_id = self.prepare(incident_routes())
        _, swapped_id = self.prepare(incident_routes(2, 1))
        store = PlanStore(self.archive)
        original, swapped = store.load(original_id), store.load(swapped_id)
        self.assertEqual(build_transition(original, 0), ((1, 0), (0, 1)))
        self.assertEqual(build_transition(swapped, 0), ((1, 0), (0, 1)))
        full = ((F(1, 2), F(1, 2)), (F(1, 2), F(1, 2)))
        self.assertEqual(build_transition(original, 1), full)
        self.assertEqual(build_transition(swapped, 1), full)
        self.assert_occupations(issue_report(self.archive, original_id)[0], (1, 0), (0, 1))
        self.assert_occupations(issue_report(self.archive, swapped_id)[0], (1, 0), (1, 0))

    def test_legal_snapshot(self):
        plan = FrozenPlan('independent-plan', 'recorded-offsite', ('A', 'B'), (F(1), F(0)), (
            FrozenRoute('outbound', 'A', 'B', F(1, 2), 1),
            FrozenRoute('return', 'B', 'A', F(1, 2), 2),
        ))
        PlanStore(self.archive).save(plan)
        self.disconnect_source()
        self.reopen_archive()
        self.assertEqual(PlanStore(self.archive).load(plan.plan_id), plan)
        issued = issue_report(self.archive, plan.plan_id)
        self.assert_occupations(issued[0], (1, 0), (0, 1))
        self.assertEqual(read_report(self.archive, issued[0].report_id), issued)

    def test_equal_order(self):
        routes = (RouteRule('out', 'A', 'B', '1/4', 1), RouteRule('back', 'B', 'A', '1/2', 1))
        _, plan_id = self.prepare(routes)
        report, _ = issue_report(self.archive, plan_id)
        self.assert_occupations(report, (1, 0), (F(2, 3), F(1, 3)))

    def test_parallel_leading(self):
        routes = (
            RouteRule('out-first', 'A', 'B', '1/4', 1),
            RouteRule('out-second', 'A', 'B', '1/4', 1),
            RouteRule('return', 'B', 'A', '1/4', 1),
        )
        _, plan_id = self.prepare(routes)
        audit = audit_plan(self.archive, plan_id, '1/2')
        self.assertEqual(audit_values(audit), (('out-first', F(1, 8)), ('out-second', F(1, 8)), ('return', F(1, 8))))
        self.assertEqual(audit.remaining, (F(3, 4), F(7, 8)))
        self.assert_occupations(issue_report(self.archive, plan_id)[0], (1, 0), (F(1, 3), F(2, 3)))

    def test_self_route(self):
        routes = (
            RouteRule('self-check', 'A', 'A', '1/4', 0),
            RouteRule('out', 'A', 'B', '1/4', 0),
            RouteRule('back', 'B', 'A', '1/2', 0),
        )
        _, plan_id = self.prepare(routes)
        plan = PlanStore(self.archive).load(plan_id)
        self.assertEqual(audit_plan(self.archive, plan_id, 0).remaining, (F(1, 2), F(1, 2)))
        self.assertEqual(build_transition(plan, 0), ((F(3, 4), F(1, 4)), (F(1, 2), F(1, 2))))
        expected = (F(2, 3), F(1, 3))
        self.assert_occupations(issue_report(self.archive, plan_id)[0], expected, expected)

    def test_transient_split(self):
        routes = (
            RouteRule('to-b', 'A', 'B', '1/4', 0),
            RouteRule('to-c', 'A', 'C', '1/2', 0),
            RouteRule('b-to-a', 'B', 'A', '1/2', 1),
            RouteRule('c-to-a', 'C', 'A', '1/2', 2),
        )
        _, plan_id = self.prepare(routes, ('A', 'B', 'C'))
        issued = issue_report(self.archive, plan_id)
        expected = {'zero': ['0', '1/3', '2/3'], 'rare': ['0', '0', '1']}
        self.assert_occupations(issued[0], (0, F(1, 3), F(2, 3)), (0, 0, 1))
        self.reopen_archive()
        received = read_report(self.archive, issued[0].report_id)
        self.assertEqual(received, issued)

        def columns(report):
            return {'zero': list(map(str, report.zero)), 'rare': list(map(str, report.rare))}

        print('POINTWISE_SCENARIO ' + json.dumps({
            'case_id': 'v_rare.transient_split',
            'input': {'stations': ['A', 'B', 'C'], 'initial': ['1', '0', '0'], 'routes': [
                [route.route_id, route.source, route.destination, str(route.base_probability), route.releases] for route in routes
            ]},
            'expected': expected,
            'actual': columns(issued[0]),
            'downstream_expected': expected,
            'downstream_actual': columns(received[0]),
            'code_paths': ['plan/freeze.py', 'analysis/occupation.py', 'analysis/rare_limit.py', 'publication/issue.py', 'publication/read.py'],
            'oracle': 'Normalize the two zero-phase exit probabilities. At positive ratios flow balance gives C:B = 2:x.',
        }, ensure_ascii=False, sort_keys=True))

    def test_transient_cycle_and_initial_closed_mass(self):
        routes = (
            RouteRule('a-b', 'A', 'B', '1/2', 0), RouteRule('a-c', 'A', 'C', '1/4', 0),
            RouteRule('b-a', 'B', 'A', '1/4', 0), RouteRule('b-d', 'B', 'D', '1/2', 0),
            RouteRule('c-a', 'C', 'A', '1/2', 1), RouteRule('d-a', 'D', 'A', '1/2', 1),
        )
        # The chance of hitting C first from A is 3/7. C also owns 1/4 of the opening mass.
        _, plan_id = self.prepare(routes, ('A', 'B', 'C', 'D'), ('1/2', 0, '1/4', '1/4'))
        self.assert_occupations(issue_report(self.archive, plan_id)[0], (0, 0, F(13, 28), F(15, 28)), (0, 0, F(3, 7), F(4, 7)))

    def test_periodic(self):
        routes = (RouteRule('ab', 'A', 'B', 1, 0), RouteRule('ba', 'B', 'A', 1, 0))
        _, plan_id = self.prepare(routes)
        self.assertEqual(build_transition(PlanStore(self.archive).load(plan_id), 0), ((0, 1), (1, 0)))
        expected = (F(1, 2), F(1, 2))
        self.assert_occupations(issue_report(self.archive, plan_id)[0], expected, expected)

    def test_six_station_cycle(self):
        stations = ('A', 'B', 'C', 'D', 'E', 'F')
        routes = tuple(
            RouteRule(source, source, stations[(index + 1) % len(stations)], '1/4' if source == 'B' else '1/2', 2 if source in ('B', 'C') else 1)
            for index, source in enumerate(stations)
        )
        _, plan_id = self.prepare(routes, stations, ('1/2', '1/2', 0, 0, 0, 0))
        # In a ring all edge flows match. B and C have the largest inverse rates as x goes to zero.
        self.assert_occupations(issue_report(self.archive, plan_id)[0], (F(1, 2), F(1, 2), 0, 0, 0, 0), (0, F(2, 3), F(1, 3), 0, 0, 0))
