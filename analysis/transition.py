from fractions import Fraction

from plan.probability import evaluate_routes, remaining_probabilities
from plan.snapshot import FrozenPlan
from routing.stations import RationalInput

TransitionMatrix = tuple[tuple[Fraction, ...], ...]


def build_transition(plan: FrozenPlan, ratio: RationalInput) -> TransitionMatrix:
    """Build a row-stochastic matrix in the original station coordinates."""
    route_values = evaluate_routes(plan, ratio)
    remaining = remaining_probabilities(plan, route_values)
    index = {station: position for position, station in enumerate(plan.stations)}
    size = len(index)
    matrix = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    for position, mass in enumerate(remaining):
        matrix[position][position] = mass
    for route, mass in zip(plan.routes, route_values, strict=True):
        matrix[index[route.source]][index[route.destination]] += mass
    return tuple(tuple(row) for row in matrix)
