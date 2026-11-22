from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from routing.stations import RationalInput, Station, exact_fraction, ordered_items, validate_identity


@dataclass(frozen=True, slots=True)
class RouteRule:
    route_id: str
    source: str
    destination: str
    base_probability: RationalInput
    releases: int


def validate_routes(stations: tuple[Station, ...], values: Iterable[RouteRule]) -> tuple[RouteRule, ...]:
    budget = {station.name: Fraction(0) for station in stations}
    route_ids = set()
    routes = []
    for value in ordered_items(values, 'routes'):
        if not isinstance(value, RouteRule):
            raise ValueError('each route must be a RouteRule')
        route_id = validate_identity(value.route_id, 'route identity')
        if route_id in route_ids:
            raise ValueError(f'duplicate route {route_id!r}')
        source = validate_identity(value.source, 'route source')
        destination = validate_identity(value.destination, 'route destination')
        if source not in budget or destination not in budget:
            raise ValueError(f'route {route_id!r} refers to an unknown station')
        if type(value.releases) is not int or value.releases not in (0, 1, 2):
            raise ValueError(f'route {route_id!r} must require zero, one or two releases')
        probability = exact_fraction(value.base_probability, f'probability of {route_id!r}')
        if probability < 0:
            raise ValueError(f'negative base probability for route {route_id!r}')
        budget[source] += probability
        if budget[source] > 1:
            raise ValueError(f'full-release probability exceeds one at station {source!r}')
        route_ids.add(route_id)
        routes.append(RouteRule(route_id, source, destination, probability, value.releases))
    return tuple(routes)
