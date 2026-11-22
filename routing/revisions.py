from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from routing.routes import RouteRule, validate_routes
from routing.stations import RationalInput, Station, validate_identity, validate_initial_distribution, validate_stations


@dataclass(frozen=True, slots=True)
class RouteRevision:
    revision_id: str
    stations: tuple[Station, ...]
    initial: tuple[Fraction, ...]
    routes: tuple[RouteRule, ...]


def build_revision(
    revision_id: str,
    stations: Iterable[Station | str],
    initial: Iterable[RationalInput],
    routes: Iterable[RouteRule],
) -> RouteRevision:
    identifier = validate_identity(revision_id, 'revision identity')
    normalized_stations = validate_stations(stations)
    return RouteRevision(
        identifier,
        normalized_stations,
        validate_initial_distribution(normalized_stations, initial),
        validate_routes(normalized_stations, routes),
    )
