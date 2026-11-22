from dataclasses import replace
from fractions import Fraction

from routing.intake import record_revision
from routing.routes import RouteRule
from routing.stations import Station
from tests.support import LineTestCase, incident_routes


class RoutingTests(LineTestCase):
    def test_over_budget(self):
        routes = (RouteRule('transfer', 'A', 'B', '3/4', 1), RouteRule('repeat', 'A', 'B', '3/4', 2))
        with self.assertRaisesRegex(ValueError, 'full-release probability'):
            record_revision(self.source, ('A', 'B'), (1, 0), routes)
        self.assertEqual(self.source_count(), 0)

    def test_cross_destination_budget(self):
        routes = (RouteRule('to-b', 'A', 'B', '3/4', 0), RouteRule('to-c', 'A', 'C', '3/4', 2))
        with self.assertRaisesRegex(ValueError, 'full-release probability'):
            record_revision(self.source, ('A', 'B', 'C'), (1, 0, 0), routes)
        self.assertEqual(self.source_count(), 0)

    def test_invalid_intake(self):
        outbound, returning = incident_routes()
        stations = ('A', 'B')
        initial = (1, 0)
        routes = (outbound, returning)
        cases = {
            'no stations': ((), (), ()),
            'missing station name': (('A', ''), initial, routes),
            'duplicate station': (('A', 'A'), initial, routes),
            'unordered stations': ({'A', 'B'}, initial, routes),
            'missing initial mass': (stations, (1,), routes),
            'nonunit initial mass': (stations, ('1/4', '1/4'), routes),
            'negative initial mass': (stations, (2, -1), routes),
            'null mass': (stations, (None, 0), routes),
            'duplicate route': (stations, initial, (outbound, replace(returning, route_id=outbound.route_id))),
            'missing route identity': (stations, initial, (replace(outbound, route_id=None), returning)),
            'missing route fields': (stations, initial, ({'route_id': 'incomplete'},)),
            'unknown endpoint': (stations, initial, (replace(outbound, destination='C'), returning)),
            'bad release count': (stations, initial, (replace(outbound, releases=3), returning)),
            'boolean release count': (stations, initial, (replace(outbound, releases=True), returning)),
            'malformed fraction': (stations, initial, (replace(outbound, base_probability='1/0'), returning)),
            'float probability': (stations, initial, (replace(outbound, base_probability=0.5), returning)),
            'negative probability': (stations, initial, (replace(outbound, base_probability='-1/2'), returning)),
        }
        baseline_id = record_revision(self.source, stations, initial, routes)
        baseline = self.source.get(baseline_id)
        for label, arguments in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    record_revision(self.source, *arguments)
                self.assertEqual(self.source_count(), 1)
                self.assertEqual(self.source.get(baseline_id), baseline)

    def test_ordered_exact_revision(self):
        routes = incident_routes() + (RouteRule('inactive', 'B', 'A', 0, 1),)
        revision_id = record_revision(self.source, (Station('B'), 'A'), ('1/3', '2/3'), routes)
        revision = self.source.get(revision_id)
        self.assertEqual(revision.stations, (Station('B'), Station('A')))
        self.assertEqual(revision.initial, (Fraction(1, 3), Fraction(2, 3)))
        self.assertEqual(tuple(route.route_id for route in revision.routes), ('outbound', 'return', 'inactive'))
        self.assertEqual(tuple(route.base_probability for route in revision.routes), (Fraction(1, 2), Fraction(1, 2), Fraction(0)))
