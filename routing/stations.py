from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from fractions import Fraction

RationalInput = Fraction | int | str


@dataclass(frozen=True, slots=True)
class Station:
    name: str


def validate_identity(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonblank string')
    return value


def ordered_items(values: Iterable, label: str) -> tuple:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError(f'{label} must be an ordered collection')
    try:
        return tuple(values)
    except TypeError as error:
        raise ValueError(f'{label} must be an ordered collection') from error


def exact_fraction(value: object, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (Fraction, int, str)):
        raise ValueError(f'{label} must be an exact rational number')
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f'{label} must be an exact rational number') from error


def validate_stations(values: Iterable[Station | str]) -> tuple[Station, ...]:
    stations = []
    names = set()
    for value in ordered_items(values, 'stations'):
        name = validate_identity(value.name if isinstance(value, Station) else value, 'station name')
        if name in names:
            raise ValueError(f'duplicate station {name!r}')
        names.add(name)
        stations.append(Station(name))
    if not stations:
        raise ValueError('at least one station is required')
    return tuple(stations)


def validate_initial_distribution(stations: tuple[Station, ...], values: Iterable[RationalInput]) -> tuple[Fraction, ...]:
    entries = ordered_items(values, 'station distribution')
    if len(entries) != len(stations):
        raise ValueError('station distribution must have one entry per station')
    masses = tuple(exact_fraction(value, f'mass for {station.name!r}') for station, value in zip(stations, entries))
    if any(mass < 0 for mass in masses) or sum(masses) != 1:
        raise ValueError('station distribution must be nonnegative and sum to one')
    return masses
