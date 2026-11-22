from fractions import Fraction

from plan.snapshot import FrozenPlan, FrozenRoute
from routing.stations import RationalInput, exact_fraction


def validate_ratio(value: RationalInput) -> Fraction:
    ratio = exact_fraction(value, 'release ratio')
    if not 0 <= ratio <= 1:
        raise ValueError('release ratio must be between zero and one')
    return ratio


def route_probability(route: FrozenRoute, ratio: Fraction) -> Fraction:
    return route.base_probability * ratio ** route.releases


def evaluate_routes(plan: FrozenPlan, ratio: RationalInput) -> tuple[Fraction, ...]:
    exact_ratio = validate_ratio(ratio)
    return tuple(route_probability(route, exact_ratio) for route in plan.routes)


def remaining_probabilities(plan: FrozenPlan, route_values: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    remaining = {station: Fraction(1) for station in plan.stations}
    for route, probability in zip(plan.routes, route_values, strict=True):
        remaining[route.source] -= probability
    return tuple(remaining.values())
