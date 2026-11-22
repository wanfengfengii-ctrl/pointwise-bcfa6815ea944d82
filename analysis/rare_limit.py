from fractions import Fraction

from analysis.linear_system import stationary_distribution
from analysis.transition import build_transition
from plan.snapshot import FrozenPlan


_PILOT_RATIO = Fraction(1, 100)


def rare_occupation_limit(plan: FrozenPlan) -> tuple[Fraction, ...]:
    return stationary_distribution(build_transition(plan, _PILOT_RATIO))
