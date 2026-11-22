from collections.abc import Sequence
from fractions import Fraction


def solve_fraction_system(
    coefficients: Sequence[Sequence[Fraction | int]],
    constants: Sequence[Fraction | int],
) -> tuple[Fraction, ...]:
    """Solve a square nonsingular system by exact row elimination."""
    size = len(coefficients)
    if len(constants) != size or any(len(row) != size for row in coefficients):
        raise ValueError('linear system dimensions do not agree')
    rows = [
        [Fraction(value) for value in row] + [Fraction(constant)]
        for row, constant in zip(coefficients, constants, strict=True)
    ]
    for column in range(size):
        pivot = next((index for index in range(column, size) if rows[index][column]), None)
        if pivot is None:
            raise ValueError('singular linear system')
        rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        rows[column] = [value / scale for value in rows[column]]
        for index, row in enumerate(rows):
            factor = row[column]
            if index != column and factor:
                rows[index] = [value - factor * lead for value, lead in zip(row, rows[column], strict=True)]
    return tuple(row[-1] for row in rows)


def stationary_distribution(matrix: Sequence[Sequence[Fraction]]) -> tuple[Fraction, ...]:
    """Return the unique stationary distribution of a closed irreducible class."""
    size = len(matrix)
    if not size or any(len(row) != size for row in matrix):
        raise ValueError('stationary distribution requires a nonempty square matrix')
    equations = [
        [matrix[source][target] - int(source == target) for source in range(size)]
        for target in range(size - 1)
    ]
    equations.append([1] * size)
    return solve_fraction_system(equations, [0] * (size - 1) + [1])
