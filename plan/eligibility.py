from collections.abc import Iterable

from routing.routes import RouteRule


def _reachable(station: str, graph: dict[str, set[str]]) -> set[str]:
    pending = [station]
    visited = {station}
    while pending:
        current = pending.pop()
        unseen = graph[current] - visited
        visited.update(unseen)
        pending.extend(unseen)
    return visited


def check_eligibility(stations: tuple[str, ...], routes: Iterable[RouteRule]) -> None:
    """Check a validated set of routes on the positive-release support."""
    if not 2 <= len(stations) <= 6:
        raise ValueError('a fixed plan must have two to six stations')
    forward = {name: set() for name in stations}
    reverse = {name: set() for name in stations}
    for route in routes:
        if route.base_probability > 0:
            forward[route.source].add(route.destination)
            reverse[route.destination].add(route.source)
    for graph in (forward, reverse):
        if len(_reachable(stations[0], graph)) != len(stations):
            raise ValueError('fixed plan stations must be mutually reachable at positive release ratios')
