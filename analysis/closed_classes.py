from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class ClosedClassPartition:
    classes: tuple[tuple[int, ...], ...]
    transient: tuple[int, ...]


def decompose_closed_classes(matrix: Sequence[Sequence[Fraction]]) -> ClosedClassPartition:
    """Partition a finite transition matrix using its positive support."""
    size = len(matrix)
    if any(len(row) != size for row in matrix):
        raise ValueError('transition matrix must be square')
    reachable = [
        {source} | {target for target, probability in enumerate(row) if probability > 0}
        for source, row in enumerate(matrix)
    ]
    for middle in range(size):
        for targets in reachable:
            if middle in targets:
                targets.update(reachable[middle])

    classified = set()
    closed = []
    transient = set()
    for source in range(size):
        if source in classified:
            continue
        peers = {target for target in reachable[source] if source in reachable[target]}
        classified.update(peers)
        if reachable[source] == peers:
            closed.append(tuple(sorted(peers)))
        else:
            transient.update(peers)
    return ClosedClassPartition(tuple(closed), tuple(sorted(transient)))
