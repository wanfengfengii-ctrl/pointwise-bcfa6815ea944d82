from dataclasses import dataclass
from fractions import Fraction

from archive.catalog import HandoverArchive
from archive.plan_store import PlanStore
from plan.probability import evaluate_routes, remaining_probabilities, validate_ratio
from routing.stations import RationalInput


@dataclass(frozen=True, slots=True)
class RouteAuditRow:
    route_id: str
    source: str
    destination: str
    probability: Fraction


@dataclass(frozen=True, slots=True)
class AuditResult:
    plan_id: str
    ratio: Fraction
    stations: tuple[str, ...]
    routes: tuple[RouteAuditRow, ...]
    remaining: tuple[Fraction, ...]


def audit_plan(archive: HandoverArchive, plan_id: str, ratio: RationalInput) -> AuditResult:
    exact_ratio = validate_ratio(ratio)
    plan = PlanStore(archive).load(plan_id)
    route_values = evaluate_routes(plan, exact_ratio)
    rows = tuple(
        RouteAuditRow(route.route_id, route.source, route.destination, probability)
        for route, probability in zip(plan.routes, route_values, strict=True)
    )
    return AuditResult(plan.plan_id, exact_ratio, plan.stations, rows, remaining_probabilities(plan, route_values))
