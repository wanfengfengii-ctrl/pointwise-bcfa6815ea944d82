from fractions import Fraction as F

from analysis.rare_limit import rare_occupation_limit
from archive.plan_store import PlanStore
from plan.audit import audit_plan
from publication.issue import issue_report
from publication.read import read_report
from routing.routes import RouteRule
from tests.support import LineTestCase, audit_values, incident_routes


class RareLimitTests(LineTestCase):
    def test_limit_is_exact_not_pilot_ratio(self):
        # 固定试点比例 1/100 会把 B 报成 100/101;精确右极限是 1。
        _, plan_id = self.prepare(incident_routes())
        plan = PlanStore(self.archive).load(plan_id)
        self.assertEqual(tuple(route.releases for route in plan.routes), (1, 2))
        self.assertEqual(rare_occupation_limit(plan), (F(0), F(1)))
        issued = issue_report(self.archive, plan_id)
        self.assert_occupations(issued[0], (1, 0), (0, 1))
        self.reopen_archive()
        self.assertEqual(read_report(self.archive, issued[0].report_id), issued)

    def test_parallel_routes_merge_for_limit(self):
        # 同端点路线核账分列、转移相加;极限取合并多项式的最低次项。
        routes = (
            RouteRule('out-linear', 'A', 'B', '1/4', 1),
            RouteRule('out-quadratic', 'A', 'B', '1/4', 2),
            RouteRule('back', 'B', 'A', '1/2', 1),
        )
        _, plan_id = self.prepare(routes)
        plan = PlanStore(self.archive).load(plan_id)
        self.assertEqual(tuple(route.releases for route in plan.routes), (1, 2, 1))
        audit = audit_plan(self.archive, plan_id, '1/4')
        self.assertEqual(
            audit_values(audit),
            (('out-linear', F(1, 16)), ('out-quadratic', F(1, 64)), ('back', F(1, 8))),
        )
        self.assertEqual(audit.remaining, (F(59, 64), F(7, 8)))
        self.assert_occupations(issue_report(self.archive, plan_id)[0], (1, 0), (F(2, 3), F(1, 3)))

    def test_zero_and_rare_columns_diverge(self):
        # 完全关闭列停留在零比例闭类 {A,B};微量放行列按最低次树权重分三份。
        routes = (
            RouteRule('ab', 'A', 'B', '1/4', 0),
            RouteRule('ba', 'B', 'A', '1/2', 0),
            RouteRule('bc', 'B', 'C', '1/4', 1),
            RouteRule('ca', 'C', 'A', '1/2', 1),
        )
        _, plan_id = self.prepare(routes, ('A', 'B', 'C'))
        issued = issue_report(self.archive, plan_id)
        self.assert_occupations(issued[0], (F(2, 3), F(1, 3), 0), (F(4, 7), F(2, 7), F(1, 7)))
        self.reopen_archive()
        self.assertEqual(read_report(self.archive, issued[0].report_id), issued)

    def test_self_route_does_not_leak_into_limit(self):
        # 本站路线只计入转移矩阵对角,不构成树形图边,不改变微量极限。
        routes = (
            RouteRule('self-check', 'A', 'A', '1/4', 1),
            RouteRule('out', 'A', 'B', '1/4', 1),
            RouteRule('back', 'B', 'A', '1/2', 2),
        )
        _, plan_id = self.prepare(routes)
        audit = audit_plan(self.archive, plan_id, '1/2')
        self.assertEqual(
            audit_values(audit),
            (('self-check', F(1, 8)), ('out', F(1, 8)), ('back', F(1, 8))),
        )
        self.assertEqual(audit.remaining, (F(3, 4), F(7, 8)))
        self.assert_occupations(issue_report(self.archive, plan_id)[0], (1, 0), (0, 1))
