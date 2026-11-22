from dataclasses import dataclass
from fractions import Fraction

from routing.stations import validate_identity, validate_initial_distribution, validate_stations


@dataclass(frozen=True, slots=True)
class OccupationReport:
    report_id: str
    plan_id: str
    stations: tuple[str, ...]
    zero: tuple[Fraction, ...]
    rare: tuple[Fraction, ...]


def validate_report(report: OccupationReport) -> OccupationReport:
    if not isinstance(report, OccupationReport):
        raise ValueError('expected an OccupationReport')
    report_id = validate_identity(report.report_id, 'report identity')
    plan_id = validate_identity(report.plan_id, 'plan identity')
    stations = validate_stations(report.stations)
    if not 2 <= len(stations) <= 6:
        raise ValueError('an occupation report must have two to six stations')
    return OccupationReport(
        report_id,
        plan_id,
        tuple(station.name for station in stations),
        validate_initial_distribution(stations, report.zero),
        validate_initial_distribution(stations, report.rare),
    )
