from dataclasses import dataclass
from fractions import Fraction

from analysis.closed_classes import decompose_closed_classes
from analysis.linear_system import solve_fraction_system, stationary_distribution
from analysis.rare_limit import rare_occupation_limit
from analysis.transition import build_transition
from plan.snapshot import FrozenPlan


@dataclass(frozen=True, slots=True)
class OccupationDraft:
    plan_id: str
    stations: tuple[str, ...]
    zero: tuple[Fraction, ...]
    rare: tuple[Fraction, ...]


def zero_occupation(plan: FrozenPlan) -> tuple[Fraction, ...]:
    matrix = build_transition(plan, 0)
    partition = decompose_closed_classes(matrix)
    transient = partition.transient
    absorption_system = [
        [int(source == target) - matrix[source][target] for target in transient]
        for source in transient
    ]
    occupation = [Fraction(0) for _ in plan.stations]
    for closed in partition.classes:
        direct_entry = [sum(matrix[source][target] for target in closed) for source in transient]
        hitting = solve_fraction_system(absorption_system, direct_entry)
        weight = sum(plan.initial[station] for station in closed)
        weight += sum(plan.initial[station] * probability for station, probability in zip(transient, hitting, strict=True))
        class_matrix = tuple(tuple(matrix[source][target] for target in closed) for source in closed)
        within = stationary_distribution(class_matrix)
        for station, probability in zip(closed, within, strict=True):
            occupation[station] = weight * probability
    return tuple(occupation)


def forecast_occupation(plan: FrozenPlan) -> OccupationDraft:
    return OccupationDraft(plan.plan_id, plan.stations, zero_occupation(plan), rare_occupation_limit(plan))
