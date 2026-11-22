from dataclasses import dataclass
from fractions import Fraction

from plan.eligibility import check_eligibility
from routing.routes import RouteRule, validate_routes
from routing.stations import ordered_items, validate_identity, validate_initial_distribution, validate_stations


@dataclass(frozen=True, slots=True)
class FrozenRoute:
    route_id: str
    source: str
    destination: str
    base_probability: Fraction
    releases: int


@dataclass(frozen=True, slots=True)
class FrozenPlan:
    plan_id: str
    revision_id: str
    stations: tuple[str, ...]
    initial: tuple[Fraction, ...]
    routes: tuple[FrozenRoute, ...]


def validate_snapshot(plan: FrozenPlan) -> FrozenPlan:
    """Validate and canonicalize a self-contained handover plan."""
    if not isinstance(plan, FrozenPlan):
        raise ValueError('expected a FrozenPlan')
    plan_id = validate_identity(plan.plan_id, 'plan identity')
    revision_id = validate_identity(plan.revision_id, 'source revision identity')
    stations = validate_stations(plan.stations)
    station_names = tuple(station.name for station in stations)
    initial = validate_initial_distribution(stations, plan.initial)
    source_rules = []
    for route in ordered_items(plan.routes, 'frozen routes'):
        if not isinstance(route, FrozenRoute):
            raise ValueError('each frozen route must be a FrozenRoute')
        source_rules.append(RouteRule(route.route_id, route.source, route.destination, route.base_probability, route.releases))
    rules = validate_routes(stations, source_rules)
    check_eligibility(station_names, rules)
    routes = tuple(
        FrozenRoute(rule.route_id, rule.source, rule.destination, rule.base_probability, rule.releases)
        for rule in rules
    )
    return FrozenPlan(plan_id, revision_id, station_names, initial, routes)
